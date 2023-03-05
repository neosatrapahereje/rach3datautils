from pathlib import Path
from rach3datautils.path_utils import PathUtils
from rach3datautils.misc import PathLike
from rach3datautils.exceptions import IdentityError
from typing import Union, Optional, List, Tuple, Literal
from partitura.performance import Performance
import partitura as pt


full_session_id = Tuple[str, str]
session_file_types = Literal["multi", "single"]


class SessionIdentity:
    """
    Handles session identity storage and identity checks for files. All files
    from the same session should have the same session identity.
    """

    def __init__(self):
        self.date: Optional[str] = None
        self.subsession_no: Optional[str] = None
        # Full ID is useful when doing ID comparisons to avoid having to
        # compare all the variables individually.
        self.full_id: Optional[full_session_id] = None

    def __str__(self):
        return "_".join([str(i) for i in self.full_id])

    @staticmethod
    def get_file_identity(file: Path) -> full_session_id:
        """
        Returns the identity of a file in the form (date, subsession_no)
        """

        date = PathUtils.get_date(file)
        subsession_no = PathUtils.get_session_no(file)

        return date, subsession_no

    def check_identity(self, file: Path) -> bool:
        """
        Check if the identity of a file matches with the currently set one.
        If no identity has been set it will be set based on the given file.

        Raises IdentityError if the identity does not match the stored one.
        """
        file_id = self.get_file_identity(file)

        if self.full_id is None:
            self.full_id = file_id

        if file_id != self.full_id:
            raise IdentityError("Trying to set a file from the wrong "
                                "session.")

        return True


class SessionFile:
    """
    Generic class representing either a single file, or a group of files that
    represent a single recording filetype.

    Can group together files that may have multiple pieces, such that you can
    access the files as a list, or the single concatenated file as a filepath.
    Can also be used to store single files.

    Checks when a property is set whether it's valid. Also makes sure all paths
    are Path objects.
    """

    def __init__(self,
                 identity: SessionIdentity,
                 file_type: session_file_types):

        self.id: SessionIdentity = identity
        self.type: str = file_type
        self._file_list: List[Optional[Path]] = []
        self._file: Optional[Path] = None

    @property
    def file_list(self) -> List[Optional[Path]]:
        return self._file_list

    @file_list.setter
    def file_list(self, value: List[Optional[PathLike]]):
        if self.type != "multi":
            return

        values = [Path(i) for i in value]
        if not values:
            return

        [self.id.check_identity(i) for i in values]
        self._file_list = value

    @property
    def file(self) -> Path:
        return self._file

    @file.setter
    def file(self, value: Optional[PathLike]):
        if value is None:
            self._file = None
            return

        value = Path(value)
        self.id.check_identity(value)
        self._file = value


class Session:
    """
    An object representing one session. Provides a useful abstraction from just
    raw filepaths.

    Specifically, this object:
        - Guarantees all paths returned are Path objects
        - Automatically loads/caches more complex objects such as a
          Partitura Performance without any extra interaction
        - Provides detailed type hints
        - Makes it easy to add files without knowing what they are
        - Checks that all files are from the same session
    """
    LIST_PATH_KEYS = ["video", "audio"]
    PATH_KEYS = ["full_midi", "full_flac", "full_video", "full_audio"]

    def __init__(self, audio: Optional[SessionFile] = None,
                 video: Optional[SessionFile] = None,
                 midi: Optional[SessionFile] = None,
                 flac: Optional[SessionFile] = None,
                 performance: Optional[Performance] = None):
        """
        Initializes session, optionally takes a custom SessionDict. The
        session identifier is required.
        """
        self.id = SessionIdentity()

        if audio is None:
            audio = SessionFile(self.id, file_type="multi")
        if video is None:
            video = SessionFile(self.id, file_type="multi")
        if midi is None:
            midi = SessionFile(self.id, file_type="single")
        if flac is None:
            flac = SessionFile(self.id, file_type="single")

        self.audio: SessionFile = audio
        self.video: SessionFile = video
        self.midi: SessionFile = midi
        self.flac: SessionFile = flac
        self._performance: Optional[Performance] = performance

    @property
    def performance(self) -> Performance:
        """
        Get the partitura performance object. If it does not exist it will be
        loaded from the midi file. If the midi file has not been specified
        an AttributeError will be raised.
        """
        if self._performance is None:
            self._load_performance_from_midi()

        return self._performance

    def _load_performance_from_midi(self):
        midi_filepath = self.midi.file
        if midi_filepath is None:
            return

        self._performance = pt.load_performance_midi(
            self.midi.file)

    def set_unknown(self, value: Union[PathLike, list[PathLike]]) -> bool:
        """
        Set a path that you don't know the filetype off. Will append to
        existing lists and replace non list values.

        Parameters
        ----------
        value: unknown path to add to session

        Returns bool, whether the operation was successful
        -------
        """
        if not isinstance(value, list):
            value = [value]

        for i in value:
            file = Path(i)
            self.id.check_identity(file)
            filetype = PathUtils().get_type(file)

            if filetype in self.LIST_PATH_KEYS:
                attribute: SessionFile = getattr(self, filetype)
                attribute.file_list.append(file)

            elif filetype in self.PATH_KEYS:
                attribute: SessionFile = getattr(self, filetype[5:])
                attribute.file = file

            else:
                return False
        return True

    def sort_videos(self):
        self.video.file_list.sort(key=PathUtils.get_fileno_p)

    def sort_audios(self):
        self.audio.file_list.sort(key=PathUtils.get_fileno_p)
