#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os

from setuptools import setup

# Package meta-data.
NAME = "rach3datautils"
DESCRIPTION = "A package for handling the Rach3 dataset"
KEYWORDS = ""
URL = "https://github.com/neosatrapahereje/rach3datautils"
EMAIL = "carloscancinochacon@gmail.com"
AUTHOR = "Carlos Cancino-Chacón"
REQUIRES_PYTHON = ">=3.9"
VERSION = "0.0.1"

# Required packages
REQUIRED = [
    "partitura~=1.4.1",
    "ffmpeg-python~=0.2.0",
    "numpy~=1.26.2",
    "madmom",
    "scipy~=1.11.3",
    "tqdm~=4.66.1",
    "fastdtw~=0.3.4"
]

# Optional
extra = ["filedate", "python-dotenv"]
EXTRAS = {
    "EXTRA": extra,
}

SCRIPTS = ["bin/R3GetVideoHash"]

here = os.path.abspath(os.path.dirname(__file__))

try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    with open(os.path.join(here, NAME, "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=KEYWORDS,
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    scripts=SCRIPTS,
    # license="Apache 2.0",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
