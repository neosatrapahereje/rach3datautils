from pathlib import Path
from collections import defaultdict
from typing import Union, Literal, List
from rach3datautils.utils.session import Session, SessionIdentity
from rach3datautils.utils.path import PathUtils, suffixes_list, suffixes
from rach3datautils.types import PathLike


valid_input_filetypes = Union[list[suffixes], suffixes, Literal["*"]]


class DatasetUtils:
    """
    Utilities for working with the rach3 dataset.
    """

    def __init__(self, root_path: Union[PathLike, List[PathLike]] = None):
        """
        Parameters
        ----------
        root_path: root path of dataset. if not specified, defaults to working
                   folder.
        """
        if root_path is None:
            root_path: List[PathLike] = ["./"]
        if not isinstance(root_path, list):
            root_path = [root_path]

        self.root: List[Path] = [Path(i) for i in root_path]

    def get_files_by_type(self,
                          filetype: valid_input_filetypes) -> list[Path]:
        """
        Get all files in dataset based on filetype (mp4, midi, etc)
        Accepts any special symbols glob would accept such as *. Optionally
        specify a list of filetypes for multiple.

        Parameters
        ----------
        filetype: .mp4, .midi, etc
        -------
        """
        # Limiting the scope is done in order to prevent unexpected files from
        # being returned.
        if filetype == "*":
            filetype = suffixes_list

        elif not isinstance(filetype, list):
            filetype = [filetype]

        files = []
        for dirpath in self.root:
            [files.extend(PathUtils.get_files_by_type(dirpath, i))
                for i in filetype]

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

        return PathUtils.get_session_no(file_1) == \
            PathUtils.get_session_no(file_2) and \
            PathUtils.get_date(file_1) == PathUtils.get_date(file_2)

    def get_sessions(self,
                     filetype: valid_input_filetypes = None) -> List[Session]:
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
    def sort_by_date_and_session(files: list[Path]) -> List[Session]:
        """
        Take a list of files and sort them into Session objects.
        """

        sorted_files = defaultdict(Session)

        for i in files:
            session_id = SessionIdentity()
            session_id.set(i)

            sorted_files[str(session_id)].set_unknown(i)

        return list(sorted_files.values())
