import threading
from collections import namedtuple

from core import syllabify

Snapshot = namedtuple("Snapshot", "gen text sylls")


class Buffer:
    """逐字槽位缓冲区:每字一个 [char, 拼音音节|None],拼音取自用户实际键入"""

    def __init__(self, on_append=None, on_commit=None):
        self._slots = []
        self._gen = 0
        self.on_append = on_append
        self.on_commit = on_commit
        self._lock = threading.RLock()

    @property
    def text(self):
        with self._lock:
            return "".join(s[0] for s in self._slots)

    def sylls(self, start, end):
        with self._lock:
            seg = self._slots[start:end]
            if any(s[1] is None for s in seg):
                return None
            return " ".join(s[1] for s in seg)

    def locate(self, word, from_index=0):
        """词在缓冲区中的字符起点,找不到返回 -1"""
        with self._lock:
            text = "".join(s[0] for s in self._slots)
        return text.find(word, from_index)

    def append(self, text, raw_input):
        sylls = syllabify.split(raw_input, count=len(text)) if raw_input else None
        with self._lock:
            aligned = sylls is not None and len(sylls) == len(text)
            for i, ch in enumerate(text):
                self._slots.append((ch, sylls[i] if aligned else None))
        if self.on_append:
            self.on_append(len(text))

    def snapshot(self):
        with self._lock:
            return Snapshot(self._gen, "".join(s[0] for s in self._slots), tuple(s[1] for s in self._slots))

    def replace_from_snapshot(self, snap, new_text):
        """只替换快照覆盖的前缀段;世代不符(期间提交过)返回 False"""
        with self._lock:
            if snap.gen != self._gen:
                return False
            inherit = len(new_text) == len(snap.text)
            head = [(ch, snap.sylls[i] if inherit else None) for i, ch in enumerate(new_text)]
            self._slots = head + self._slots[len(snap.text):]
            return True

    def delete_last(self):
        with self._lock:
            if self._slots:
                self._slots.pop()

    def commit(self):
        with self._lock:
            text = "".join(s[0] for s in self._slots)
            self._slots = []
            self._gen += 1
        if self.on_commit:
            self.on_commit()
        return text
