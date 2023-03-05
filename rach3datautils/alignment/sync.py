import madmom
from rach3datautils import dataset_utils
from rach3datautils.video_audio_tools import AudioVideoTools
import numpy as np
from typing import Tuple, Optional, List
from rach3datautils.backup_files import PathLike
from rach3datautils.dataset_utils import Session
import argparse as ap
from pathlib import Path
import scipy.spatial as sp
from timeit import default_timer as timer
import csv


# (session ID, first note, last note)
timestamps = Tuple[str, float, float]


def main(root_dir: PathLike,
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
    output to a file if specified.
    """
    dataset = dataset_utils.DatasetUtils(root_path=Path(root_dir))

    sessions = dataset.get_sessions([".mid", ".aac", ".flac"])

    timestamps_list: List[timestamps] = []
    for i in sessions:
        timestamps_list.append(
            get_timestamps(
                subsession=i,
                sample_rate=sample_rate,
                frame_size=frame_size,
                hop_size=hop_size,
                window_size=window_size,
                _dist_func=distance_function,
                stride=stride,
                search_period=search_period
            )
        )

    if output_file is None:
        print(timestamps_list)
        return

    with open(output_file, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["session_id", "first_note", "last_note"])
        csv_writer.writerows(timestamps_list)


def get_timestamps(subsession: Session,
                   sample_rate: Optional[int] = None,
                   frame_size: Optional[int] = None,
                   hop_size: Optional[int] = None,
                   window_size: Optional[int] = None,
                   _dist_func = None,
                   stride: Optional[int] = None,
                   search_period: Optional[int] = None
                   ) -> timestamps:
    """
    Get the timestamps for the first and last note given 2 audio files and a
    midi file.

    Uses the spectrogram between the two files, and finds the most likely
    place where the notes are.

    Parameters
    ----------
    subsession: the session object containing at least the aac, flac, and midi
        files
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
        window_size = 4200
    if sample_rate is None:
        sample_rate = 44100
    if hop_size is None:
        hop_size = int(np.round(sample_rate * 0.002))
    if _dist_func is None:
        _dist_func = _cos_dist
    if search_period is None:
        search_period = 30
    if stride is None:
        stride = hop_size

    if None in [subsession.midi.file, subsession.flac.file,
                subsession.audio.file]:
        raise AttributeError("Some files are missing from the session")

    performance = subsession.performance

    note_array = performance.note_array()

    aac_len = AudioVideoTools().get_len(subsession.audio.file)

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

    aac_frame_times_first = np.arange(
        aac_signal.shape[0]) * (hop_size / sample_rate)
    aac_frame_times_last = np.arange(aac_signal.shape[0]) * \
        (hop_size / sample_rate) + aac_len - search_period

    flac_frame_times = np.arange(
        flac_signal.shape[0]) * (hop_size / sample_rate)

    first_frame = abs(
        flac_frame_times - note_array["onset_sec"].min()).argmin()
    last_frame = abs(
        flac_frame_times - note_array["onset_sec"].max()).argmin()

    search_area = int(search_period // (hop_size / sample_rate))

    first_note_window = get_log_spect_window(
        signal=flac_signal,
        midpoint=first_frame + window_size // 2,
        window_size=window_size
    )

    last_note_window = get_log_spect_window(
        signal=flac_signal,
        midpoint=last_frame - window_size // 2,
        window_size=window_size
    )

    # For the aac we need to generate many windows, so we first generate a
    # large window, and then we'll split it later into smaller ones.
    # We're not interested in the middle of the audio, so we're only looking
    # at the beginning and end sections.
    aac_spect_first = get_spect_section(
        signal=aac_signal,
        start=0,
        end=search_area
    )
    aac_spect_last = get_spect_section(
        signal=aac_signal,
        start=-search_area,
        end=aac_signal.shape[0] - 1
    )
    aac_start_windows = create_windows(
        arr=aac_spect_first,
        stride=stride,
        window_size=window_size,
        start=0,
        end=search_area
    )
    aac_end_windows = create_windows(
        arr=aac_spect_last,
        stride=stride,
        window_size=window_size,
        start=(aac_spect_last.shape[0] - 1) - search_area,
        end=aac_spect_last.shape[0] - 1
    )

    first_distances = _dist_func(aac_start_windows, first_note_window)
    last_distances = _dist_func(aac_end_windows, last_note_window)

    first_note_aac_window = np.argmin(first_distances)
    first_note_aac_frame = first_note_aac_window * stride
    first_note_aac_time = aac_frame_times_first[first_note_aac_frame]

    last_note_aac_window = np.argmin(last_distances)
    last_note_aac_frame = last_note_aac_window * stride
    last_note_aac_time = aac_frame_times_last[last_note_aac_frame]

    return str(subsession.id), first_note_aac_time, last_note_aac_time


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
    )[:, 8:47]


def get_spect_section(signal: madmom.audio.signal.FramedSignal,
                      start: int,
                      end: int,
                      spec_func=None) -> np.ndarray:
    """
    Generate a certain section of the log_spectrogram given start and end
    points. Uses the logarithmic filtered spectrogram by default.
    """
    if spec_func is None:
        spec_func = madmom.audio.LogarithmicFilteredSpectrogram

    return np.array(
        spec_func(
            signal[start:end][:]
        )
    )[:, 8:47]


def create_windows(arr: np.ndarray,
                   stride: int,
                   window_size: int,
                   start: int,
                   end: int) -> np.ndarray:
    """
    Create views into a given array corresponding to a sliding window.

    Parameters
    ----------
    arr: array to be indexed
    stride: how far to move the window
    window_size: size of window
    start: where to start indexing
    end: where to end indexing
    """

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

    args = parser.parse_args()

    if args.distance_function == "manhatten":
        dist_func = _manhatten_dist
    else:
        dist_func = None

    main(
        root_dir=args.root_dir,
        frame_size=args.frame_size,
        hop_size=args.hop_size,
        window_size=args.window_size,
        distance_function=dist_func,
        stride=args.stride,
        search_period=args.search_period,
        sample_rate=args.sample_rate,
        output_file=args.output_file
    )
