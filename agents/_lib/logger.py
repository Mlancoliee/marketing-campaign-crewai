import datetime


def make_logger(prefix: str):
    def log(msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{prefix}][{ts}] {msg}")
    return log
