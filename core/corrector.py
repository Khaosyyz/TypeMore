import threading

import requests


class Corrector:
    """每 interval_chars 个新进字符触发一次云端矫正;单线程串行,最多一个在途请求"""

    def __init__(self, cfg, buffer, learner, context_text_fn):
        self.cfg = cfg
        self.buffer = buffer
        self.learner = learner
        self.context_text = context_text_fn
        self._pending = 0
        self._key_warned = False
        self._interval = cfg["correction"]["interval_chars"]
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = None

    def on_append(self, n_chars):
        self._pending += n_chars
        self._wake.set()

    def on_commit(self):
        """提交后触发计数归零(与快照世代无关,仅重置计数)"""
        self._pending = 0

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def _run(self):
        while not self._stop.is_set():
            self._wake.wait()
            self._wake.clear()
            if self._pending >= self._interval:
                self._pending = 0
                self._correct()

    def _correct(self):
        snap = self.buffer.snapshot()
        if not snap.text.strip():
            return
        api = self.cfg["api"]
        key = api.get("key")
        if not key:
            if not self._key_warned:
                self._key_warned = True
                print("[corrector] config.yaml 未填 api.key,云端矫正停用")
            return
        print(f"[矫正] 触发(缓冲区 {len(snap.text)}字): {snap.text!r}")
        body = {
            "model": api["model"],
            "messages": [
                {"role": "system", "content": self.cfg["correction"]["system_prompt"].format(context=self.context_text())},
                {"role": "user", "content": snap.text},
            ],
            "temperature": api["temperature"],
            "stream": False,
        }
        if api.get("thinking_disabled"):
            body["thinking"] = {"type": "disabled"}
        new_text = None
        try:
            r = requests.post(
                api["base_url"],
                headers={"Authorization": f"Bearer {key}"},
                json=body,
                timeout=api["timeout_ms"] / 1000,
            )
            r.raise_for_status()
            new_text = r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[corrector] {e}")
        if not new_text:
            return
        changed = sum(1 for a, b in zip(snap.text, new_text) if a != b) + abs(len(snap.text) - len(new_text))
        print(f"[矫正] 结果({changed}处变化): {new_text!r}")
        if changed:
            self.buffer.replace_from_snapshot(snap, new_text)
            self.learner.process(snap.text, new_text)
