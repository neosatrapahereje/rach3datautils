"""
Custom types used throughout the whole module
"""
import os
from typing import Tuple, Union

timestamps = Tuple[float, float]
note_sections = Tuple[int, int]

# Recommended by PEP 519
PathLike = Union[str, bytes, os.PathLike]
