import os
import filecmp
import datetime
from rach3datautils.types import PathLike
from rach3datautils.utils.path import PathUtils
from typing import Optional
from pathlib import Path


def backup_dir(
    dir1: PathLike,
    dir2: PathLike,
    filetype: Optional[str] = None,
    cut_by_date: Optional[str] = None,
):
    def by_extension(filename: Path):
        return PathUtils.check_extension(filename=filename, ext=filetype)

    def by_date(filename):
        date = PathUtils.get_date(filename)
        isodate = "-".join(date)
        date = datetime.date.fromisoformat(isodate)

        return True

    if not os.path.exists(dir1) or not os.path.exists(dir2):
        raise ValueError

    dcmp = filecmp.dircmp(
        a=dir1,
        b=dir2,
    )

    in_dir1_not_in_dir2 = dcmp.left_only
    in_dir2_not_in_dir1 = dcmp.right_only

    if filetype is not None:

        in_dir1_not_in_dir2 = filter(
            lambda x: PathUtils.check_extension(Path(x), filetype),
            in_dir1_not_in_dir2
        )

        in_dir2_not_in_dir1 = filter(
            lambda x: PathUtils.check_extension(Path(x), filetype),
            in_dir2_not_in_dir1
        )

    for fn in in_dir1_not_in_dir2:
        print(fn, "in 1, not in 2")

    for fn in in_dir2_not_in_dir1:
        print(fn, "in 2, not in 1")

    import pdb

    pdb.set_trace()
