import argparse
from .dataset_utils import DatasetUtils
from .video_audio_tools import AudioVideoTools
from pathlib import Path
import os


def main(args=None):
    """
    Remove silence at start and end of all concatenated audio files. To be used
    with the Rach dataset and output from extract_and_concat_audio.
    """
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

    args = parser.parse_args(args)

    root_dir = Path(args.root_directory)
    output_dir = Path(args.output_directory)
    dataset_utils = DatasetUtils(root_dir)
    a_v_tools = AudioVideoTools()

    if output_dir.suffix:
        raise AttributeError("output_dir must be a valid path to a directory")
    elif not output_dir.exists():
        os.mkdir(output_dir)

    # Gather all full audio and flac files
    all_audio_files = [i for i in dataset_utils.get_files_by_type(
        ["mp3", "flac"]) if dataset_utils.is_full_audio(i)
                       or dataset_utils.is_full_flac(i)]

    # Apply trim function to all the files.
    for i in all_audio_files:
        # add _trimmed to the end of the file.
        output_path = output_dir.joinpath(i.stem+"_trimmed"+i.suffix)

        if output_path.exists() and not args.overwrite:
            continue

        if i.suffix == ".flac":
            # The flac files are quieter than the mp3, so we need a lower
            # threshold.
            threshold = -60
        else:
            threshold = -21

        a_v_tools.trim_silence(file=i,
                               output=output_path,
                               overwrite=args.overwrite,
                               threshold=threshold)


if __name__ == "__main__":
    main()
