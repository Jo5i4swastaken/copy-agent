class FileLock:
    def __init__(self, lock_file: str):
        self._lock_file = lock_file
        try:
            from filelock import FileLock as _FileLock
        except Exception:
            _FileLock = None
        self._impl = _FileLock(lock_file) if _FileLock else None

    def __enter__(self):
        if self._impl is None:
            return self
        return self._impl.__enter__()

    def __exit__(self, exc_type, exc, tb):
        if self._impl is None:
            return False
        return self._impl.__exit__(exc_type, exc, tb)
