#!/usr/bin/env python3
"""Точка входа TGWorker.exe — чистка tdata и экспорт session-пака, без Qt."""
from __future__ import annotations

import sys

from tgmanager.automation.worker import main

if __name__ == "__main__":
    raise SystemExit(main())
