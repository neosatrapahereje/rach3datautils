import madmom
from rach3datautils.utils import dataset_utils
from rach3datautils.exceptions import MissingSubsessionFilesError
import numpy as np
import numpy.typing as npt
from typing import Tuple, Optional, List, TypedDict
from rach3datautils.backup_files import PathLike
from rach3datautils.utils.dataset_utils import Session
import argparse as ap
from pathlib import Path
import scipy.spatial as sp
import csv
from tqdm import tqdm

# (session ID, first note, last note)
time_section = Tuple[float, float]
timestamps = Tuple[str, time_section]
frame_section = Tuple[int, int]


# These TypedDicts are useful for specifying inputs to the load_and_sync func.
class TrackArgs(TypedDict, total=False):
    frame_size: Optional[int]
    sample_rate: Optional[int]
    hop_size: Optional[float]


class SyncArgs(TypedDict, total=False):
    notes_index: Optional[Tuple[int, int]]
    window_size: Optional[int]
    stride: Optional[int]
    search_period: Optional[int]
    start_end_times: Optional[time_section]


class Track:
    """
    Class for a single track, to be used in the Sync class when representing
    the two tracks being synced.
    """
    FRAME_SIZE = 8372
    SAMPLE_RATE = 44100
    HOP_SIZE = int(np.round(SAMPLE_RATE * 0.005))

    def __init__(self,
                 filepath: PathLike,
                 frame_size: Optional[int] = None,
                 sample_rate: Optional[int] = None,
                 hop_size: Optional[float] = None):
        if frame_size is None:
            frame_size = self.FRAME_SIZE
        if sample_rate is None:
            sample_rate = self.SAMPLE_RATE
        if hop_size is None:
            hop_size = self.HOP_SIZE

        self.hop_size = hop_size
        self.sample_rate = sample_rate

        self.signal: madmom.audio.signal.FramedSignal = self.load_signal(
            filepath=filepath,
            frame_size=frame_size,
            hop_size=hop_size,
            sample_rate=sample_rate
        )
        self.frame_times: npt.NDArray = self.calc_frame_times()

    def getframe(self, time: float) -> int:
        """
        Get the closest frame to a certain timestamp is seconds. Inverse of
        gettime.
        """
        return abs((self.frame_times - time)).argmin()

    def calc_frame_times(self) -> npt.NDArray:
        return np.arange(
            self.signal.shape[0]
        ) * (self.hop_size / self.sample_rate)

    @staticmethod
    def load_signal(filepath: PathLike,
                    frame_size: int,
                    hop_size: int,
                    sample_rate: int) -> madmom.audio.signal.FramedSignal:
        signal = madmom.audio.Signal(
            str(filepath),
            sample_rate=sample_rate,
            num_channels=1,
            norm=True,
        )
        f_signal = madmom.audio.FramedSignal(
            signal=signal,
            frame_size=frame_size,
            hop_size=hop_size
        )

        return f_signal

    def calc_log_spect_section(
            self,
            start: Optional[float] = None,
            end: Optional[float] = None,
            spectrogram_clip: Optional[Tuple[int, int]] = None
    ) -> Tuple[time_section, npt.NDArray]:
        """
        Generate a certain section of the log_spectrogram given start and end
        points.
        Uses the logarithmic filtered spectrogram by default.
        If start/end points are none then the entire signal is used.

        spectrogram_clip specifies the start and end of the frequency bands
        index, useful for reducing ram usage and improving performance if you
        don't need the whole range of frequency bands.
        """
        if start is None:
            start = 0
        if end is None:
            end = self.signal.shape[0]
        if spectrogram_clip is None:
            spectrogram_clip = (10, 40)

        start = self.getframe(start)
        end = self.getframe(end)

        if end - start <= 0:
            raise AttributeError("The given end should be larger than the "
                                 "start.")

        spec = np.array(
            madmom.audio.LogarithmicFilteredSpectrogram(
                self.signal[start:end][:]
            )
        )[:, spectrogram_clip[0]:spectrogram_clip[1]]

        return (self.frame_times[start], self.frame_times[end]), spec


