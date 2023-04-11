"""
Miscellaneous utilities
"""
import os
import subprocess
import hashlib
from typing import Union
import platform

# Recommended by PEP 519
PathLike = Union[str, bytes, os.PathLike]


def get_md5_hash(filename: PathLike) -> str:
    """
    Get MD5 hash. Will try to use an OS utility, but falls back to pure python
    in case of an error.

    Parameters
    ----------
    filename: PathLike
        Path to the file.

    Returns the hash of the file
    """
    system = platform.system()
    try:
        if system == "Darwin":
            md5_hash = _get_md5_hash_darwin(filename=filename)

        elif system == "Linux":
            md5_hash = _get_md5_hash_linux(filename=filename)

        else:
            md5_hash = _get_md5_hash_generic(filename=filename)

    except ChildProcessError:
        md5_hash = _get_md5_hash_generic(filename=filename)

    return md5_hash


def _get_md5_hash_generic(filename: PathLike) -> str:
    """
    Native Python MD5 hash calculation implementation, should work on any PC
    where Python works.
    """
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        while chunk := f.read(8192):
            md5.update(chunk)

    return md5.hexdigest()


def _get_md5_hash_darwin(filename: PathLike) -> str:
    """
    MD5 hash calculation for Apple systems, relies on the md5 command.
    """
    command = ["md5", "-q", filename]
    checksum_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if checksum_process.returncode != 0:
        raise ChildProcessError("Running md5 returned a non-zero exit code")
    return str(checksum_process.stdout.split()[-1])


def _get_md5_hash_linux(filename: PathLike) -> str:
    """
    MD5 hash calculation for Linux systems, relies on md5sum being installed.
    """
    command = ["md5sum", filename]
    checksum_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if checksum_process.returncode != 0:
        raise ChildProcessError("Running md5sum returned a non-zero exit code")

    return str(checksum_process.stdout.split()[0])
