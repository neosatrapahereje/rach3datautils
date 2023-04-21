import tempfile
from pathlib import Path
from typing import Optional, List

from rach3datautils.exceptions import MissingFilesError
from rach3datautils.utils.multimedia import MultimediaTools
from rach3datautils.utils.session import Session


def extract_and_concat(session: Session,
                       output: Path,
                       audio: Optional[bool] = None,
                       video: Optional[bool] = None,
                       overwrite: Optional[bool] = None,
                       reencode: Optional[bool] = None) -> List[Path]:
    """
    Extract audio from videos and concatenate both audios and videos into one
    file for each subsession.

    Parameters
    ----------
    reencode : bool, optional
    session : Session
        Subsession object
    output : Path
        Where to output file
    audio : bool, optional
        Whether to do subsession audio
    video : bool, optional
        Whether to do subsession video
    overwrite : bool, optional
        Whether to overwrite already existing files

    Returns
    -------
    None
    """
    if overwrite is None:
        overwrite = False
    if audio is None:
        audio = True
    if video is None:
        video = True

    if not session.video.file_list:
        raise MissingFilesError("Video files expected in subsession, but "
                                "found none")
    elif not audio and not video:
        raise AttributeError("Either audio or video should be true when "
                             "running extract_and_concat.")

    outputs = []
    if audio:
        audio_output = output.joinpath(str(session.id) + "_full.aac")
        outputs.append(audio_output)
        _aac_concat(session=session,
                    output=audio_output,
                    overwrite=overwrite,
                    reencode=reencode)
    if video:
        video_output = output.joinpath(str(session.id) + "_full.mp4")
        outputs.append(video_output)
        _video_concat(session=session,
                      output=video_output,
                      overwrite=overwrite,
                      reencode=reencode)

    return outputs


def _video_concat(session: Session,
                  output: Path,
                  overwrite: Optional[bool] = None,
                  reencode: Optional[bool] = None):
    if overwrite is None:
        overwrite = False

    if output.exists() and not overwrite:
        return

    session.sort_videos()

    # Concatenate session files into one
    MultimediaTools.concat(
        files=session.video.file_list,
        output=output,
        overwrite=overwrite,
        reencode=reencode
    )

    session.video.file = output


def _aac_concat(session: Session,
                output: Path,
                overwrite: Optional[bool] = None,
                reencode: Optional[bool] = None):
    if overwrite is None:
        overwrite = False

    if output.exists() and not overwrite:
        return

    tempdir = tempfile.TemporaryDirectory()
    workdir: Path = Path(tempdir.name)

    # Extract audio from all videos in session before
    # concatenating them.
    session.audio.file_list = [
        MultimediaTools.extract_audio(filepath=j,
                                      overwrite=overwrite,
                                      output=workdir.joinpath(
                                          j.with_suffix(".aac").name))
        for j in session.video.file_list]

    session.sort_audios()

    # Concatenate session files into one
    MultimediaTools.concat(
        files=session.audio.file_list,
        output=output,
        overwrite=overwrite,
        reencode=reencode
    )
    session.audio.file = output
