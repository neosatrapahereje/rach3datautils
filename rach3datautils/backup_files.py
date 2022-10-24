import os
import filecmp
import re
import datetime
import glob

import numpy as np

from rach3datautils.misc import PathLike, get_md5_hash

from typing import Optional, List


date_pat = re.compile(r"_([0-9]{4})-([0-9]{2})-([0-9]{2})_")


def check_extension(filename: PathLike, ext: str) -> bool:
    """
    True if the extension of the file is the same as the one specified
    """
    file_ext = os.path.splitext(filename)[-1]
    return file_ext == f".{ext}"


def backup_dir(
    dir1: PathLike,
    dir2: PathLike,
    filetype: Optional[str] = None,
    cut_by_date: Optional[str] = None,
):
    def by_extension(filename):
        return check_extension(filename=filename, ext=filetype)

    def by_date(filename):

        date_info = date_pat.search(filename)

        if date_info is not None:
            isodate = "-".join(date_info.groups())
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
            lambda x: check_extension(x, filetype), in_dir1_not_in_dir2
        )

        in_dir2_not_in_dir1 = filter(
            lambda x: check_extension(x, filetype), in_dir2_not_in_dir1
        )

    for fn in in_dir1_not_in_dir2:
        print(fn, "in 1, not in 2")

    for fn in in_dir2_not_in_dir1:
        print(fn, "in 2, not in 1")

    import pdb

    pdb.set_trace()


def get_video_hash(filename: PathLike, video_dirs: List[PathLike]) -> None:

    # Get files with hashes
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write("# filename\thash\n")

        hashes = {}

    else:

        data = np.loadtxt(
            fname=filename,
            dtype=str,
            delimiter="\t",
            comments="#",
        )
        # Load hashed files
        hashes = dict([(video[0], video[1]) for video in data])

    # get all videos in the video_dirs
    for vdir in video_dirs:
        video_fns = glob.glob(os.path.join(vdir, "*", "*.mp4"))

        # import pdb
        # pdb.set_trace()
        print(vdir)
        for vfn in video_fns:
            # Hashes are stored by basename
            basename = os.path.basename(vfn)
            computed = False
            # Get hash of the files
            if basename not in hashes:
                md5_hash = get_md5_hash(vfn)

                with open(filename, "a") as f:
                    f.write(f"{basename}\t{md5_hash}\n")

                hashes[basename] = md5_hash
                computed = True

                print(f"{basename}:{hashes[basename]} computed: {computed}")


if __name__ == "__main__":

    dir1 = "/Volumes/Rach3Data_Main/LogicProjects/recordings_clean/midi"

    dir2 = "/Users/carlos/Documents/Rach3Journal/LogicProjects/recordings_clean/midi"

    backup_dir(dir1, dir2, filetype="mid")
