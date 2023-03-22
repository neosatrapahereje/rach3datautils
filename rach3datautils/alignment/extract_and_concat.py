import argparse
import tempfile
from typing import Literal, Optional
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.backup_files import PathLike
from rach3datautils.session import Session
from rach3datautils.exceptions import MissingSubsessionFilesError
import os
from pathlib import Path
from tqdm import tqdm


def main(root_dir: PathLike,
         output_dir: PathLike,
         overwrite: Optional[bool] = None,
         audio: Optional[bool] = None,
         video: Optional[bool] = None):
    """
    Script for concatenating session videos into one video per session. Can
    also extract and concatenate the audio.
    """
    output = Path(output_dir)
    root_dir = Path(root_dir)
    data_utils = DatasetUtils(root_path=root_dir)

    # Check if the output dir exists, and if not create a new one
    if output.suffix:
        raise AttributeError("Output must be a path to a directory")
    elif not output.exists():
        os.mkdir(output)

    filetypes: list[Literal[".mp4"]] = [".mp4"]

    sessions = data_utils.get_sessions(filetype=filetypes)

    for session in tqdm(sessions):
        extract_and_concat(
            session=session,
            output=output,
            audio=audio,
            video=video,
            overwrite=overwrite
        )


def extract_and_concat(session: Session,
                       output: Path,
                       audio: Optional[bool] = None,
                       video: Optional[bool] = None,
                       overwrite: Optional[bool] = None):
    """
    Extract audio from videos and concatenate both audios and videos into one
    file for each subsession.
    Parameters
    ----------
    session: subsession object
    output
    audio
    video
    overwrite

    Returns
    -------

    """
    if overwrite is None:
        overwrite = False
    if audio is None:
        audio = True
    if video is None:
        video = True

    if not session.video.file_list:
        raise MissingSubsessionFilesError("Video files expected in "
                                          "subsession, but found none")

    if audio:
        _aac_concat(session,
                    output.joinpath(str(session.id) +
                                    "_full.aac"),
                    overwrite)
    if video:
        _video_concat(session,
                      output.joinpath(str(session.id) + "_full.mp4"),
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

    session.video.file = output


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

    session.audio.file = output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Extract audio/video and concatenate",
        description="Take a folder containing one or more complete sessions "
                    "and combine all the sub-videos and audios into 1 session "
                    "video or audio."
    )
    parser.add_argument(
        "-d", "--root_directory",
        action='store',
        help='The root directory where the dataset is '
             'located. All folders and subfolders in this '
             'directory will be searched.'
    )
    parser.add_argument(
        "-w", "--overwrite", action='store_true',
        help='If the concatenated files exist already, '
             'whether to overwrite them.'
    )
    parser.add_argument(
        "-o", "--output_dir", action='store',
        help='Where to output processed files. If the '
             'directory does not exist, a new one will be '
             'created.',
        default='./concat/'
    )
    parser.add_argument(
        "-a", "--audio", action="store_true",
        help="Whether to output only the audio."
    )
    parser.add_argument(
        "-v", "--video", action="store_true",
        help="Whether to concatenate the video files."
    )

    args = parser.parse_args()

    main(
        root_dir=args.root_directory,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        audio=args.audio,
        video=args.video
    )
