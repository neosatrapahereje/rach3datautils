import datetime
import filedate
from rach3datautils.types import PathLike
from typing import Union


def change_creation_time(
    filename: PathLike,
    creation_time: Union[str, datetime.datetime],
) -> None:
    """
    Change creation time of a file.

    Parameters
    ----------
    filename: PathLike
        path to the file
    creation_time: str or datetime.datetime
        new creation time to set

    Returns
    -------
    None
    """
    if isinstance(creation_time, str):

        if len(creation_time.split(".")) == 2:
            # Note that this line does not check if the formatting
            # is correct! It is only for checking whether the miliseconds
            # are missing.
            ctime = creation_time
        else:
            # pad with zero miliseconds.
            ctime = f"{creation_time}.0"
        date_time = datetime.datetime(ctime, "%Y-%m-%d %H:%M:%S.%f")
        date = date_time.date()
        time = date_time.time()
    elif isinstance(creation_time, datetime.datetime):
        date = creation_time.strftime("%m/%d/%Y")
        time = creation_time.strftime("%H:%M:%S")
    else:
        raise ValueError(
            "`creation_time` should be a datetime.datetime instance or a "
            f"string but is {type(creation_time)}"
        )
    file_date = filedate.File(filename)
    file_date.set(created=f"{date} {time}")
