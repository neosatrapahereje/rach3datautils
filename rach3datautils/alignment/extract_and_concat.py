import argparse
import tempfile
from typing import Literal, Optional
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.backup_files import PathLike
from rach3datautils.session import Session
import os
from pathlib import Path


def main(root_dir: PathLike,
         output_dir: Optional[PathLike] = None,
         overwrite: Optional[bool] = None,
         audio: Optional[bool] = None,
         flac: Optional[bool] = None,
         video: Optional[bool] = None):
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
    if audio is None:
        audio_only = False
    if flac is None:
        flac = False
    if video is None:
        video = True

    output = Path(output_dir)
    root_dir = Path(root_dir)
    data_utils = DatasetUtils(root_path=root_dir)

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

    for session in files.values():
        if audio:
            _aac_concat(session,
                        output.joinpath(session.session + "_full.aac"),
                        overwrite)
        if video:
            _video_concat(session,
                          output.joinpath(session.session + "_full.mp4"),
                          overwrite)
        if flac:
            _flac_concat(session,
                         output.joinpath(session.session + "_full.flac"),
                         overwrite)


def _video_concat(session: Session,
                  output: Path,
                  overwrite: Optional[bool] = None):
    if overwrite is None:
        overwrite = False

    if output.exists() and not overwrite:
        return

    session.sort_videos()

    # Concatenate session files into one
    AudioVideoTools.concat(
        files=session.video.file_list,
        output=output,
        overwrite=overwrite)

    session.video.full = output


def _aac_concat(session: Session,
                output: Path,
                overwrite: Optional[bool] = None):
    if overwrite is None:
        overwrite = False

    if output.exists() and not overwrite:
        return

    tempdir = tempfile.TemporaryDirectory()
    workdir: Path = Path(tempdir.name)

    # Extract audio from all videos in session before
    # concatenating them.
    session.audio.file_list = [
        AudioVideoTools.extract_audio(filepath=j,
                                      overwrite=overwrite,
                                      output=workdir.joinpath(
                                          j.with_suffix(".aac").name))
        for j in session.video.file_list]

    session.sort_audios()

    # Concatenate session files into one
    AudioVideoTools.concat(
        files=session.audio.file_list,
        output=output,
        overwrite=overwrite)

    session.audio.full = output


def _flac_concat(session: Session,
                 output: Path,
                 overwrite: Optional[bool] = None):
    if overwrite is None:
        overwrite = False

    if output.exists() and not overwrite:
        return

    session.sort_flacs()

    # Concatenate session files into one
    AudioVideoTools.concat(
        files=session.flac.file_list,
        output=output,
        overwrite=overwrite)

    session.flac.full = output


if __name__ == "__main__":
    # Let's set up some argument parsing for ease of use.
    parser = argparse.ArgumentParser(
        prog="Extract audio/video and concatenate",
        description="Take a folder containing one or more complete sessions "
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
    parser.add_argument("-a", "--audio", action="store_true",
                        help="Whether to output only the audio.")

    parser.add_argument("-f", "--flac", action="store_true",
                        help="Whether to concatenate the flac files.")

    parser.add_argument("-v", "--video", action="store_true",
                        help="Whether to concatenate the video files.")

    args = parser.parse_args()

    main(root_dir=args.root_directory,
         output_dir=args.output_dir,
         overwrite=args.overwrite,
         audio=args.audio,
         flac=args.flac,
         video=args.video)
