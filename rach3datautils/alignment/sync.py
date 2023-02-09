import madmom
from rach3datautils import dataset_utils
import numpy as np
from typing import Tuple
from rach3datautils.backup_files import PathLike
import partitura as pt
from partitura.performance import Performance
import argparse as ap
from pathlib import Path


def main(root_dir: PathLike,
         frame_size: int = None,
         hop_size: int = None,
         window_size: int = 20,
         dist_func=None):
    """
    Find the timestamps corresponding to the first and last notes for each
    mp3/flac pair. Is intended to be used with the mp3 output from
    extract_and_concat.
    """
    dataset = dataset_utils.DatasetUtils(root_path=Path(root_dir))

    sessions = dataset.get_sessions(["mid", "aac", "flac"])

    for i in sessions:
        _get_timestamps(i)


def _get_timestamps(mp3_filepath: PathLike,
                    flac_path: PathLike,
                    midi_path: PathLike,
                    sample_rate: int = 44100,
                    frame_size: int = 8372,
                    hop_size: int = None,
                    window_size: int = 20,
                    dist_func=None
                    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    Get the timestamps for the first and last note given 2 audio files and a
    midi file.

    Parameters
    ----------
    mp3_filepath: path to mp3 file
    flac_path: path to flac file
    midi_path: path to midi file
    sample_rate: the sample rate to use, should be the sample rate of the audio
    being inputted.
    frame_size: how large one frame should be when loading the audio
    hop_size: how far away the next window should be
    window_size: size of window within which to compare
    dist_func: a custom distance function to be used when comparing
    windows.

    Returns a tuple where the first entry is a tuple containing first note
    sample indexes, and 2nd entry contains 2nd note sample indexes. The order
    goes mp3, flac.
    -------

    """
    if frame_size is None:
        frame_size = int(np.round(sample_rate * 0.05))
    if hop_size is None:
        hop_size = int(np.round(sample_rate * 0.005))
    if dist_func is None:
        dist_func = dist_sum

    midi = pt.load_performance_midi(midi_path)

    flac_signal = madmom.audio.FramedSignal(
        flac_path,
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate,
        num_channels=1
    )
    mp3_signal = madmom.audio.FramedSignal(
        flac_path,
        frame_size=frame_size,
        hop_size=hop_size,
        sample_rate=sample_rate,
        num_channels=1
    )

    flac_spect = np.array(
        madmom.audio.LogarithmicFilteredSpectrogram(flac_signal))
    mp3_spect = np.array(
        madmom.audio.LogarithmicFilteredSpectrogram(mp3_signal))

    flac_frame_times = np.arrange(
        flac_signal.num_frames) * (hop_size / sample_rate)

    note_array = midi.note_array()

    first_frame = abs(
        flac_frame_times - note_array["onset_sec"].min()).argmin()
    last_frame = abs(
        flac_frame_times - note_array["onset_sec"].max()).argmax()

    first_note_window = flac_spect[
                        first_frame - window_size: first_frame + window_size,
                        :]
    last_note_window = flac_spect[
                       last_frame - window_size: last_frame + window_size, :]

    mp3_start_windows = create_windows(
        arr=mp3_spect,
        stride=hop_size,
        window_size=window_size,
        start=0,
        end=first_frame * 2
    )
    mp3_end_windows = create_windows(
        arr=mp3_spect,
        stride=hop_size,
        window_size=window_size,
        start=last_frame - (mp3_spect.shape[1] - last_frame) * 2,
        end=mp3_spect.shape[1]
    )


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

    sub_window_idxs = (
            start +
            np.expand_dims(np.arange(window_size), 0) +
            np.expand_dims(np.arange(end + 1, step=stride), 0).T
    )

    return arr[sub_window_idxs]


def dist_sum(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sum(np.abs(a - b)))


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
        required=True
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
    elif args.distance_function is None:
        dist_func = dist_sum

    if args.hop_size is not None:
        hop_size = int(args.hop_size)

    if args.window_size is not None:
        window_size = int(args.window_size)

    main(
        root_dir=args.root_dir,
        frame_size=int(args.frame_size),
        hop_size=args.hop_size,
        window_size=args.window_size,
        dist_func=dist_func
    )
