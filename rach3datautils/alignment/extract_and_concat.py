import argparse
import tempfile
from typing import Literal, Union
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.backup_files import PathLike
import os
from pathlib import Path


def main(root_dir: PathLike,
         output_dir: PathLike = None,
         overwrite: bool = None,
         audio_only: bool = None,
         flac: bool = None):
    """
    Script for concatenating session videos into one video per session. Can
    also extract and concatenate the audio and flac files.
    """
    if root_dir is None:
        raise AttributeError("No root directory was supplied!")
    if output_dir is None:
        output_dir = './concat_audio/'
    if overwrite is None:
        overwrite = False
    if audio_only is None:
        audio_only = False
    if flac is None:
        flac = False

    output = Path(output_dir)
    root_dir = Path(root_dir)
    data_utils = DatasetUtils(root_path=root_dir)
    a_d_tools = AudioVideoTools()

    # Check if the output dir exists, and if not create a new one
    if output.suffix:
        raise AttributeError("Output must be a path to a directory")
    elif not output.exists():
        os.mkdir(output)

    # First we get a list of all the video files.
    if flac:
        filetypes: list[Literal[".mp4", ".flac"]] = [".mp4", ".flac"]
    else:
        filetypes: list[Literal[".mp4"]] = [".mp4"]

    files = data_utils.get_sessions(filetype=filetypes)

    # Use a temporary working directory for audio files if extracting them.
    if audio_only:
        tempdir = tempfile.TemporaryDirectory()
        workdir = tempdir.name

    else:
        workdir = root_dir

    for s, i in files.items():
        # Create the path to the output file based on name of current
        # session.
        if audio_only:
            output_path = output.joinpath(s + "_full.aac")
        else:
            output_path = output.joinpath(s + "_full.mp4")

        if output_path.exists() and not overwrite:
            continue

        if audio_only:
            # Extract audio from all videos in session
            session_files = [
                a_d_tools.extract_audio(filepath=j,
                                        overwrite=overwrite,
                                        output=workdir.joinpath(
                                            j.with_suffix(".aac").name))
                for j in i["videos"]]
        else:
            session_files = i["videos"]

        # Concatenate session files into one
        a_d_tools.concat(
            files=session_files,
            output=output_path,
            overwrite=overwrite)

        if audio_only:
            # Delete unnecessary audio files generated during middle step.
            AudioVideoTools.delete_files(session_files)


if __name__ == "__main__":
    # Let's set up some argument parsing for ease of use.
    parser = argparse.ArgumentParser(
        prog="Extract audio/video and concatenate",
        description="Take a folder containing one or more complete sesions "
                    "and combine all the sub-videos and audios into 1 session "
                    "video or audio.")

    parser.add_argument("-d", "--root_directory", action='store',
                        help='The root directory where the dataset is '
                             'located. All folders and subfolders in this '
                             'directory will be searched.')
    parser.add_argument("-w", "--overwrite", action='store_true',
                        help='If the concatenated files exist already, '
                             'whether to overwrite them.')
    parser.add_argument("-o", "--output_dir", action='store',
                        help='Where to output processed files. If the '
                             'directory does not exist, a new one will be '
                             'created.',
                        default='./concat/')
    parser.add_argument("-a", "--audio-only", action="store_true",
                        help="Whether to output only the audio.")

    args = parser.parse_args()

    main(root_dir=args.root_directory,
         output_dir=args.output_dir,
         overwrite=args.overwrite,
         audio_only=args.audio_only)
