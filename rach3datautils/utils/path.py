from pathlib import Path
from typing import Union, Literal, Tuple, get_args, List
import re
from rach3datautils.exceptions import IdentityError


filetypes = Literal["midi", "full_midi", "flac", "full_flac", "mp4",
                    "full_video", "video", "aac", "full_audio", "audio",
                    "trimmed_video", "split_midi", "split_video",
                    "split_flac"]

suffixes = Literal[".aac", ".flac", ".mp4", ".mid"]
suffixes_list: Tuple[suffixes, ...] = get_args(suffixes)


class PathUtils:
    """
    Contains various functions that help working with paths within the dataset.
    """

    def get_type(self, path: Path) -> Union[filetypes, None]:
        """
        Get the type of the given file.

        Parameters
        ----------
        path : Path

        Returns
        -------
        filetype : filetypes or None
            None if no filetype could be identified

        Notes
        -----
        Instead of returning the filetype as a string, it would be much better
        to return the list of tags the file has. For example:
        ("video", "full", "split") or ("flac", "full").

        The current way this works is fragile and overly verbose.
        """
        if self.is_warmup(path):
            return
        elif path.stem.split("_")[0] != "rach3":
            return

        if path.suffix == ".mid":
            if self.is_valid_midi(path):
                return "full_midi"
            elif self.is_split(path):
                return "split_midi"

        elif path.suffix == ".flac":
            if self.is_valid_flac(path):
                return "full_flac"
            elif self.is_split(path):
                return "split_flac"

        elif path.suffix == ".mp4":
            if self.is_trimmed(path):
                return "trimmed_video"
            elif self.is_full_video(path):
                return "full_video"
            elif self.is_valid_video(path):
                return "video"
            elif self.is_split(path):
                return "split_video"

        elif path.suffix == ".aac":
            if self.is_full_audio(path):
                return "full_audio"
            elif self.is_valid_audio(path):
                return "audio"

    @staticmethod
    def is_split(file: Path):
        """
        Determine whether a given file is a "part" file.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[-1][:5] == "split"

    @staticmethod
    def is_valid_video(file: Path) -> bool:
        """
        Checks whether a file is a basic video file.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[-1][0] == "p" and file.suffix == ".mp4"

    @staticmethod
    def is_valid_audio(file: Path) -> bool:
        """
        Checks whether a file is a basic audio file (not split, not full, etc.)

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[-1][0] == "p" and file.suffix == ".aac"

    @staticmethod
    def get_session_no(file: Path) -> Union[str, None]:
        """
        Get the session number from a given file in the format a01, a02, etc.

        Parameters
        ----------
        file : Path

        Returns
        -------
        session_no : str or None
            None if no number can be found
        """
        for i in file.stem.split("_"):
            if re.search(pattern="(^a|^v)\\d\\d$", string=i):
                return "a"+i[-2:]
        return None

    @staticmethod
    def get_date(file: Path) -> str:
        """
        Get the date from a given file in format yyyy_mm_dd.
        Raises an attribute error if a date cannot be found.

        Parameters
        ----------
        file : Path

        Returns
        -------
        date : str

        Raises
        ------
        AttributeError
            if date cannot be found
        """
        date_pat = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
        search = date_pat.search(file.name)
        if search is None:
            raise IdentityError("Date could not be identified from the given "
                                "file.")
        date = search.group()
        return date

    @staticmethod
    def check_extension(filename: Path, ext: str) -> bool:
        """
        True if the extension of the file is the same as the one specified

        Parameters
        ----------
        filename : Path
        ext : str

        Returns
        -------
        bool
        """
        return filename.suffix == f".{ext}"

    @staticmethod
    def is_full_audio(file: Path) -> bool:
        """
        Check whether a certain file is the full audio file as generated by
        extract_and_concat_audio.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[-1] == "full" and file.suffix == ".aac"

    @staticmethod
    def get_fileno_a(file: Path) -> int:
        """
        Get the file number for files using the a + 2 numbers format.

        Parameters
        ----------
        file : Path

        Returns
        -------
        file_number : int
        """
        no = re.search(pattern="a\\d{2}", string=str(file)).group()
        return int(no[-2:])

    @staticmethod
    def get_fileno_p(file: Path) -> int:
        """
        Get the file number for files using the p + 3 numbers format.

        Parameters
        ----------
        file : Path

        Returns
        -------
        file_number : int
        """
        no = re.search(pattern="p\\d{3}", string=str(file)).group()
        return int(no[-3:])

    @staticmethod
    def is_trimmed(file: Path) -> bool:
        """
        Check whether a file is a trimmed audio file.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[-1] == "trimmed"

    @staticmethod
    def is_warmup(file: Path) -> bool:
        """
        Check if a file is from a warmup.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[0] == "warmup"

    @staticmethod
    def is_valid_flac(file: Path) -> bool:
        """
        Checks if a file is a valid flac file that hasn't been modified.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.suffix == ".flac" and file.stem.split("_")[-1][0] == "a"

    @staticmethod
    def is_valid_midi(file: Path) -> bool:
        """
        Check if a midi file is valid and hasn't been modified.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.suffix == ".mid" and file.stem.split("_")[-1][0] == "a"

    @staticmethod
    def is_full_video(file: Path) -> bool:
        """
        Check if a file is a full video file of a session

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool
        """
        return file.stem.split("_")[-1] == "full" and file.suffix == ".mp4"

    @staticmethod
    def get_files_by_type(root: Path,
                          filetype: suffixes) -> List[Path]:
        """
        Return all files in the dataset of a certain type. The types should be
        found in file_suffixes.

        Parameters
        ----------
        root : Path
            where to start the recursive search
        filetype : suffixes
            .mid, .flac, etc.

        Returns
        -------
        files_list : List[Path]
            list of Path objects pointing to requested files
        """
        files = [Path(j) for j in root.rglob('*' + filetype)]
        return files
