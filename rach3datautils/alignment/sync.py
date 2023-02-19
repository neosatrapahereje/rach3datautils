import madmom
from rach3datautils import dataset_utils
import numpy as np
from typing import Tuple
from rach3datautils.backup_files import PathLike
from rach3datautils.dataset_utils import Session
import argparse as ap
from pathlib import Path
import scipy.spatial as sp


def main(root_dir: PathLike,
         frame_size: int = None,
         hop_size: int = None,
         window_size: int = None,
         distance_function=None,
         sample_rate: int = None,
         stride: int = None,
         search_period: int = None):
    """
    Find the timestamps corresponding to the first and last notes for each
    aac/flac pair. Is intended to be used with the aac output from
    extract_and_concat.
    """
    if frame_size is None:
        frame_size = 8372
    if window_size is None:
        window_size = 4200
    if sample_rate is None:
        sample_rate = 44100
    if hop_size is None:
        hop_size = int(np.round(sample_rate * 0.0006))
    if distance_function is None:
        distance_function = _cos_dist
    if search_period is None:
        search_period = 30
    if stride is None:
        stride = hop_size

    dataset = dataset_utils.DatasetUtils(root_path=Path(root_dir))

    sessions = dataset.get_sessions([".mid", ".aac", ".flac"])

    for i in sessions.values():
        _get_timestamps(i,
                        sample_rate=sample_rate,
                        frame_size=frame_size,
                        hop_size=hop_size,
                        window_size=window_size,
                        _dist_func=distance_function,
                        stride=stride,
                        search_period=search_period)


def _get_timestamps(session: Session,
                    sample_rate: int,
                    frame_size: int,
                    hop_size: int,
                    window_size: int,
                    _dist_func,
                    stride: int,
                    search_period: int
                    ) -> Tuple[int, int]:
    """
    Get the timestamps for the first and last note given 2 audio files and a
    midi file.

    Uses the spectrogram between the two files, and finds the most likely
    place where the notes are.

    Parameters
    ----------
    session: the session object containing at least the aac, flac, and midi
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
    if None in [session.midi.full, session.flac.full, session.audio.full]:
        raise AttributeError("Some files are missing from the session")

    performance = session.performance
    note_array = performance.note_array()

    window_time = window_size * (hop_size / sample_rate)

    first_note_time = note_array["onset_sec"].min()
    last_note_time = note_array["onset_sec"].max()

    flac_signal_first = load_signal(
        filepath=str(session.flac.full),
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate,
        start=first_note_time,
        stop=first_note_time + window_time
    )
    aac_signal = load_signal(
        filepath=str(session.audio.full),
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate
    )

    flac_frame_times = np.arange(
        flac_signal.shape[0]) * (hop_size / sample_rate)
    aac_frame_times = np.arange(
        aac_signal.shape[0]) * (hop_size / sample_rate)

    search_area = int(search_period // (hop_size / sample_rate))

    first_frame = abs(
        flac_frame_times - first_note_time).argmin()
    last_frame = abs(
        flac_frame_times - last_note_time).argmin()

    # This is important because we're going to be splitting the signal into 2,
    # therefore, in order to find the last frame in the 2nd half, we need to
    # use the negative index because the regular one is wrong.
    last_frame = -(flac_signal.shape[0] - last_frame)

    # We only need two windows from the flac, so we generate those directly.
    # It's important to generate the first window with the note at the
    # beginning, and the last window with the note at the end, because there
    # may not be enough samples otherwise.
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
        end=aac_signal.shape[0]-1
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

    distances = _dist_func(aac_start_windows, first_note_window)

    first_note_aac_window = np.argmin(distances)
    first_note_aac_frame = first_note_aac_window * stride
    first_note_aac_time = aac_frame_times[first_note_aac_frame]

    return first_note_aac_time


def load_signal(filepath: PathLike,
                frame_size: int,
                hop_size: int,
                sample_rate: int,
                start: float,
                stop: float) -> madmom.audio.signal.FramedSignal:
    signal = madmom.audio.Signal(
        filepath,
        sample_rate=sample_rate,
        num_channels=1,
        norm=True,
        start=start,
        stop=stop
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
        sample_rate=args.sample_rate
    )
