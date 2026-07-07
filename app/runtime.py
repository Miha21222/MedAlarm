from __future__ import annotations

import signal
import subprocess
import sys
import time


COMMANDS = (
    (sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"),
    (sys.executable, "main.py"),
)


def run() -> int:
    processes = [subprocess.Popen(command) for command in COMMANDS]
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for process in processes:
            process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping:
            for process in processes:
                if process.poll() is not None:
                    stop()
                    return process.returncode or 1
            time.sleep(0.5)
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
