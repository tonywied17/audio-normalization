"""Utility helpers for batch processing."""
import os
from typing import List


def find_media_files(directory: str, supported_extensions) -> List[str]:
    media_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(supported_extensions):
                media_files.append(os.path.join(root, file))
    return media_files
