"""Utility functions for Base Image Automation Agent."""

import logging
import re
import sys
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def parse_version(tag: str) -> Optional[Tuple]:
    if not tag:
        return None
    parts = re.findall(r'\d+', tag)
    return tuple(int(p) for p in parts) if parts else None


def compare_versions(current: str, latest: str) -> Tuple[bool, Optional[int]]:
    if current == latest:
        return True, 0
    
    current_tuple = parse_version(current)
    latest_tuple = parse_version(latest)
    
    if current_tuple and latest_tuple:
        if current_tuple >= latest_tuple:
            return True, 0
        for i in range(min(len(current_tuple), len(latest_tuple))):
            if current_tuple[i] < latest_tuple[i]:
                return False, latest_tuple[i] - current_tuple[i]
        return False, 1
    
    return False, None


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def encode_project_path(project_path: str) -> str:
    return project_path.replace("/", "%2F")
