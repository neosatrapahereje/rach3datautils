import os
import filecmp
import datetime
import glob
from tqdm import tqdm
import numpy as np
from rach3datautils.extra.hashing import get_md5_hash
from rach3datautils.types import PathLike
from rach3datautils.utils.path import PathUtils
from typing import Optional, List, Union
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


def get_video_hash(filename: PathLike, video_dirs: List[PathLike]) -> None:

    # Get files with hashes
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write("# filename\thash\n")

        hashes = {}

    else:
        hashes = load_hash_file(filepath=filename)

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


def load_hash_file(filepath: PathLike) -> dict[str, str]:
    """
    Load a file with video hashes in it.

    Parameters
    ----------
    filepath: PathLike
        Path to the file containing hashes

    Returns
    -------
    hash_dict: Dict[str, str]
        A dictionary containing the filename and associated hash
    """
    data = np.loadtxt(
        fname=filepath,
        dtype=str,
        delimiter="\t",
        comments="#",
    )
    # Load hashed files
    return dict([(video[0], video[1]) for video in data])


def check_hashes(hash_file: PathLike, video_dirs: List[PathLike]) -> \
        Union[bool, list]:
    """
    Given a file with video hashes, check hashes against video files in given
    directory.

    Parameters
    ----------
    hash_file: PathLike
        file containing hashes
    video_dirs: List[PathLike]
        directory with videos to be hashed

    Returns
    -------
    True:
        if all hashes match
    mismatch_list: List[videos]
        A list of files with mismatching hashes
    """
    hashes = load_hash_file(hash_file)
    mismatched: list[str] = []
    for vdir in video_dirs:
        print(f"Checking {vdir}")
        videos = glob.glob(os.path.join(vdir, "*", "*.mp4"))

        existing_videos = [i for i in videos if os.path.basename(i) in hashes]

        if len(videos) != len(existing_videos):
            print(f"Hashes not found in the hash file for "
                  f"{abs(len(videos)-len(existing_videos))} videos.")

        for video in tqdm(existing_videos):
            vid_hash = get_md5_hash(video)

            if hashes[os.path.basename(video)] != vid_hash:
                print(f"Hash does not match for: {video}")
                mismatched.append(video)

    if mismatched:
        return mismatched
    return True


if __name__ == "__main__":

    dir1 = "/Volumes/Rach3Data_Main/LogicProjects/recordings_clean/midi"

    dir2 = "/Users/carlos/Documents/Rach3Journal/LogicProjects/recordings_clean/midi"

    backup_dir(dir1, dir2, filetype="mid")
