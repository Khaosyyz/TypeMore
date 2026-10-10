import ctypes
import threading
import time
from ctypes import wintypes

import jieba
import uiautomation as uia

_WINEVENTPROC = ctypes.WINFUNCTYPE(
    None, wintypes.HWND, ctypes.c_uint, wintypes.HWND, ctypes.c_long, ctypes.c_long, ctypes.c_uint, ctypes.c_uint
)
_TIMERPROC = ctypes.WINFUNCTYPE(None, wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, wintypes.DWORD)
EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_FOCUS = 0x8005
WM_QUIT = 0x0012
WM_WAKEUP = 0x0401
CARET_TIMER_MS = 200


class ContextService:
    """语境服务:聚焦是唯一内容信号——聚焦一次抓一次,全量覆盖加分表与语境原文。
    光标定位(独立于内容刷新)由定时器在泵线程上持续跟踪,供候选窗锚定。
    所有 uia COM 调用必须与 COM 初始化同线程且该线程泵消息,因此收敛到 _pump 单线程。"""

    def __init__(self, cfg, channel):
        self._cfg = cfg["context"]
        self._channel = channel
        self.last_text = ""
        self.caret_pos = None
        self.editable = False
        self.is_password = False
        self._focus_state = ""
        self._last = 0.0
        self._last_hwnd = None
        self._nodes = 0
        self._thread_id = None
        self._evt_pending = False
        self._keep = []
        uia.SetGlobalSearchTimeout(self._cfg["uia_timeout_ms"])

    def start(self):
        threading.Thread(target=self._pump, daemon=True).start()

    def stop(self):
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _pump(self):
        uia.InitializeUIAutomationInCurrentThread()
        self._thread_id = threading.get_ident()
        user32 = ctypes.windll.user32
        self._keep = [_WINEVENTPROC(self._on_event), _TIMERPROC(self._on_caret_timer)]
        user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, None, self._keep[0], 0, 0, 0)
        user32.SetWinEventHook(EVENT_OBJECT_FOCUS, EVENT_OBJECT_FOCUS, None, self._keep[0], 0, 0, 0)
        user32.SetTimer(None, 1, CARET_TIMER_MS, self._keep[1])
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
            if self._evt_pending:
                self._evt_pending = False
                self._capture_if()

    def _on_event(self, *args):
        self._evt_pending = True
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_WAKEUP, 0, 0)

    def _on_caret_timer(self, *args):
        """光标/焦点状态探测器:仅更新缓存(位置、可编辑、密码),与语境内容刷新无关"""
        try:
            ctrl = uia.GetFocusedControl()
            if not ctrl:
                return
            ctype = ctrl.ControlTypeName
            name = (ctrl.Name or "")[:24]
            pw = False
            try:
                pw = bool(ctrl.GetPropertyValue(uia.PropertyId.IsPasswordPropertyId))
            except Exception:
                pass
            caret = None
            try:
                tp = ctrl.GetTextPattern()
                sel = tp.GetSelection()
                r = sel[0] if isinstance(sel, (list, tuple)) else sel
                rects = r.GetBoundingRectangles()
                if rects:
                    rc = rects[-1]
                    caret = (int(rc.left), int(rc.bottom))
            except Exception:
                pass
            editable = (caret is not None or ctype == "EditControl") and not pw
            state = f"{ctype}|{name}"
            if state != self._focus_state:
                self._focus_state = state
                print(f"[焦点] {ctype} '{name}' 可编辑={editable} 密码={pw}")
            self.editable = editable
            self.is_password = pw
            if caret:
                self.caret_pos = caret
        except Exception:
            pass

    def _capture_if(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            fresh_window = hwnd != self._last_hwnd
            if not fresh_window and time.time() - self._last < self._cfg["capture_min_interval_ms"] / 1000:
                return
            if not self._editable():
                return
            self._capture()
        except Exception as e:
            print(f"[context] {e}")

    def _editable(self):
        try:
            ctrl = uia.GetFocusedControl()
            return bool(ctrl) and ctrl.ControlType in (uia.ControlType.EditControl, uia.ControlType.DocumentControl)
        except Exception:
            return False

    def _capture(self):
        t0 = time.perf_counter()
        texts = []
        self._nodes = 0
        try:
            self._collect(uia.GetForegroundControl(), 0, texts)
        except Exception:
            pass
        joined = " ".join(texts)[: self._cfg["max_context_chars"]]
        self.last_text = joined
        boost = {}
        for w in jieba.cut(joined):
            if len(w) >= 2:
                boost[w] = boost.get(w, 0) + 1
        scores = {
            w: min(n, self._cfg["boost_cap"])
            for w, n in sorted(boost.items(), key=lambda x: -x[1])[: self._cfg["max_boost_words"]]
        }
        self._channel.write_boost(scores)
        self._last = time.time()
        self._last_hwnd = ctypes.windll.user32.GetForegroundWindow()
        print(f"[context] {len(texts)}段/{len(joined)}字 → {len(scores)}词 {(time.perf_counter()-t0)*1000:.1f}ms")

    def _collect(self, ctrl, depth, out):
        if depth > self._cfg["max_depth"] or self._nodes > self._cfg["max_nodes"]:
            return
        self._nodes += 1
        try:
            v = ctrl.Name
            if v and len(v.strip()) > 1 and v.strip() not in out:
                out.append(v.strip())
        except Exception:
            pass
        try:
            if ctrl.ControlType in (uia.ControlType.EditControl, uia.ControlType.DocumentControl):
                v = ctrl.GetValuePattern().Value
                if v and len(v.strip()) > 1 and v.strip() not in out:
                    out.append(v.strip())
        except Exception:
            pass
        try:
            for child in ctrl.GetChildren():
                self._collect(child, depth + 1, out)
        except Exception:
            pass
