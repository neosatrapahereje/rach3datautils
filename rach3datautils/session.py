from pathlib import Path
from rach3datautils.path_utils import PathUtils
from rach3datautils.misc import PathLike
from typing import Union, Optional, List
from partitura.performance import Performance
import partitura as pt


class SessionFile:
    """
    Generic class for files that have multiple pieces and one combined version.
    """

    def __init__(self,
                 session: Optional[str] = None,
                 file_list: Optional[List[Optional[Path]]] = None,
                 full_file: Optional[Path] = None):
        if file_list is None:
            file_list = []

        self._file_list: List[Optional[Path]] = file_list
        self._full: Optional[Path] = full_file
        self.session: Optional[str] = session

    @property
    def file_list(self) -> List[Optional[Path]]:
        return self._file_list

    @file_list.setter
    def file_list(self, value: List[Optional[PathLike]]):
        values = [Path(i) for i in value]

        if self.session is None and values:
            self.session = PathUtils.get_date(values[0])

        if len([i for i in values if PathUtils.get_date(i) == self.session]) \
                != len(values):
            raise AttributeError("Trying to set a file from the wrong "
                                 "session.")
        self._file_list = value

    @property
    def full(self) -> Path:
        return self._full

    @full.setter
    def full(self, value: PathLike):
        value = Path(value)

        if self.session is None:
            self.session = PathUtils.get_date(value)

        if PathUtils.get_date(value) != self.session:
            raise AttributeError("Trying to set a file from the wrong "
                                 "session.")

        self._full = value


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
        - TODO: Easily utilize various scripts from .alignment
    """

    def __init__(self, session: Optional[str] = None,
                 audio: Optional[SessionFile] = None,
                 video: Optional[SessionFile] = None,
                 midi: Optional[SessionFile] = None,
                 flac: Optional[SessionFile] = None,
                 performance: Optional[Performance] = None):
        """
        Initializes session, optionally takes a custom SessionDict. The
        session identifier is required.
        """
        if audio is None:
            audio = SessionFile()
        if video is None:
            video = SessionFile()
        if midi is None:
            midi = SessionFile()
        if flac is None:
            flac = SessionFile()

        self.audio: SessionFile = audio
        self.video: SessionFile = video
        self.midi: SessionFile = midi
        self.flac: SessionFile = flac
        self._performance: Optional[Performance] = performance

        self.session = session

        self.list_path_keys = ["flac", "midi", "video", "audio"]
        self.path_keys = ["full_midi", "full_flac", "full_video", "full_audio"]

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

    @performance.setter
    def performance(self, value: Performance):
        if not isinstance(value, Performance):
            raise AttributeError("The given value is not a Performance "
                                 "object.")
        self._performance = value

    def _load_performance_from_midi(self):
        midi_filepath = self.midi.full
        if midi_filepath is None:
            return

        self._performance = pt.load_performance_midi(
            self.midi.full)

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

            if self.session is None:
                self.session = PathUtils.get_date(file)
            elif PathUtils.get_date(file) != self.session:
                raise AttributeError("The session of the file provided does "
                                     "not match with the other files in the "
                                     "current session.")

            filetype = PathUtils().get_type(file)

            if filetype in self.list_path_keys:
                attribute: SessionFile = getattr(self, filetype)
                attribute.file_list.append(file)

            elif filetype in self.path_keys:
                attribute: SessionFile = getattr(self, filetype[5:])
                attribute.full = file

            else:
                return False

        return True

    def sort_flacs(self):
        self.flac.file_list.sort(key=PathUtils.get_fileno_a)

    def sort_midis(self):
        self.midi.file_list.sort(key=PathUtils.get_fileno_a)

    def sort_videos(self):
        self.video.file_list.sort(key=PathUtils.get_fileno_p)

    def sort_audios(self):
        self.audio.file_list.sort(key=PathUtils.get_fileno_p)

