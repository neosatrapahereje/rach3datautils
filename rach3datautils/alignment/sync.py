import madmom
from rach3datautils import dataset_utils
from rach3datautils.exceptions import MissingSubsessionFilesError
import numpy as np
import numpy.typing as npt
from typing import Tuple, Optional, List
from rach3datautils.backup_files import PathLike
from rach3datautils.dataset_utils import Session
import argparse as ap
from pathlib import Path
import scipy.spatial as sp
import csv
from tqdm import tqdm


# (session ID, first note, last note)
timestamps = Tuple[str, float, float]


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

    timestamps_list: List[timestamps] = []
    for i in tqdm(sessions):
        timestamps_list.append(
            timestamps_spec(subsession=i, notes_index=notes_index,
                            sample_rate=sample_rate, frame_size=frame_size,
                            hop_size=hop_size, window_size=window_size,
                            _dist_func=distance_function, stride=stride,
                            search_period=search_period)
        )

    if output_file is None:
        print(timestamps_list)
        return

    with open(output_file, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["session_id", "first_note", "last_note"])
        csv_writer.writerows(timestamps_list)


def timestamps_spec(subsession: Session,
                    notes_index: Optional[Tuple[int, int]] = None,
                    sample_rate: Optional[int] = None,
                    frame_size: Optional[int] = None,
                    hop_size: Optional[int] = None,
                    window_size: Optional[int] = None,
                    _dist_func=None,
                    stride: Optional[int] = None,
                    search_period: Optional[int] = None,
                    start_end_times: Optional[Tuple[float, float]] = None
                    ) -> timestamps:
    """
    Get the timestamps for the first and last note given 2 audio files and a
    midi file.

    Uses the spectrogram between the two files, and finds the most likely
    place where the notes are.

    Parameters
    ----------
    start_end_times: To save time on processing, optionally provide the times
        for the first and last notes in the aac file.
    notes_index: A tuple containing indexes of first and last note of the
        section to sync. Defaults to first and last notes (0, -1).
    subsession: the session object containing at least the aac, flac, and midi
        files.
    sample_rate: the sample rate to use, should be the sample rate of the audio
        being inputted.
    frame_size: how large one frame should be when loading the audio
    hop_size: how far between frames in the FramedSignal
    window_size: size of window within which to compare
    _dist_func: a custom distance function to be used when comparing
        windows.
    stride: how far to go between windows.
    search_period: the period in seconds within which to search the aac file
        at the start and end.

    Returns a tuple with first entry being first note time and second entry
    being second note time.
    -------
    """
    if frame_size is None:
        frame_size = 8372
    if window_size is None:
        window_size = 2000
    if sample_rate is None:
        sample_rate = 44100
    if hop_size is None:
        hop_size = int(np.round(sample_rate * 0.005))
    if _dist_func is None:
        _dist_func = _cos_dist
    if search_period is None:
        search_period = 120
    if stride is None:
        stride = 1
    if notes_index is None:
        notes_index = (0, -1)

    if [i for i in [subsession.performance, subsession.flac.file,
                    subsession.audio.file] if i is None]:
        raise MissingSubsessionFilesError(
            "Some files are missing from the session"
        )

    performance = subsession.performance
    note_array = performance.note_array()

    flac_signal = load_signal(
        filepath=str(subsession.flac.file),
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate,
    )
    aac_signal = load_signal(
        filepath=str(subsession.audio.file),
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate,
    )

    aac_frame_times = np.arange(
        aac_signal.shape[0]
    ) * (hop_size / sample_rate)

    flac_frame_times = np.arange(
        flac_signal.shape[0]
    ) * (hop_size / sample_rate)

    if start_end_times is None:
        start_end_times = (0, aac_frame_times[-1])

    first_frame = abs(
        flac_frame_times - note_array["onset_sec"][notes_index[0]]).argmin()
    last_frame = abs(
        flac_frame_times - note_array["onset_sec"][notes_index[1]]).argmin()

    if last_frame - first_frame < window_size:
        raise IndexError("Window size is larger than the given section length."
                         " Either reduce the window size, provide a longer "
                         "section, or reduce the hop size.")

    # The first window is generated from the first note on to avoid index
    # errors with the start of the file
    first_note_window = get_log_spect_window(
        signal=flac_signal,
        midpoint=first_frame + window_size // 2,
        window_size=window_size
    )
    # The last window is generated up to the last note
    # This is in order to avoid index errors when hitting the end of the file
    last_note_window = get_log_spect_window(
        signal=flac_signal,
        midpoint=last_frame - window_size // 2,
        window_size=window_size
    )

    first_note_full_window_limits = window_clip_check(
        midpoint=start_end_times[0],
        size=search_period,
        frame_times=aac_frame_times
    )
    last_note_full_window_limits = window_clip_check(
        midpoint=start_end_times[1],
        size=search_period,
        frame_times=aac_frame_times
    )

    aac_spect_first = get_spect_section(
        signal=aac_signal,
        start=first_note_full_window_limits[0],
        end=first_note_full_window_limits[1]
    )
    aac_spect_last = get_spect_section(
        signal=aac_signal,
        start=last_note_full_window_limits[0],
        end=last_note_full_window_limits[1]
    )
    aac_start_windows = create_windows(
        arr=aac_spect_first,
        stride=stride,
        window_size=window_size,
    )
    aac_end_windows = create_windows(
        arr=aac_spect_last,
        stride=stride,
        window_size=window_size,
    )

    first_distances = _dist_func(aac_start_windows, first_note_window)
    last_distances = _dist_func(aac_end_windows, last_note_window)

    first_note_aac_window = np.argmin(first_distances)
    first_note_aac_frame = first_note_aac_window * stride
    first_note_aac_time = aac_frame_times[first_note_full_window_limits[0] +
                                          first_note_aac_frame]

    last_note_aac_window = np.argmin(last_distances)
    last_note_aac_frame = last_note_aac_window * stride + window_size
    last_note_aac_time = aac_frame_times[last_note_full_window_limits[0] +
                                         last_note_aac_frame]

    return str(subsession.id), first_note_aac_time, last_note_aac_time


