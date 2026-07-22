from datetime import datetime
from pathlib import Path

# ── unbuffered stdout + file tee ──────────────────────────────────
_log_fh = open(Path(__file__).parent / "has.log", "a", encoding="utf-8")
_log_fh.write(f"\n--- HAS session {datetime.now():%Y-%m-%d %H:%M:%S} ---\n")
_log_fh.flush()

import sys

class _TeeStream:
    """Wraps a stream so every write is flushed immediately AND teed to the log file."""
    def __init__(self, original):
        self.original = original
    def write(self, data):
        self.original.write(data)
        self.original.flush()
        _log_fh.write(data)
        _log_fh.flush()
    def flush(self):
        self.original.flush()
        _log_fh.flush()

sys.stdout = _TeeStream(sys.stdout)
sys.stderr = _TeeStream(sys.stderr)
# ──────────────────────────────────────────────────────────────────

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
