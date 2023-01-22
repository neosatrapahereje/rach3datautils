import argparse
from .video_audio_tools import AudioVideoTools
from .dataset_utils import DatasetUtils
import os
from pathlib import Path


def main(args: list[str] = None):
    """
    Script for extracting audio from video files, and then concatenating it
    into the full parts.
    """

    # Let's set up some argument parsing for ease of use.
    parser = argparse.ArgumentParser(
        prog="Extract audio and concatenate",
        description="To be used with rach3 dataset. This script takes the video"
                    "files, extracts the audio, and then combines the audios "
                    "that come from the same recording. e.g the audio from "
                    "the 2 files: rach_3_2022-03-20_p001 and rach_3_2022-03-"
                    "20_p002 get combined into one file.")

    parser.add_argument("-d", "--root_directory", action='store',
                        help='The root directory where the dataset is located. '
                             'All folders and subfolders in this directory '
                             'will be searched.')
    parser.add_argument("-w", "--overwrite", action='store_true',
                        help='If the concatenated audio files exist already, '
                             'whether to overwrite them.')
    parser.add_argument("-o", "--output_dir", action='store',
                        help='Where to output processed files. If the directory'
                             'does not exist, a new one will be created.',
                        default='./concat_audio/')

    args = parser.parse_args(args)

    output = Path(args.output_dir)
    root_dir = Path(args.root_directory)
    data_utils = DatasetUtils(root_path=root_dir)
    a_d_tools = AudioVideoTools()

    # Check if the output dir exists, and if not create a new one
    if output.suffix:
        raise AttributeError("Output must be a path to a directory")
    elif not output.exists():
        os.mkdir(output)

    # First we get a list of all the video files.
    video_files = data_utils.get_sessions(filetype="mp4")

    # Use a temporary working directory for the session pieces
    temp = Path(output.joinpath("_temp/"))
    if not temp.exists():
        temp.mkdir()

    try:
        for s, i in video_files.items():
            # Create the path to the output file based on name of current session.
            output_path = output.joinpath(s + "_full.mp3")

            if output_path.exists() and not args.overwrite:
                continue

            # Extract audio from all videos in session
            audio_files = [
                a_d_tools.extract_audio(filepath=j,
                                        overwrite=args.overwrite,
                                        output=temp.joinpath(j.name)) for j in i]
            # Concatenate extracted audio files into one
            a_d_tools.concat_audio(
                audio_files=audio_files,
                output=output_path,
                overwrite=args.overwrite)

            # Delete unnecessary audio files generated during middle step.
            AudioVideoTools.delete_files(audio_files)
    except Exception as e:
        raise e
    finally:
        os.rmdir(temp)


if __name__ == "__main__":
    main()
