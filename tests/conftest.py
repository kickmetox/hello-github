import os
import tempfile
from pathlib import Path

_root = Path(tempfile.mkdtemp(prefix="docman-test-"))
os.environ["DOCMAN_DATA"] = str(_root)
os.environ["DOCMAN_SEED"] = "0"
os.environ["DOCMAN_WATCH"] = "0"
os.environ["DOCMAN_HOST"] = "127.0.0.1"
os.environ["DOCMAN_PORT"] = "8000"
