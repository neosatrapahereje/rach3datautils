from typing import Tuple, Optional, TypedDict, Callable

import numpy as np
import numpy.typing as npt
import scipy.spatial as sp
from partitura.performance import Performance

from rach3datautils.exceptions import MissingFilesError
from rach3datautils.exceptions import SyncError
from rach3datautils.types import PathLike, timestamps
from rach3datautils.utils.track import Track, TrackArgs

# A tuple with start and end frame
frame_section = Tuple[int, int]


# This TypedDict is useful for specifying inputs to the load_and_sync func.
class SyncArgs(TypedDict, total=False):
    notes_index: Optional[Tuple[int, int]]
    window_size: Optional[int]
    stride: Optional[int]
    search_period: Optional[int]
    start_end_times: Optional[timestamps]


class Sync:
    """
    A class containing all necessary functions for syncing two audios based on
    their spectrogram's and a midi file synced to one audio.
    """
    WINDOW_SIZE = 500
    SEARCH_PERIOD = 180
    STRIDE = 1
    NOTES_INDEX = (0, -1)

    def __init__(self,
                 distance_func: Optional = None):
        """
        Parameters
        ----------
        distance_func : func, optional
            optionally specify a custom distance function.
            Default is cos.
        """
        if distance_func is None:
            distance_func = self.cos_dist

        self.distance_func = distance_func
        self.stride: int = self.STRIDE
        self.window_size: int = self.WINDOW_SIZE

    def calc_timestamps(self,
                        synced_track: Track,
                        nonsynced_track: Track,
                        note_array: npt.NDArray,
                        notes_index: Optional[Tuple[int, int]] = None,
                        window_size: Optional[int] = None,
                        stride: Optional[int] = None,
                        search_period: Optional[int] = None,
                        start_end_times: Optional[timestamps] = None
                        ) -> timestamps:
        """
        Get the timestamps for the first and last note given 2 audio files and
        a midi file.

        Uses the spectrogram between the two files, and finds the most likely
        place where the notes are.

        Parameters
        ----------
        note_array : npt.NDArray
            note array synced with synced_track
        window_size : int, optional
            Size of windows generated within search_period in samples
            Default: 500
        nonsynced_track : Track
            track that is not synced to midi
        synced_track : Track
            Track synced to the midi
        start_end_times : time_section, optional
            To save time on processing, optionally provide the
            times for the first and last notes in the aac file
        notes_index : Tuple[int, int], optional
            A tuple containing indexes of first and last note of the
            section to sync. Default: (0, -1)
        stride : int, optional
            how far to go between windows. Default: 1
        search_period : int, optional
            the period in seconds within which to search the aac
            file at the start and end. Default: 180

        Returns
        -------
        time_section : Tuple[float, float]
            tuple with first entry being first note time and second entry being
            second note time.

        Raises
        ------
        SyncError
            If something prevents the algorithm from working.
        """
        if window_size is not None:
            self.window_size = window_size
        if stride is not None:
            self.stride = stride
        if search_period is None:
            search_period = self.SEARCH_PERIOD
        if notes_index is None:
            notes_index = self.NOTES_INDEX
        if start_end_times is None:
            start_end_times = (0, nonsynced_track.frame_times[-1])

        first_note_time = note_array["onset_sec"][notes_index[0]]

        last_note_time = note_array["onset_sec"][notes_index[1]] + \
            note_array["duration_sec"][notes_index[1]]

        window_time = synced_track.frame_times[self.window_size]

        # The first window is generated from the first note on to avoid index
        # errors with the start of the file
        try:
            _, synced_first_note_window = synced_track.calc_log_spect_section(
                start=first_note_time,
                end=first_note_time + window_time
            )
            # The last window is generated up to the last note This is in
            # order to avoid index errors when hitting the end of the file
            _, synced_last_note_window = synced_track.calc_log_spect_section(
                start=last_note_time - window_time,
                end=last_note_time
            )
        except AttributeError as f:
            raise SyncError("Unable to generate synced track spectrogram. "
                            "Something may be wrong with the provided "
                            "note array.") from f

        try:
            sect_border_first, nonsynced_first_note_windows = \
                self.windows_within_section(
                    track=nonsynced_track,
                    section_size=search_period,
                    section_midpoint=start_end_times[0]
                )

            sect_border_last, nonsynced_last_note_windows = \
                self.windows_within_section(
                    track=nonsynced_track,
                    section_midpoint=start_end_times[1],
                    section_size=search_period
                )
        except AttributeError as f:
            raise SyncError("Unable to generate non-synced track spectrogram. "
                            "The provided start_end_times are most likely "
                            "wrong.") from f

        first_distances = self.distance_func(nonsynced_first_note_windows,
                                             synced_first_note_window)
        last_distances = self.distance_func(nonsynced_last_note_windows,
                                            synced_last_note_window)

        first_note_nonsynced_window = first_distances.argmin()
        first_note_nonsynced_frame = first_note_nonsynced_window * self.stride
        first_time = sect_border_first[0] + nonsynced_track.frame_times[
            first_note_nonsynced_frame
        ]

        last_note_nonsynced_window = np.argmin(last_distances)
        last_note_nonsynced_frame = \
            last_note_nonsynced_window * self.stride + self.window_size
        last_time = sect_border_last[0] + nonsynced_track.frame_times[
            last_note_nonsynced_frame
        ]

        return first_time, last_time

    def windows_within_section(self,
                               track: Track,
                               section_size: float,
                               section_midpoint: float,
                               ) -> Tuple[timestamps, npt.NDArray]:
        """
        Generate windows within 2 given boundaries. Returns the windows and
        the start and end points of the boundaries.

        Parameters
        ----------
        track : Track
            the Track object
        section_size : float
            size of the section is seconds
        section_midpoint : float
            midpoint of section in seconds

        Returns
        -------
        time_section_windows : Tuple[time_section, npt.NDArray]
            contains start and end times of section and a numpy array with
            all windows.
        """
        if self.window_size is None or self.stride is None:
            raise AttributeError("window_size and stride are undefined")

        (start, end), section = track.calc_log_spect_section(
            start=section_midpoint - section_size // 2,
            end=section_midpoint + section_size // 2
        )
        windows = self.create_windows(
            arr=section
        )
        return (start, end), windows

    def create_windows(self,
                       arr: npt.NDArray,
                       start: Optional[int] = None,
                       end: Optional[int] = None
                       ) -> npt.NDArray:
        """
        Create views into a given array corresponding to a sliding window.
        If no start or end is given, then the start/end of the given array is
        used.

        Parameters
        ----------
        arr : npt.NDArray
            array to be indexed
        start : int, optional
            where to start indexing
        end : int, optional
            where to end indexing

        Returns
        -------
        windows : npt.NDArray
            dim 0 is all windows, dims 1 and 2 are the actual window
            dimensions.
        """
        if start is None:
            start = 0
        if end is None:
            end = arr.shape[0]

        sub_window_ids = (
                start +
                np.expand_dims(np.arange(self.window_size), 0) +
                np.expand_dims(np.arange(
                    end - start - self.window_size, step=self.stride), 0).T
        )

        return arr[sub_window_ids, :]

    @staticmethod
    def manhatten_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        diff = np.abs(a - b)
        sums = np.sum(diff, axis=(1, 2))
        return sums

    @staticmethod
    def cos_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        b = b.flatten()
        return np.array([sp.distance.cosine(x.flatten(), b) for x in a[:]])


