from pathlib import Path
from rach3datautils.misc import PathLike
from rach3datautils.path_utils import PathUtils
from typing import TypedDict, Literal, Union
from partitura.performance import Performance
import partitura as pt


# For the sake of type hints lets define exactly what's in a session
class SessionDict(TypedDict, total=False):
    videos: list[PathLike]
    audios: list[PathLike]
    midi: list[PathLike]
    full_audio: PathLike
    flac: PathLike
    full_video: PathLike
    full_midi: PathLike
    performance: Performance


# I wish this wasn't necessary but TypedDict is a little more basic than I'd
# like
session_key_types = Literal["videos", "audios", "midi", "full_audio", "flac",
                            "full_video", "full_midi", "performance"]
session_item_types = Union[list[PathLike], PathLike, Performance]


class Session:
    """
    An object representing one session. Contains all files corresponding to
    the session.
    """

    def __init__(self,
                 videos: list[PathLike] = None,
                 audios: list[PathLike] = None,
                 midi: list[PathLike] = None,
                 flac: PathLike = None,
                 full_audio: PathLike = None,
                 full_video: PathLike = None,
                 full_midi: PathLike = None):
        """
        Takes filepaths as input and initializes the session object.
        """
        self.files: SessionDict = {}

        if videos is not None:
            self.files["videos"] = videos
        if audios is not None:
            self.files["audios"] = audios
        if midi is not None:
            self.files["midi"] = midi
        if full_audio is not None:
            self.files["full_audio"] = full_audio
        if flac is not None:
            self.files["flac"] = flac
        if full_video is not None:
            self.files["full_video"] = full_video
        if full_midi is not None:
            self.files["full_midi"] = full_midi

    def __getitem__(self, item: session_key_types) -> session_item_types:
        """
        Get an item from the session. The item is loaded if it has not been
        accessed yet.

        possible items are listed in Session.paths.keys. Additionally a
        performance can be requested which is loaded on demand from the midi
        file.
        """
        if item == "performance":
            return self._load_midi()

        return self.files[item]

    def _load_midi(self) -> Performance:
        if "midi" not in self.files.keys():
            raise KeyError("No midi path found in session")

        elif "performance" not in self.files.keys():
            self.files["performance"] = pt.load_performance_midi(
                self.files["full_midi"])

        return self.files["performance"]

    def __setitem__(self, key: session_key_types,
                    value: session_item_types):
        """
        Set an item in the session. Will overwrite old values, including
        lists.
        """
        self.files[key] = value

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
            filetype = PathUtils().get_type(Path(i))
            if filetype == "video":
                self["videos"].append(Path(i))
            elif filetype == "audio":
                self["audios"].append(Path(i))
            elif filetype in self.files.keys():
                self[filetype] = Path(i)
            else:
                return False
        return True
