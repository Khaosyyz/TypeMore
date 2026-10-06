import os
import threading

import yaml

from core.buffer import Buffer
from core.channel import Channel
from core.context import ContextService
from core.corrector import Corrector
from core.learner import Learner


class App:
    """装配层:把缓冲区/矫正器/学习/语境四模块接成一个运行中的服务"""

    def __init__(self, cfg, root):
        ch_dir = cfg["channel"]["dir"]
        if not os.path.isabs(ch_dir):
            ch_dir = os.path.join(root, ch_dir)
        os.makedirs(ch_dir, exist_ok=True)
        self.channel = Channel(ch_dir)
        self.channel.init_files()
        self.buffer = Buffer()
        self.learner = Learner(cfg, self.channel, self.buffer)
        self.context = ContextService(cfg, self.channel)
        self.corrector = Corrector(cfg, self.buffer, self.learner, lambda: self.context.last_text)
        self.buffer.on_append = self.corrector.on_append
        self.buffer.on_commit = self.corrector.on_commit
        self._stop = threading.Event()

    def start(self):
        self.context.start()
        self.corrector.start()
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._stop.set()
        self.corrector.stop()
        self.context.stop()

    def _loop(self):
        """尾随通道 feed 日志(未来由引擎侧写入),驱动缓冲区进字"""
        while not self._stop.is_set():
            for text, raw in self.channel.feed_lines():
                self.buffer.append(text, raw)
            self._stop.wait(0.05)


def load_config(root):
    cfg_path = os.path.join(root, "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = App(load_config(root), root)
    app.start()
    print("typemore service running, Ctrl+C 退出")
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        app.stop()
