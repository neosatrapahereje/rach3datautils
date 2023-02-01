import argparse
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.backup_files import PathLike
from pathlib import Path
import os


def main(root_dir: PathLike = None,
         output_dir: PathLike = None,
         overwrite: bool = None):
    """
    Remove silence at start and end of all given video/audio files.
    """
    if root_dir is None:
        root_dir = "./concat_audio/"
    if output_dir is None:
        output_dir = "./trimmed_silence/"
    if overwrite is None:
        overwrite = False

    root_dir = Path(root_dir)
    output_dir = Path(output_dir)
    dataset_utils = DatasetUtils(root_dir)
    a_v_tools = AudioVideoTools()

    if output_dir.suffix:
        raise AttributeError("output_dir must be a valid path to a directory")
    elif not output_dir.exists():
        os.mkdir(output_dir)

    # Gather all full audio and flac files
    all_files = [i for i in dataset_utils.get_files_by_type(
        ["mp3", "flac"]) if dataset_utils.is_full_audio(i)
                 or dataset_utils.is_full_flac(i)
                 or dataset_utils.is_full_video(i)
                 ]

    # Apply trim function to all the files.
    for i in all_files:
        # add _trimmed to the end of the file.
        output_path = output_dir.joinpath(i.stem+"_trimmed"+i.suffix)

        if output_path.exists() and not overwrite:
            continue

        if i.suffix == ".flac":
            # The flac files are quieter than the mp3, so we need a lower
            # threshold.
            threshold = -60
        else:
            threshold = -21

        a_v_tools.trim_silence(file=i,
                               output=output_path,
                               overwrite=overwrite,
                               threshold=threshold)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Silence Trimmer",
        description="Trim silence at start and end of all videos in dataset."
    )

    parser.add_argument("-d", "--root_directory",
                        action="store",
                        help="Root directory where the audio files are stored. "
                             "If not set './concat_audio is used.",
                        default="./concat_audio/")

    parser.add_argument("-w", "--overwrite",
                        action="store_true",
                        help="Whether to overwrite the trimmed files if they"
                             "already exist")

    parser.add_argument("-o", "--output_directory",
                        action="store",
                        help="Folder where the output should go.",
                        default="./trimmed_silence/")

    args = parser.parse_args()
    main(root_dir=args.root_directory,
         output_dir=args.output_directory,
         overwrite=args.overwrite)
