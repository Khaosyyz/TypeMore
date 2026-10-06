import os


class Channel:
    """侧车与引擎之间的三个通道文件(引擎侧 lua 只做行解析,故不采用 json)"""

    def __init__(self, user_dir):
        self.user_dir = user_dir
        self._boost_path = os.path.join(user_dir, "typemore_boost.txt")
        self._learn_path = os.path.join(user_dir, "typemore_learn.txt")
        self._feed_path = os.path.join(user_dir, "typemore_feed.log")
        self._learn_seq = 1
        self._feed_offset = 0

    def init_files(self):
        self._write(self._learn_path, "1\n")
        self._write(self._boost_path, "")
        self._feed_offset = self._feed_size()

    def _write(self, path, content):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)

    def _feed_size(self):
        return os.path.getsize(self._feed_path) if os.path.exists(self._feed_path) else 0

    def write_boost(self, scores):
        self._write(self._boost_path, "".join(f"{w} {s}\n" for w, s in scores.items()))

    def write_learn(self, items):
        """items: [(word, pinyin)],行格式 word pinyin(词在前,lua 侧按 ASCII 边界解析)"""
        self._learn_seq += 1
        lines = [f"{self._learn_seq}\n"] + [f"{w} {py}\n" for w, py in items]
        self._write(self._learn_path, "".join(lines))

    def feed_lines(self):
        """返回自上次调用以来新增的行 [(text, input)]"""
        if not os.path.exists(self._feed_path):
            return []
        with open(self._feed_path, "r", encoding="utf-8") as f:
            f.seek(self._feed_offset)
            chunk = f.read()
            self._feed_offset = f.tell()
        out = []
        for line in chunk.splitlines():
            if line:
                text, _, raw = line.partition("\t")
                out.append((text, raw))
        return out
