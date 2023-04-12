from typing import Optional
from rach3datautils.utils.multimedia import MultimediaTools
from rach3datautils.types import PathLike
from rach3datautils.alignment.sync import load_and_sync
from rach3datautils.exceptions import MissingFilesError
import numpy as np
from partitura.performance import Performance


def trim(audio: PathLike,
         flac: PathLike,
         midi: PathLike,
         video: PathLike,
         performance: Performance,
         output_file: PathLike,
         padding: Optional[float] = None):
    """
    Trim the silence from the start and end of a video based on given
    midi and flac files and output to the output file specified.

    Parameters
    ----------
    audio : PathLike
        subsession audio filepath
    flac : PathLike
        subsession flac filepath
    midi : PathLike
        subsession midi filepath
    video : PathLike
        subsession video filepath
    performance : Performance
        subsession performance filepath
    output_file : PathLike
        where to output the new file including filename
    padding : float, optional
        an amount in seconds to add around the first and last note.
        Default is 1

    Returns
    -------
    None
    """
    if padding is None:
        padding = 1.

    required = [audio, flac, midi, video]

    if [i for i in required if i is None]:
        raise MissingFilesError(
            "Session must have the full audio, video, flac, "
            "and midi present."
        )

    # To improve speed and reduce ram usage, we run a large search with low
    # accuracy, and then we do a second more focussed search with good
    # accuracy to get the exact locations.
    start_time, end_time = load_and_sync(
        performance=performance,
        flac=flac,
        audio=audio,
        sync_args={
            "notes_index": (0, -1),
            "search_period": 100,
            "window_size": 100,
        },
        track_args={"hop_size": int(np.round(44100 * 0.1))}
    )
    timestamps = load_and_sync(
        performance=performance,
        flac=flac,
        audio=audio,
        sync_args={
            "notes_index": (0, -1),
            "search_period": 3,
            "start_end_times": (start_time, end_time),
            "window_size": 500
        },
        track_args={"hop_size": int(np.round(44100 * 0.0025))}
    )

    MultimediaTools.extract_section(file=video,
                                    output_file=output_file,
                                    start=timestamps[0]-padding,
                                    end=timestamps[1]+padding)
