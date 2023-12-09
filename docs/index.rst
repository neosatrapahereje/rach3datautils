.. rach3datautils documentation master file, created by
   sphinx-quickstart on Sat Apr 22 15:49:17 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to rach3datautils's documentation!
==========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   ./sources/modules

About
-----
Rach3datautils is the official library for working with the Rach3
dataset. It contains various utility functions that help speed up any
workflow that uses the dataset. This package provides the following:

Alignment
  The alignment module contains an automated pipeline for fixing the
  alignment between the videos and FLAC/MIDI files.
File Grouping
  The :class:`.DatasetUtils` and :class:`.Session` objects make it easy
  to scan all files in the dataset root and automatically sort them.
Utility Functions
  Other useful functions such as :class:`.Hashing`, :func:`.backup_dir`
  and :func:`.change_creation_time`.



To see some examples on how to use rach3datautils, check out the scripts
`here`_.

.. _here: https://github.com/neosatrapahereje/rach3datautils/tree/main/bin

Sessions
--------
The :class:`.Session` object is the basic organizational unit for the
dataset. One session is equivalent to one recording/practice session.
Therefore, a single :class:`.Session` object will include the video, FLAC,
MIDI, :external:class:`partitura.performance.Performance`, and any other
files/objects that may correspond to that one period of time.

:class:`.Session` objects are automatically built by the
:class:`.DatasetUtils` object when it scans a directory. Therefore, to
easily get a list of sessions, simply call :meth:`.DatasetUtils.get_sessions`.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
