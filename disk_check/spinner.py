import sys
import threading
import time

from disk_check.constants import G, C, RS


class MultiSpinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, sections):
        # sections: [(key, label), ...]
        self._sections = list(sections)
        self._n = len(self._sections)
        self._done = set()
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._initialized = threading.Event()

    def _redraw(self, frame_idx):
        frame = self.FRAMES[frame_idx % len(self.FRAMES)]
        for key, label in self._sections:
            if key in self._done:
                sys.stdout.write(f"\r\033[K  {G}✓{RS}  {label}\n")
            else:
                sys.stdout.write(f"\r\033[K  {C}{frame}{RS}  {label}\n")

    def _spin(self):
        with self._lock:
            for _ in range(self._n):
                sys.stdout.write("\n")
            sys.stdout.flush()
        self._initialized.set()
        i = 0
        while self._running:
            with self._lock:
                sys.stdout.write(f"\033[{self._n}A")
                self._redraw(i)
                sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        self._initialized.wait()

    def section_done(self, key, output):
        with self._lock:
            sys.stdout.write(f"\033[{self._n}A")
            for _ in range(self._n):
                sys.stdout.write(f"\r\033[K\n")
            sys.stdout.write(f"\033[{self._n}A")
            sys.stdout.write(output + "\n")
            self._done.add(key)
            self._redraw(0)
            sys.stdout.flush()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        with self._lock:
            sys.stdout.write(f"\033[{self._n}A")
            for _ in range(self._n):
                sys.stdout.write(f"\r\033[K\n")
            sys.stdout.write(f"\033[{self._n}A")
            sys.stdout.flush()


class NullSpinner:
    def start(self): pass
    def section_done(self, key, output): pass
    def stop(self): pass