def load_and_sync(
        performance: Performance,
        flac: PathLike,
        audio: PathLike,
        track_args: Optional[TrackArgs] = None,
        sync_args: Optional[SyncArgs] = None,
        sync_distance_func: Optional[Callable] = None
) -> timestamps:
    """
    Function that handles loading flac and audio from a subsession and then
    syncing them using the Sync and Track objects respectively.

    Parameters
    ----------
    performance : Performance
        subsession Performance object
    flac : PathLike
        subsession flac filepath
    audio : PathLike
        subsession audio filepath
    track_args : TrackArgs, optional
        optional args to be passed to the Track object
    sync_args : SyncArgs, optional
        optional args to be passed to the Sync object
    sync_distance_func : Callable, optional
        optional custom distance function

    Returns
    -------
    time_section : Tuple[float, float]
        tuple containing timestamps of first and last note in the
        audio file
    """
    if [i for i in [performance, flac, audio] if i is None]:
        raise MissingFilesError(
            "Some files are missing from the session"
        )

    sync = Sync(distance_func=sync_distance_func)
    flac = Track(
        filepath=flac,
        **track_args
    )
    aac = Track(
        filepath=audio,
        **track_args
    )
    return sync.calc_timestamps(
        synced_track=flac,
        nonsynced_track=aac,
        note_array=performance.note_array(),
        **sync_args
    )
