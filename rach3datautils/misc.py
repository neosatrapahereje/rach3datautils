"""
Miscellaneous utilities

TODO
----
* These utilities only work on macOS. Update for Linux/Windows?
"""
import datetime
import os
import subprocess
import hashlib
from typing import Union


# Recommended by PEP 519
PathLike = Union[str, bytes, os.PathLike]


def change_creation_time(
    filename: PathLike,
    creation_time: Union[str, datetime.datetime],
) -> None:
    """
    Change creation time of a file.

    Parameters
    ----------
    filename : PathLike
        Path to the file.
    creation_time: str or datetime.datetime
    """
    if isinstance(creation_time, str):

        if len(creation_time.split(".")) == 2:
            # Note that this line does not check if the formatting
            # is correct! It is only for checking whether the miliseconds
            # are missing.
            ctime = creation_time
        else:
            # pad with zero miliseconds.
            ctime = f"{ctime}.0"
        date_time = datetime.datetime(ctime, "%Y-%m-%d %H:%M:%S.%f")
        date = date_time.date()
        time = date_time.time()
    elif isinstance(creation_time, datetime.datetime):
        date = creation_time.strftime("%m/%d/%Y")
        time = creation_time.strftime("%H:%M:%S")
    else:
        raise ValueError(
            "`creation_time` should be a datetime.datetime instance or a string"
            f" but is {type(creation_time)}"
        )
    command = ["SetFile", "-d", f'"{date} {time}"', os.path.abspath(filename)]
    subprocess.call(" ".join(command), shell=True)


def get_md5_hash(filename: PathLike) -> str:
    """
    Get MD5 hash

    Parameters
    ----------
    filename : PathLike
        Path to the file.

    Returns
    md5_hash : str
        The hash of the file.
    """
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        while chunk := f.read(4096):
            md5.update(chunk)

    return md5.hexdigest()
