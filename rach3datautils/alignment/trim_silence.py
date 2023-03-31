from typing import Optional, List
import argparse
from rach3datautils.utils.dataset_utils import DatasetUtils
from rach3datautils.utils.video_audio_tools import AudioVideoTools
from rach3datautils.backup_files import PathLike
from rach3datautils.session import Session
from rach3datautils.alignment.sync import load_and_sync
from rach3datautils.exceptions import MissingSubsessionFilesError
from pathlib import Path
import numpy as np
from tqdm import tqdm


def main(root_dir: PathLike,
         output_dir: PathLike,
         overwrite: Optional[bool]):
    """
    Wrapper for the trim function that handles loading all files from a given
    root directory and applying trim to them. Will use the defaults present in
    get_timestamps.
    """
    if overwrite is None:
        overwrite = False

    output_dir = Path(output_dir)
    if output_dir.suffix:
        raise AttributeError("Output directory should not have a suffix as "
                             "it is a directory.")
    if not output_dir.exists():
        output_dir.mkdir()

    dataset = DatasetUtils(root_path=root_dir)

    subsessions = dataset.get_sessions(filetype=[".aac", ".flac", ".mp4",
                                                 ".mid"])

    fail_list: List[Session] = []
    for i in tqdm(subsessions):
        output_file = output_dir.joinpath(str(i.id) + "_trimmed.mp4")
        if output_file.exists() and not overwrite:
            continue

        try:
            trim(subsession=i,
                 output_file=output_file)

        except MissingSubsessionFilesError:
            fail_list.append(i)

    if fail_list:
        print("Trimming failed for following files:\n",
              [i.id for i in fail_list])


def trim(subsession: Session,
         output_file: PathLike,
         padding: Optional[float] = None):
    """
    Trim the silence from the start and end of a video based on given
    midi and flac files and output to the output file specified.
    """
    if padding is None:
        padding = 1.

    required = [subsession.audio.file, subsession.flac.file,
                subsession.midi.file, subsession.video.file]

    if [i for i in required if i is None]:
        raise MissingSubsessionFilesError(
            "Session must have the full audio, video, flac, "
            "and midi present."
        )

    # To improve speed and reduce ram usage, we run a large search with low
    # accuracy, and then we do a second more focussed search with good
    # accuracy to get the exact locations.
    start_time, end_time = load_and_sync(
        subsession=subsession,
        sync_args={
            "notes_index": (0, -1),
            "search_period": 100,
            "window_size": 100,
        },
        track_args={"hop_size": int(np.round(44100 * 0.1))}
    )
    timestamps = load_and_sync(
        subsession=subsession,
        sync_args={
            "notes_index": (0, -1),
            "search_period": 3,
            "start_end_times": (start_time, end_time),
            "window_size": 500
        },
        track_args={"hop_size": int(np.round(44100 * 0.0025))}
    )

    AudioVideoTools.extract_section(file=subsession.video.file,
                                    output_file=output_file,
                                    start=timestamps[0]-padding,
                                    end=timestamps[1]+padding)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Silence Trimmer",
        description="Trim silence at start and end of all videos in dataset "
                    "based on note detection from midi/flac files."
    )
    parser.add_argument(
        "-d", "--root_directory",
        action="store",
        help="Root directory where the dataset files are "
             "stored.",
        required=True
    )
    parser.add_argument(
        "-w", "--overwrite",
        action="store_true",
        help="Whether to overwrite the trimmed files if they"
             "already exist"
    )
    parser.add_argument(
        "-o", "--output_directory",
        action="store",
        help="Folder where the output should go.",
        required=True
    )
    args = parser.parse_args()
    main(root_dir=args.root_directory,
         output_dir=args.output_directory,
         overwrite=args.overwrite)
