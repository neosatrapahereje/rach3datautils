from partitura.performance import Performance
import argparse
from pathlib import Path
from typing import Optional, Union, List, Tuple
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.exceptions import MissingSubsessionFilesError
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.backup_files import PathLike
from rach3datautils.session import Session
import os


def main(root_dir: PathLike,
         output_dir: PathLike,
         overwrite: bool):
    """
    Detect pauses in playing based on midi file, and split audio at these
    pauses. The aim is to reduce time drifting between the video file and flac
    file.
    """
    output_dir = Path(output_dir)

    if output_dir.suffix:
        raise AttributeError("output_dir must be a path to a valid directory")

    if not output_dir.exists():
        os.mkdir(output_dir)

    dataset = DatasetUtils(root_dir)
    subsessions = dataset.get_sessions(filetype=[".mid", ".mp4", ".flac"])

    for i in subsessions:
        split_video_and_flac(
            subsession=i,
            overwrite=overwrite,
            output_dir=output_dir
        )


def split_video_and_flac(
        subsession: Session,
        output_dir: PathLike,
        overwrite: Optional[bool] = None,
        pad_size: Optional[float] = None,
        break_size: Optional[float] = None,
):
    """
    Split a video and flac according to breaks in its corresponding midi file.
    """
    if overwrite is None:
        overwrite = False
    if pad_size is None:
        pad_size = 1.

    required = [subsession.midi.file, subsession.video.trimmed,
                subsession.flac.file]
    if [i for i in required if i is None]:
        raise MissingSubsessionFilesError("Midi and video are required for "
                                          "split_video to function.")

    if not isinstance(output_dir, Path):
        output_dir: Path = Path(output_dir)

    midi = subsession.performance
    video = subsession.video.trimmed
    flac = subsession.flac.file

    duration_flac = AudioVideoTools().get_len(flac)
    first_note_time = AudioVideoTools.get_first_time(midi)
    last_note_time = AudioVideoTools.get_last_time(midi)

    splits_vid = get_split_points(
        midi=midi,
        file_duration=AudioVideoTools.get_decoded_duration(video),
        pad_left=pad_size,
        pad_right=pad_size,
    )
    splits_flac = get_split_points(
        midi=midi,
        file_duration=duration_flac,
        pad_left=first_note_time,
        pad_right=duration_flac-last_note_time,
    )
    split_at_timestamps(
        splits=splits_vid,
        file=video,
        output_dir=output_dir,
        overwrite=overwrite
    )
    split_at_timestamps(
        splits=splits_flac,
        file=flac,
        output_dir=output_dir,
        overwrite=overwrite
    )


def get_split_points(
        midi: Performance,
        file_duration: float,
        pad_left: float,
        pad_right: float,
        break_size: Optional[Union[float, int]] = None
) -> List[Tuple[float, float]]:
    """
    Calculate splits for a file according to midi timestamps. Splits in the
    second half will have their timestamps calculated from the right of the
    file, and splits in the first half will have their timestamps calculated
    from the left side of the file.

    Parameters
    ----------
    file_duration: duration of file to calculate split points for
    midi: midi file to use when identifying breaks
    pad_left: amount of silence before first note at the start
    pad_right: amount of silence after the last note
    break_size: how much time is considered a break

    Returns a list containing start and stop times of all sections
    -------
    """
    if break_size is None:
        break_size = 5

    duration = file_duration
    breaks = AudioVideoTools.find_breaks(
        midi,
        length=break_size
    )

    if breaks:
        # Calculate the exact timestamps at which to split.
        breakpoints = []
        for m in breaks:
            breakpoints.append(m[0] + ((m[1] - m[0]) / 2))

        first_note_time = AudioVideoTools.get_first_time(midi=midi)
        duration_midi = AudioVideoTools().get_last_time(midi) - first_note_time

        breakpoints -= first_note_time

        # If the break point is in the second half of the file calculate the
        # timestamp from the right. This is just for the video.
        breakpoints_lr = []
        for b in breakpoints:
            if b > duration / 2:
                breakpoints_lr.append(
                    (duration - pad_right) - (duration_midi - b)
                )
            else:
                breakpoints_lr.append(
                    b + pad_left
                )
        # Calculate exact timestamps at which to split file into sections.
        splits = calc_splits(
            breakpoints=breakpoints_lr,
            startpoint=pad_left
        )
        # Generate splits does not generate a split for the last section
        # because it doesn't have the length of the file, therefore, we add it
        # here
        splits.append((splits[-1][1], duration-pad_right))

    else:
        # In case no breaks were found
        splits = [(pad_left, duration - pad_right)]

    return splits


def split_at_timestamps(splits: list,
                        file: Path,
                        output_dir: Path,
                        overwrite: bool):
    # Split files at the calculated timestamps
    for split_no, (start, end) in enumerate(splits):
        output_path_video = output_dir.joinpath(
            file.stem + f"_split{split_no + 1}" + file.suffix
        )

        if output_path_video.exists() and not overwrite:
            return

        AudioVideoTools.extract_section(
            file=file,
            start=start,
            end=end,
            output_file=output_path_video,
        )


def calc_splits(breakpoints: list,
                startpoint: Optional[float] = None) -> list:
    if startpoint is None:
        startpoint = 0

    splits = []
    prev_point = startpoint
    for m in breakpoints:
        difference = m - prev_point
        splits.append((prev_point, prev_point + difference))
        prev_point = prev_point + difference
    return splits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Midi Based Video and Audio Splitter",
        description="Split video and audio files where there are breaks in "
                    "the music based on a midi file."
    )
    parser.add_argument(
        "-d", "--root_directory",
        action="store",
        help="Root directory of the dataset. If not set, the"
             "current working folder is used.",
        required=True
    )
    parser.add_argument(
        "-w", "--overwrite",
        action="store_true",
        help="Whether to overwrite the files if they already"
             "exist."
    )
    parser.add_argument(
        "-o", "--output_directory",
        action="store",
        help="Directory where to store output files.",
        default="./audio_split/"
    )
    args = parser.parse_args()

    main(
        root_dir=args.root_directory,
        overwrite=args.overwrite,
        output_dir=args.output_directory
    )
