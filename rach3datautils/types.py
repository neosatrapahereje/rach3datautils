"""
Custom types used throughout the whole module
"""
from typing import Tuple, Union
import os


timestamps = Tuple[float, float]
note_sections = Tuple[int, int]

# Recommended by PEP 519
PathLike = Union[str, bytes, os.PathLike]
