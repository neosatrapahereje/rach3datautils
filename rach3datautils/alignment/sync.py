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
         dist_func=None,
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
    if dist_func is None:
        dist_func = dist_cos
    if search_period is None:
        search_period = 30
    if stride is None:
        stride = hop_size
    dataset = dataset_utils.DatasetUtils(root_path=Path(root_dir))

    sessions = dataset.get_sessions(["mid", "aac", "flac"])

    for i in sessions.values():
        _get_timestamps(i,
                        sample_rate=sample_rate,
                        frame_size=frame_size,
                        hop_size=hop_size,
                        window_size=window_size,
                        _dist_func=dist_func,
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
    dist_func: a custom distance function to be used when comparing
        windows.
    stride: how far to go between windows.
    search_period: the period in seconds within which to search the aac file
        at the start and end.

    Returns a tuple with first entry being first note time and second entry
    being second note time.
    -------
    """
    if None in [session["midi"], session["flac"], session["full_audio"]]:
        raise AttributeError("Some files are missing from the session")

    performance = session["performance"]

    flac_signal = load_signal(
        filepath=str(session["flac"]),
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate,
    )
    aac_signal = load_signal(
        filepath=str(session["full_audio"]),
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate
    )

    note_array = performance.note_array()

    flac_frame_times = np.arange(
        flac_signal.shape[0]) * (hop_size / sample_rate)
    aac_frame_times = np.arange(
        aac_signal.shape[0]) * (hop_size / sample_rate)

    search_area = int(search_period // (hop_size / sample_rate))

    first_frame = abs(
        flac_frame_times - note_array["onset_sec"].min()).argmin()
    last_frame = abs(
        flac_frame_times - note_array["onset_sec"].max()).argmin()

    # This is important because we're going to be splitting the signal into 2,
    # therefore, in order to find the last frame in the 2nd half, we need to
    # use the negative index because the regular one is wrong.
    last_frame = -(flac_signal.shape[0] - last_frame)

    # We only need two windows from the flac, so we generate those directly.
    first_note_window = get_log_spect_window(
        signal=flac_signal,
        midpoint=first_frame+window_size//2,
        window_size=window_size
    )
    last_note_window = get_log_spect_window(
        signal=flac_signal,
        midpoint=last_frame,
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
                sample_rate: int) -> madmom.audio.signal.FramedSignal:
    signal = madmom.audio.Signal(
        filepath,
        sample_rate=sample_rate,
        num_channels=1,
        norm=True
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


def dist_sum(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    diff = np.abs(a - b)
    sums = np.sum(diff, axis=(1, 2))
    return sums


def dist_cos(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    b = b.flatten()
    return np.array([sp.distance.cosine(x.flatten(), b) for x in a[:]])


def dummy_distance(a, b):
    return np.random.rand(a.shape[0])


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
        help="The root directory containing midi, flac, and mp3 files."
    )
    parser.add_argument(
        "-fs", "--frame-size",
        action="store",
        required=False,
        default=None
    )
    parser.add_argument(
        "-ws", "--window-size",
        action="store",
        required=False,
        default=None
    )
    parser.add_argument(
        "-ds", "--distance-function",
        action="store",
        required=False,
        default=None
    )
    parser.add_argument(
        "-hs", "--hop-size",
        action="store",
        required=False,
        default=None
    )
    args = parser.parse_args()

    if args.distance_function == "sum":
        dist_func = dist_sum
    else:
        dist_func = None

    if args.hop_size is not None:
        hop_size = int(args.hop_size)
    else:
        hop_size = None

    if args.window_size is not None:
        window_size = int(args.window_size)
    else:
        window_size = None

    if args.frame_size is not None:
        frame_size = int(args.frame_size)
    else:
        frame_size = None

    main(
        root_dir=args.root_dir,
        frame_size=frame_size,
        hop_size=hop_size,
        window_size=window_size,
        dist_func=dist_func
    )