class Sync:
    """
    A class containing all necessary functions for syncing two audios based on
    their spectrograms and a midi file synced to one audio.
    """
    WINDOW_SIZE = 2000
    SEARCH_PERIOD = 120
    STRIDE = 1
    NOTES_INDEX = (0, -1)

    def __init__(self,
                 distance_func: Optional = None):
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
                        start_end_times: Optional[time_section] = None
                        ) -> time_section:
        """
        Get the timestamps for the first and last note given 2 audio files and
        a midi file.

        Uses the spectrogram between the two files, and finds the most likely
        place where the notes are.

        Parameters
        ----------
        note_array: note array synced with synced_track
        window_size: Size of windows generated within search_period in samples
        nonsynced_track: track that is not synced to midi
        synced_track: Track synced to the midi
        start_end_times: To save time on processing, optionally provide the
            times for the first and last notes in the aac file.
        notes_index: A tuple containing indexes of first and last note of the
            section to sync. Defaults to first and last notes (0, -1).
        stride: how far to go between windows.
        search_period: the period in seconds within which to search the aac
            file at the start and end.

        Returns a tuple with first entry being first note time and second entry
        being second note time.
        -------
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

        window_time = synced_track.frame_times[window_size]

        # The first window is generated from the first note on to avoid index
        # errors with the start of the file
        _, synced_first_note_window = synced_track.calc_log_spect_section(
            start=first_note_time,
            end=first_note_time + window_time
        )
        # The last window is generated up to the last note
        # This is in order to avoid index errors when hitting the end of the
        # file
        _, synced_last_note_window = synced_track.calc_log_spect_section(
            start=last_note_time - window_time,
            end=last_note_time
        )

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
                               ) -> Tuple[time_section, npt.NDArray]:
        """
        Generate windows within 2 given boundaries. Returns the windows and
        the start and end points of the boundaries.
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
                       arr: np.ndarray,
                       start: Optional[int] = None,
                       end: Optional[int] = None
                       ) -> npt.NDArray:
        """
        Create views into a given array corresponding to a sliding window.
        If no start or end is given, then the start/end of the given array is
        used.
        Parameters
        ----------
        arr: array to be indexed
        start: where to start indexing
        end: where to end indexing
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
        """
        Get cos distance between two windows. Could be better optimized bit
        it's already fast enough anyway.
        """
        b = b.flatten()
        return np.array([sp.distance.cosine(x.flatten(), b) for x in a[:]])


def load_and_sync(
        subsession: Session,
        track_args: Optional[TrackArgs] = None,
        sync_args: Optional[SyncArgs] = None,
        sync_distance_func: Optional = None
) -> time_section:
    """
    Function that handles loading flac and audio from a subsession and then
    syncing them using the Sync and Track objects respectively.
    """
    if [i for i in [subsession.performance, subsession.flac.file,
                    subsession.audio.file] if i is None]:
        raise MissingSubsessionFilesError(
            "Some files are missing from the session"
        )

    sync = Sync(distance_func=sync_distance_func)
    flac = Track(
        filepath=subsession.flac.file,
        **track_args
    )
    aac = Track(
        filepath=subsession.audio.file,
        **track_args
    )
    return sync.calc_timestamps(
        synced_track=flac,
        nonsynced_track=aac,
        note_array=subsession.performance.note_array(),
        **sync_args
    )


def main(root_dir: PathLike,
         notes_index: Optional[Tuple[int, int]] = None,
         output_file: Optional[PathLike] = None,
         frame_size: Optional[int] = None,
         hop_size: Optional[int] = None,
         window_size: Optional[int] = None,
         distance_function: Optional = None,
         sample_rate: Optional[int] = None,
         stride: Optional[int] = None,
         search_period: Optional[int] = None):
    """
    Wrapper function for get_timestamps that handles loading files and saving
    output to a file if specified. Useful when running this file as a script.
    """
    dataset = dataset_utils.DatasetUtils(root_path=Path(root_dir))

    sessions = dataset.get_sessions([".mid", ".aac", ".flac"])

    track_args = {
        "sample_rate": sample_rate,
        "frame_size": frame_size,
        "hop_size": hop_size
    }
    sync_args = {
        "notes_index": notes_index,
        "window_size": window_size,
        "stride": stride,
        "search_period": search_period
    }
    timestamps_list: List[timestamps] = []
    for i in tqdm(sessions):
        timestamps_list.append(
            (
                str(i),
                load_and_sync(
                    subsession=i,
                    track_args=track_args,
                    sync_args=sync_args,
                    sync_distance_func=distance_function
                )
            )
        )

    if output_file is None:
        print(timestamps_list)
        return

    with open(output_file, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["session_id", "first_note", "last_note"])
        csv_writer.writerows(timestamps_list)


if __name__ == "__main__":
    parser = ap.ArgumentParser(
        prog="Audio Synchronizer",
        description="Use midi data and spectral analysis to find timestamps "
                    "corresponding to the same note in 2 different audio "
                    "files."
    )
    parser.add_argument(
        "-d", "--root-dir",
        action="store",
        required=True,
        help="The root directory containing midi, flac, and mp3 files.",
        type=str
    )
    parser.add_argument(
        "-fs", "--frame-size",
        action="store",
        required=False,
        default=None,
        help="Frame size when loading the FramedSignal object.",
        type=int
    )
    parser.add_argument(
        "-hs", "--hop-size",
        action="store",
        required=False,
        default=None,
        help="Hop size to use when generating FramedSignal object",
        type=int
    )
    parser.add_argument(
        "-ws", "--window-size",
        action="store",
        required=False,
        default=None,
        help="Window size to use when calculating distances.",
        type=int
    )
    parser.add_argument(
        "-ds", "--distance-function",
        action="store",
        required=False,
        default=None,
        help="Distance function to use, defaults to cosine.",
        type=str
    )
    parser.add_argument(
        "-s", "--stride",
        action="store",
        required=False,
        default=None,
        help="How many samples to move the window center between windows.",
        type=int
    )
    parser.add_argument(
        "-sp", "--search-period",
        action="store",
        required=False,
        default=None,
        help="How many seconds at the start and end to look through, smaller "
             "values mean faster performance and less likely to return an "
             "incorrect result. However if the first note isn't in the search "
             "period specified it wont be found.",
        type=int
    )
    parser.add_argument(
        "-sr", "--sample-rate",
        action="store",
        required=False,
        default=None,
        help="Sample rate to use when loading the audio files.",
        type=int
    )
    parser.add_argument(
        "-o", "--output-file",
        action="store",
        required=False,
        default=None,
        help="Where to store outputs as csv, if not set will just print the "
             "results.",
        type=str
    )
    parser.add_argument(
        "-ns", "--notes-index",
        action="store",
        required=False,
        default=None,
        help="What notes to look for, defaults to first and last.",
        type=str
    )
    args = parser.parse_args()

    if args.distance_function == "manhatten":
        dist_func = Sync.manhatten_dist
    else:
        dist_func = None

    main(
        root_dir=args.root_dir,
        notes_index=args.notes_index,
        frame_size=args.frame_size,
        hop_size=args.hop_size,
        window_size=args.window_size,
        distance_function=dist_func,
        stride=args.stride,
        search_period=args.search_period,
        sample_rate=args.sample_rate,
        output_file=args.output_file
    )
