from pathlib import Path
from collections import defaultdict
import re
from typing import Union, Dict
from rach3datautils.backup_files import PathLike
import partitura as pt
from partitura.performance import Performance


class Session:
    """
    An object representing one session. Contains all files corresponding to
    the session.
    """
    def __init__(self,
                 videos: list[PathLike] = None,
                 audios: list[PathLike] = None,
                 midi: PathLike = None,
                 full_audio: PathLike = None,
                 flac: PathLike = None,
                 full_video: PathLike = None):
        """
        Takes filepaths as input and initializes the session object.
        """
        self.paths: Dict[str, Union[list[Path], Path, None]] = {
            "videos": None,
            "audios": None,
            "midi": None,
            "flac": None,
            "full_audio": None,
            "full_video": None
        }
        all_vars = [videos, audios, midi, full_audio, full_video, flac]
        [self.set_unknown(i) for i in all_vars if i is not None]

        # Initialize the performance object as None since we don't want to
        # perform any fancy operations to load it until it's needed.
        self._performance: Union[Performance, None] = None

    def __getitem__(self, item: str) -> Union[list[Path], Performance, Path]:
        """
        Get an item from the session. The item is loaded if it has not been
        accessed yet.

        possible items are listed in Session.paths.keys

        When accessing the midi file a partitura.Performance is returned.

        To get the filepaths use Session.paths dictionary.
        """
        if item == "midi":
            return self._midi()
        return self.paths[item]

    def _midi(self) -> Performance:
        if self._performance is None and self.paths["midi"] is not None:
            self.performance = pt.load_performance_midi(self.paths["midi"])
        return self.performance

    def __setitem__(self, key: str,
                    value: Union[PathLike, list[PathLike]]):
        """
        Set an item in the session. Will overwrite old values.
        """
        if key in ["videos", "audios"]:
            if not isinstance(value, list):
                self.paths[key] = [Path(value)]

        self.paths[key] = Path(value)

    def set_unknown(self, value: Union[PathLike, list[PathLike]]):
        filetype = PathUtils().get_type(Path(value))
        if isinstance(value, list):
            for i in value:
                self[filetype] = Path(i)
            return
        self[filetype] = Path(value)

    def append_unknown(self, value: Union[PathLike, list[PathLike]]):
        """
        Tries to append the value to the already existing ones. Falls back
        to set_unknown if the value cannot be appended.
        """
        value = Path(value)
        filetype = PathUtils().get_type(value)

        if filetype not in ["videos", "audios"]:
            return self.set_unknown(value)

        try:
            if isinstance(value, list):
                for i in value:
                    self[filetype].append(i)
                return
            self[filetype].append(value)

        except AttributeError:
            # The value was never set / is still None
            self.set_unknown(value)


class DatasetUtils:
    """
    Utilities for working with the rach3 dataset.
    """

    def __init__(self, root_path: Path = None):
        """
        Parameters
        ----------
        root_path: root path of dataset. if not specified, defaults to working
                   folder.
        """
        if root_path is None:
            root_path = "./"

        self.root = root_path

    def get_files_by_type(self, filetype: Union[str, list]) -> list[Path]:
        """
        Get all files in dataset based on filetype (mp4, midi, etc)
        Accepts any special symbols glob would accept such as *. Optionally
        specify a list of filetypes for multiple.

        Parameters
        ----------
        filetype: mp4, midi, etc
        -------
        """

        if not isinstance(filetype, list):
            filetype = [filetype]

        files = []
        [files.extend(Path(self.root).rglob('*.' + i)) for i in filetype]
        return files

    @staticmethod
    def compare_session(file_1: Path, file_2: Path) -> bool:
        """
        Determine whether 2 files are from the same recording session. For
        example, files marked v01_p001 and v01_p002 return True. However,
        files marked v01_p001 and v02_p002 would return False.

        Parameters
        ----------
        file_1: Path of first file
        file_2: Path of second file
        -------
        """

        return str(file_1)[:-7] + str(file_1)[-4:] == \
            str(file_2)[:-7] + str(file_2)[-4:]

    def get_sessions(self, filetype: Union[str, list] = None) -> \
            defaultdict[str, Session]:
        """
        Returns a dictionary with all dates and sessions. Each key is one
        session.

        Can optionally specify what filetype/s you want.
        """

        if filetype is None:
            filetype = "*"

        all_files = self.get_files_by_type(filetype=filetype)
        sessions = self.sort_by_date_and_session(all_files)

        return sessions

    @staticmethod
    def sort_by_date_and_session(files: list[Path]) -> \
            defaultdict[str, Session]:
        """
        Take a list of files and return a dictionary of form
        dict[date_session] = fileslist
        """

        sorted_files = defaultdict(Session)

        for i in files:
            date = PathUtils().get_date(i)
            session_no = PathUtils().get_session_no(i)

            if session_no is None or date is None:
                raise AttributeError(f"The path {i} could not be "
                                     f"identified.")
            else:
                sorted_files[date + "_a" + session_no].append_unknown(i)

        return sorted_files


class PathUtils:
    """
    Contains various functions that help working with paths within the dataset.
    """
    def get_type(self, path: Path) -> str:
        if self.is_valid_midi(path):
            return "midi"
        elif self.is_full_flac(path):
            return "flac"
        elif path.suffix == ".mp4":
            if self.is_full_video(path):
                return "full_video"
            return "video"
        elif path.suffix == ".aac":
            if self.is_full_audio(path):
                return "full_audio"
            return "audio"

    @staticmethod
    def get_session_no(file: Path) -> Union[str, None]:
        """
        Get the session number from a given file in the format 01, 02, etc.
        """
        for i in file.stem.split("_"):
            if re.search(pattern="(^a|^v)\\d\\d$", string=i):
                return i[-2:]
        return None

    @staticmethod
    def get_date(file: Path) -> Union[str, None]:
        """
        Get the date from a given file.
        """
        for i in file.stem.split("_"):
            if re.search(pattern="^\\d{4}-\\d{2}-\\d{2}$",
                         string=i):
                return i
        return None

    @staticmethod
    def is_full_audio(file: Path) -> bool:
        """
        Check whether a certain file is the full audio file as generated by
        extract_and_concat_audio.
        """

        return file.stem.split("_")[-1] == "full" and file.suffix == ".aac"

    @staticmethod
    def is_trimmed(file: Path) -> bool:
        """
        Check whether a file is a trimmed audio.
        """

        return file.stem.split("_")[-1] == "trimmed"

    @staticmethod
    def is_warmup(file: Path) -> bool:
        """
        Check if a file is from a warmup.
        """
        return file.stem.split("_")[0] == "warmup"

    @staticmethod
    def is_full_flac(file: Path) -> bool:
        """
        Check whether a file is a full flac recording of a session
        """
        return len(file.stem.split("_")) == 3 and file.suffix == ".flac"

    @staticmethod
    def is_valid_midi(file: Path) -> bool:
        """
        Check if a midi file is valid.
        """
        split_len = len(file.stem.split("_"))
        if split_len != 3:
            return False
        if not file.suffix == ".mid":
            return False
        return True

    @staticmethod
    def is_full_video(file: Path):
        """
        Check if a file is a full video file of a session
        """
        if file.suffix != ".mp4":
            return False

        split = file.stem.split("_")
        if "full" in split:
            return True
        return False
