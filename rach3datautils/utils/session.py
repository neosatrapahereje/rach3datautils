from pathlib import Path
from typing import Union, Optional, List, Tuple, Literal

from partitura.performance import Performance

from rach3datautils.exceptions import IdentityError
from rach3datautils.types import PathLike
from rach3datautils.utils.multimedia import MultimediaTools
from rach3datautils.utils.path import PathUtils

full_session_id = Tuple[str, str]  # (date, subsession_no)
# A file can either be composed of many parts, "multi", or just be one part
# "single"
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
        Returns the identity of a given file.

        Parameters
        ----------
        file : Path

        Returns
        -------
        full_session_id : Tuple[str, str]
            contains (date, subsession_no)
        """

        date = PathUtils.get_date(file)
        subsession_no = PathUtils.get_session_no(file)

        return date, subsession_no

    def check_identity(self, file: Path) -> bool:
        """
        Check if the identity of a file matches with the currently set one.
        If no identity has been set it will be set based on the given file.

        Parameters
        ----------
        file : Path

        Returns
        -------
        bool

        Raises
        ------
        IdentityError
            if the identity of the given file does not match with the current
            stored identity
        """
        file_id = self.get_file_identity(file)

        if self.full_id is None:
            self.set(file)

        if file_id != self.full_id:
            raise IdentityError("Trying to set a file from the wrong "
                                "session.")

        return True

    def set(self, file: Path):
        """
        Set the identity from a given file. Raises IdentityError if file
        cannot be identified.

        Parameters
        ----------
        file : Path

        Returns
        -------
        None

        Raises
        ------
        IdentityError
            if the file cannot be identified
        """
        date, subsession_no = self.get_file_identity(file)

        self.date = date
        self.subsession_no = subsession_no
        self.full_id = (self.date, self.subsession_no)


class SessionFile:
    """
    Generic class representing either a single file, or a group of files that
    represent a single recording.

    Can group together files that may have multiple pieces, such that you can
    access the files as a list, or the single concatenated file as a filepath.
    Can also be used to store single files.

    Checks when a property is set whether it's valid. Also makes sure all paths
    are Path objects. The split lists are also sorted every time they're
    set to guarantee that different SessionFile objects have the same
    sorting.
    """

    def __init__(self,
                 identity: SessionIdentity,
                 file_type: session_file_types) -> None:
        """
        Parameters
        ----------
        identity : SessionIdentity
        file_type : session_file_types
        """
        self.id: SessionIdentity = identity
        self.type: str = file_type
        self._file_list: List[Optional[Path]] = []
        self._splits_list: List[Optional[Path]] = []
        self._file: Optional[Path] = None
        self._trimmed: Optional[Path] = None

    def _list_id_check(self, values: List[Path]) -> None:
        [self.id.check_identity(i) for i in values]

    @property
    def splits_list(self) -> List[Optional[Path]]:
        """
        List of files that make up the original file after it's been
        split as part of the alignment process from
        :func:`split_video_flac_mid`. This list is automatically
        sorted by date every time it's set.

        Because the list is sorted, it's easy to iterate through a
        session simply by zipping all the split lists in the session.
        To maintain this property, please refrain from modifying the
        actual list itself. Instead, when modifying the list, call the
        list setter, which auto-sorts it.

        Returns
        -------
        splits_list : List[Optional[Path]]
        """
        return self._splits_list

    @splits_list.setter
    def splits_list(self, value: List[Optional[PathLike]]) -> None:
        if not value:
            return
        paths = [Path(i) for i in value]
        self._list_id_check(values=paths)
        self._splits_list = paths
        self.sort_splits()

    def sort_splits(self) -> None:
        """
        Sort the list of splits. Does nothing if the list does not exist.
        """
        if not self.splits_list:
            return
        self.splits_list.sort(key=PathUtils().get_split_num_id)

    @property
    def file_list(self) -> List[Optional[Path]]:
        """
        The list of files that represent one larger recording.

        Returns
        -------
        file_list : List[Optional[Path]]
        """
        return self._file_list

    @file_list.setter
    def file_list(self, value: List[Optional[PathLike]]) -> None:
        if self.type != "multi":
            return
        if not value:
            return
        paths = [Path(i) for i in value]
        self._list_id_check(values=paths)
        self._file_list = paths

    @property
    def file(self) -> Union[Path, None]:
        """
        Path to the actual file represented by the object. If the object
        is multi-file (such as a video before being concatenated), file
        will return None.

        Returns
        -------
        file : Path
        """
        return self._file

    @file.setter
    def file(self, value: Optional[PathLike]) -> None:
        if value is None:
            self._file = None
            return

        value = Path(value)
        self.id.check_identity(value)
        self._file = value

    @property
    def trimmed(self) -> Union[Path, None]:
        """
        Path to the trimmed version of the file if it exists.

        Returns
        -------
        trimmed_file : Path
        """
        return self._trimmed

    @trimmed.setter
    def trimmed(self, value: Optional[PathLike]) -> None:
        if value is None:
            self._trimmed = None
            return

        value = Path(value)
        self.id.check_identity(value)
        self._trimmed = value

    def all_files(self) -> List[Path]:
        """
        Get all files currently in the SessionFile object.

        Returns
        -------
        file_list : List[PathLike]
        """
        all_files = [self.file, self.trimmed]
        all_files.extend(self.splits_list)
        all_files.extend(self.file_list)
        files_list = [i for i in all_files if i is not None]
        return files_list


class Session:
    """
    An object representing one session. Provides a useful abstraction from just
    raw filepaths.

    Specifically, this object:
        - Guarantees all paths returned are Path objects
        - Automatically loads/caches more complex objects such as a
          Partitura :external:class:`.Performance` without any extra
          interaction
        - Provides detailed type hints
        - Makes it easy to add files without knowing what they are
        - Checks that all files are from the same session
    """
    # The following definitions are useful mainly for the set_unknown
    # method. The current way this is handled may be a bit fragile and
    # there is probably room for improvement.

    # These attributes represent lists
    LIST_PATH_KEYS = ["video", "audio"]
    # These attributes represent split lists
    SPLIT_KEYS = ["split_flac", "split_midi", "split_video"]
    # These attributes represent single paths
    PATH_KEYS = ["full_midi", "full_flac", "full_video", "full_audio"]

    def __init__(self, audio: Optional[SessionFile] = None,
                 video: Optional[SessionFile] = None,
                 midi: Optional[SessionFile] = None,
                 flac: Optional[SessionFile] = None,
                 performance: Optional[Performance] = None):
        """
        Initializes session, can optionally supply any of the objects
        in the session. The session identity will automatically be set
        by scanning the filenames provided.

        Parameters
        ----------
        audio : SessionFile, optional
        video : SessionFile, optional
        midi : SessionFile, optional
        flac : SessionFile, optional
        performance : Performance, optional

        Raises
        ------
        IdentityError
            If any of the provided files are detected to have mismatching
            identities.
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
        Get the partitura :external:class:`.Performance` object. If it
        does not exist, it will be loaded from the midi file.

        Returns
        -------
        performance : Performance

        Raises
        ------
        AttributeError
            If no midi file is present within the session
        """
        if self._performance is None:
            res = self._load_performance_from_midi()
            if not res:
                raise AttributeError("Tried to load the performance but no "
                                     "midi file present in Session.")
        return self._performance

    def _load_performance_from_midi(self) -> bool:
        """Attempt to load a performance from the stored MIDI file, returns
        False if no MIDI file is found.
        """
        midi_filepath = self.midi.file
        if midi_filepath is None:
            return False
        self._performance = MultimediaTools.load_performance(midi_filepath)
        self._performance[0].sustain_pedal_threshold = 127
        return True

    def set_unknown(self, value: Union[PathLike, list[PathLike]]) -> bool:
        """
        Set a path that you don't know the filetype of while maintaining
        the sorting order of all relevant lists. This method relies
        heavily on the :attr:`.SPLIT_KEYS`, :attr:`.LIST_PATH_KEYS` and
        :attr:`.PATH_KEYS` attributes.

        Parameters
        ----------
        value : PathLike or List of PathLike
            Unknown path to add to session

        Returns
        -------
        bool
            Whether the operation was successful
        """
        if not isinstance(value, list):
            value = [value]

        for i in value:
            file = Path(i)
            self.id.check_identity(file)
            filetype = PathUtils().get_type(file)

            if filetype == "trimmed_video":
                self.video.trimmed = file

            if filetype in self.SPLIT_KEYS:
                attribute: SessionFile = getattr(self, filetype[6:])
                attribute.splits_list.append(file)
                attribute.splits_list = attribute.splits_list

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
        """
        Sort the videos within the session in chronological order. This
        includes any splits.

        Returns
        -------
        None
        """
        self.video.file_list.sort(key=PathUtils.get_fileno_p)
        self.video.sort_splits()

    def sort_audios(self):
        """
        Sort the audios within the session in chronological order. This
        includes any splits.

        Returns
        -------
        None
        """
        self.audio.file_list.sort(key=PathUtils.get_fileno_p)
        self.audio.sort_splits()

    def check_properties(self, properties: Union[List[str], str]) -> bool:
        """
        Check if a property exists in the object. Based on a string or
        multiple strings.

        Parameters
        ----------
        properties : Union[List[str], str]
            The properties to be checked.

        Returns
        -------
        bool
            True if property exists, False otherwise.
        """
        for i in properties:
            attrs = i.split(".")
            obj = self
            try:
                for j in attrs:
                    obj = getattr(obj, j)

                if obj is None:
                    return False

            except AttributeError:
                return False
        return True

    def all_files(self) -> List[Path]:
        """
        Get all the files currently stored in the Session object.

        Returns
        -------
        file_list : List[Path]
        """
        file_list = []
        for i in [self.audio, self.video, self.midi, self.flac]:
            file_list.extend(i.all_files())

        return file_list