def window_clip_check(midpoint: float,
                      size: float,
                      frame_times: npt.NDArray) -> Tuple[int, int]:
    # Start and end times of first note window
    start_time = max(midpoint - (size / 2), 0)
    end_time = min(midpoint + (size / 2), frame_times[-1])

    first_frame = abs(frame_times - start_time).argmin()
    last_frame = abs(frame_times - end_time).argmin()

    return first_frame, last_frame


def load_signal(filepath: PathLike,
                frame_size: int,
                hop_size: int,
                sample_rate: int) -> madmom.audio.signal.FramedSignal:
    signal = madmom.audio.Signal(
        filepath,
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


def get_log_spect_window(signal: madmom.audio.signal.FramedSignal,
                         midpoint: int,
                         window_size: int,
                         spec_func=None) -> np.ndarray:
    """
    Generate a window from a signal and return it as a numpy array.
    Uses the logarithmic filtered spectrogram by default.
    """
    if spec_func is None:
        spec_func = madmom.audio.LogarithmicFilteredSpectrogram

    return np.array(
        spec_func(
            signal[midpoint - window_size // 2:
                   midpoint + window_size // 2][:]
        )
    )[:, 10:40]


def get_spect_section(signal: madmom.audio.signal.FramedSignal,
                      start: Optional[int] = None,
                      end: Optional[int] = None,
                      spec_func=None) -> np.ndarray:
    """
    Generate a certain section of the log_spectrogram given start and end
    points. Uses the logarithmic filtered spectrogram by default.
    If start/end points are none then the entire signal is used.
    """
    if start is None:
        start = 0
    if end is None:
        end = signal.shape[0]
    if spec_func is None:
        spec_func = madmom.audio.LogarithmicFilteredSpectrogram

    spec = np.array(
        spec_func(
            signal[start:end][:]
        )
    )[:, 10:40]

    return spec


def create_windows(arr: np.ndarray,
                   stride: int,
                   window_size: int,
                   start: Optional[int] = None,
                   end: Optional[int] = None
                   ) -> np.ndarray:
    """
    Create views into a given array corresponding to a sliding window.
    If no start or end is given, then the start/end of the given array is
    used.
    Parameters
    ----------
    arr: array to be indexed
    stride: how far to move the window
    window_size: size of window
    start: where to start indexing
    end: where to end indexing
    """
    if start is None:
        start = 0
    if end is None:
        end = arr.shape[0]

    sub_window_ids = (
            start +
            np.expand_dims(np.arange(window_size), 0) +
            np.expand_dims(np.arange(
                end - start - window_size, step=stride), 0).T
    )

    return arr[sub_window_ids, :]


def _manhatten_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    diff = np.abs(a - b)
    sums = np.sum(diff, axis=(1, 2))
    return sums


def _cos_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Get cos distance between two windows. Could be better optimized bit it's
    already quite fast.
    """
    b = b.flatten()
    return np.array([sp.distance.cosine(x.flatten(), b) for x in a[:]])


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
        dist_func = _manhatten_dist
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
