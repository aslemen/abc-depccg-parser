"""
An A* CCG Parser for Modern Japanese, based on the ABC Treebank

Author: Nori Hayashi <ac@hayashi-lin.net>
"""

import subprocess

name = "abc-depccg-parser"

try:
    __version__ = subprocess.check_output(["git", "describe"]).strip()
except:
    __version__ = "N/A"
# === END TRY ===