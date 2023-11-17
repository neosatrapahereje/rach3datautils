from collections import defaultdict
from pathlib import Path
from typing import Union, Literal, List, Optional

from rach3datautils.exceptions import IdentityError
from rach3datautils.types import PathLike
from rach3datautils.utils.path import PathUtils, suffixes_list, suffixes
from rach3datautils.utils.session import Session, SessionIdentity

valid_input_filetypes = Union[list[suffixes], suffixes, Literal["*"]]


class DatasetUtils:
    """
    Utilities for working with the rach3 dataset.
    """

    def __init__(self, root_path: Optional[Union[PathLike,
                                           List[PathLike]]] = None):
        """
        Parameters
        ----------
        root_path : PathLike or List[PathLike], optional
            root path of dataset. Default is "./"
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
        Also accepts "*". Optionally specify a list of filetypes.

        Parameters
        ----------
        filetype : valid_input_filetypes
            .mp4, .mid, etc. or [".mp4", ".mid", ...]

        Returns
        -------
        files_list : List[Path]
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
        file_1 : Path
            Path of first file
        file_2 : Path
            Path of second file

        Returns
        -------
        bool
            whether the two files are from the same session
        """
        return PathUtils.get_session_no(file_1) == \
            PathUtils.get_session_no(file_2) and \
            PathUtils.get_date(file_1) == PathUtils.get_date(file_2)

    def get_sessions(self,
                     filetype: Optional[valid_input_filetypes] = None) -> \
            List[Session]:
        """
        Returns a list with all sessions.
        Can optionally specify what filetype/s you want.

        Parameters
        ----------
        filetype : valid_input_filetypes, optional
            .mp4, .mid, etc. or [".mp4", ".mid", ...]. default is "*"

        Returns
        -------
        session_list : List[Session]
        """
        if filetype is None:
            filetype = "*"

        all_files = self.get_files_by_type(filetype=filetype)
        sessions = self.sort_by_date_and_session(all_files)

        return sessions

    @staticmethod
    def sort_by_date_and_session(files: List[Path]) -> List[Session]:
        """
        Take a list of files and sort them into Session objects.

        Parameters
        ----------
        files : List[Path]

        Returns
        -------
        session_list : List[Session]
        """
        sorted_files = defaultdict(Session)

        for i in files:
            try:
                session_id = SessionIdentity()
                session_id.set(i)

                sorted_files[str(session_id)].set_unknown(i)
            except IdentityError:
                continue

        return list(sorted_files.values())

    @staticmethod
    def remove_noncomplete(subsession_list: List[Session],
                           required: Union[List[str], str]):
        """
        Return a list of subsessions with only subsessions that have the
        required attributes.

        Parameters
        ----------
        subsession_list : List[Session]
        required : Union[List[str], str]
            required attributes, e.g. performance, midi.file.

        Returns
        -------
        new_subsession_list
            a new list that contains only subsessions with the required
            attributes.
        """
        return [i for i in subsession_list if i.check_properties(required)]
