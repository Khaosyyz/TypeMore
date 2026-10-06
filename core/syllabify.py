import re
import unicodedata

from pypinyin.core import PINYIN_DICT


def _plain(reading):
    out = []
    for ch in reading:
        d = unicodedata.normalize("NFD", ch)
        base, marks = d[0], d[1:]
        if base == "ü" or (base == "u" and "\u0308" in marks):
            out.append("v")
        elif base.isascii() and base.isalpha():
            out.append(base.lower())
    return "".join(out)


def _syllables():
    syls = set()
    for v in PINYIN_DICT.values():
        for reading in v.split(","):
            p = _plain(reading)
            if p:
                syls.add(p)
    return syls


SYLLABLES = _syllables()
_MAX_SYLL = max(len(s) for s in SYLLABLES)
_RUN = re.compile(r"[a-z]+")


def _split_run(s):
    if not s:
        return []
    for L in range(len(s), 0, -1):
        if s[:L] in SYLLABLES:
            rest = _split_run(s[L:])
            if rest is not None:
                return [s[:L]] + rest
    return None


def _split_exact(s, want):
    """记忆化搜索:恰好 want 个音节的切法(长音节优先),无解返回 None"""
    memo = {}

    def dfs(i, k):
        if i == len(s):
            return [] if k == 0 else None
        if k <= 0 or (i, k) in memo:
            return memo.get((i, k))
        for L in range(min(_MAX_SYLL, len(s) - i), 0, -1):
            if s[i:i + L] in SYLLABLES:
                rest = dfs(i + L, k - 1)
                if rest is not None:
                    memo[(i, k)] = [s[i:i + L]] + rest
                    return memo[(i, k)]
        memo[(i, k)] = None
        return None

    return dfs(0, want)


def split(raw, count=None):
    """连续拼音串切成音节列表;count 为期望音节数(已知提交字数时传入),
    歧义段(如 shanjiao = shan+jiao | sha+jian)按数量约束消解;非法串返回 None"""
    out = []
    for seg in _RUN.findall(raw.lower()):
        want = None if count is None else count - len(out)
        part = _split_exact(seg, want) if want is not None else _split_run(seg)
        if part is None:
            return None
        out += part
    return out or None
