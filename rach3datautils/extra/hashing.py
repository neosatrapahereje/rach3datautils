"""
Miscellaneous utilities
"""
import subprocess
import hashlib
import platform
from rach3datautils.types import PathLike
from typing import Union, List
import numpy as np
from tqdm import tqdm
import glob
import os


class Hashing:
    """
    Class containing functions for calculating hashes
    """
    def get_md5_hash(self, filename: PathLike) -> str:
        """
        Get MD5 hash. Will try to use an OS utility, but falls back to pure
        python in case of an error.

        Parameters
        ----------
        filename : PathLike
            path to the file

        Returns
        -------
        md5_hash : str
            hash of the file given
        """
        system = platform.system()
        try:
            if system == "Darwin":
                md5_hash = self._get_md5_hash_darwin(filename=filename)

            elif system == "Linux":
                md5_hash = self._get_md5_hash_linux(filename=filename)

            else:
                md5_hash = self._get_md5_hash_generic(filename=filename)

        except ChildProcessError:
            md5_hash = self._get_md5_hash_generic(filename=filename)

        return md5_hash

    @staticmethod
    def _get_md5_hash_generic(filename: PathLike) -> str:
        """
        Native Python MD5 hash calculation implementation, should work
        anywhere where Python works.
        """
        md5 = hashlib.md5()
        with open(filename, 'rb') as f:
            while chunk := f.read(8192):
                md5.update(chunk)

        return md5.hexdigest()

    @staticmethod
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
            raise ChildProcessError("Running md5 returned a non-zero exit "
                                    "code")
        return str(checksum_process.stdout.split()[-1])

    @staticmethod
    def _get_md5_hash_linux(filename: PathLike) -> str:
        """
        MD5 hash calculation for Linux systems, relies on md5sum being
        installed, which should be the case on most distros.
        """
        command = ["md5sum", filename]
        checksum_process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if checksum_process.returncode != 0:
            raise ChildProcessError("Running md5sum returned a non-zero exit "
                                    "code")

        return str(checksum_process.stdout.split()[0])


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
                md5_hash = Hashing().get_md5_hash(vfn)

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
    filepath : PathLike
        Path to the file containing hashes

    Returns
    -------
    hash_dict : Dict[str, str]
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
    hash_file : PathLike
        file containing hashes
    video_dirs : List[PathLike]
        directory with videos to be hashed

    Returns
    -------
    result : List[videos] or True
        if all hashes match True is returned, otherwise a list of mismatching
        files is returned
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
            vid_hash = Hashing().get_md5_hash(video)

            if hashes[os.path.basename(video)] != vid_hash:
                print(f"Hash does not match for: {video}")
                mismatched.append(video)

    if mismatched:
        return mismatched
    return True
