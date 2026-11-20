#!/usr/bin/env python3
"""Compatibility forwarder to social-science-km/scripts/check_rebuild_rag.py."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_rebuild_rag import *  # noqa: F401,F403,E402
from check_rebuild_rag import main  # noqa: E402

if __name__ == "__main__":
    main()
