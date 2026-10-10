import difflib

import jieba
from pypinyin import lazy_pinyin


class Learner:
    """矫正返回后的学习管线:diff 词对 + 矫正后全文分词 → 有则计数无则造词,统一写学习清单"""

    def __init__(self, cfg, channel, buffer):
        self.cfg = cfg
        self.channel = channel
        self.buffer = buffer
        seg = cfg["segmentation"]
        self.word_freq = seg["learn_word_freq"]
        self.fallback = seg["pinyin_fallback"]

    def process(self, old_text, new_text):
        diff_pairs = self._diff_pairs(old_text, new_text)
        seg_words = list(jieba.lcut(new_text))
        print(f"[学习] diff词对: {diff_pairs or '无'} | 分词: {seg_words}")
        words = set(diff_pairs) | set(seg_words)
        items = []
        for w in words:
            if w.isascii():
                continue
            py = self._word_pinyin(w)
            if py:
                items.append((w, py))
        if items:
            items.sort(key=lambda x: (-len(x[0]), x[0]))
            self.channel.write_learn(items)
            for w, _ in items:
                jieba.add_word(w, freq=self.word_freq)
            print(f"[学习] 写清单 {len(items)} 条: {items}")
        return items

    def _diff_pairs(self, old, new):
        out = []
        sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "replace":
                continue
            ow = jieba.lcut(old[i1:i2])
            nw = jieba.lcut(new[j1:j2])
            wsm = difflib.SequenceMatcher(None, ow, nw, autojunk=False)
            for t, a1, a2, b1, b2 in wsm.get_opcodes():
                if t == "replace" and (a2 - a1) == (b2 - b1):
                    out.extend(nw[b1:b2])
                elif t == "insert":
                    out.extend(nw[b1:b2])
        return out

    def _word_pinyin(self, word):
        pos = 0
        while True:
            pos = self.buffer.locate(word, pos)
            if pos < 0:
                break
            py = self.buffer.sylls(pos, pos + len(word))
            if py:
                return py
            pos += 1
        if self.fallback:
            return " ".join(lazy_pinyin(word))
        return None
