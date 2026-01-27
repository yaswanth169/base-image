#!/usr/bin/env python
"""CLI entry point."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.base_image_agent import main

if __name__ == "__main__":
    main()
