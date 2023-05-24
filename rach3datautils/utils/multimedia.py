import os
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Optional, Union, overload, Literal, List, Dict, Tuple

import ffmpeg
import numpy as np
import numpy.typing as npt
import partitura as pt
from partitura.performance import Performance
from partitura.performance import PerformedPart
from partitura.utils.music import slice_ppart_by_time

from rach3datautils.config import LOGLEVEL
from rach3datautils.types import PathLike, timestamps

FFMPEG_LOGLEVELS = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "panic"
}
FFMPEG_LOGLEVEL = FFMPEG_LOGLEVELS[LOGLEVEL]


class MultimediaTools:
    """
    Contains useful ffmpeg pipelines for working with audio and video, as well
    as other utility functions for working with midi files.
    """
    @staticmethod
    def extract_audio(filepath: Path, output: Path = None,
                      overwrite: bool = False) -> Path:
        """
        Extract audio from a video file. Returns the filepath of the new audio
        file.
        If no output is specified outputs the file in the same folder
        as the original video.

        Parameters
        ----------
        filepath : Path
        output : Path
        overwrite : bool

        Returns
        -------
        new_file : Path
        """

        if output is None:
            output = Path(os.path.join("..", "audio_files",
                                       filepath.stem + "_audio.mp3"))
        elif not output.suffix == ".aac":
            raise AttributeError("Output must either be None or a valid path "
                                 "to a .acc file")

        if output.is_file() and not overwrite:
            return output

        video = ffmpeg.input(filepath)
        out = ffmpeg.output(video.audio, filename=output, c="copy",
                            loglevel=FFMPEG_LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()
        return output

    @staticmethod
    def concat(files: List[Optional[Path]],
               output: Path,
               overwrite: Optional[bool] = None,
               reencode: Optional[bool] = None) -> Union[Path, None]:
        """
        Takes a list of audio or video files and concatenates them into one
        file. They will be concatenated in the order present within the list.

        If only one file is given, it will simply be copied to the output
        location.

        Parameters
        ----------
        files : List[Optional[Path]]
        output : Path
        overwrite : bool, optional
            default is False
        reencode : bool, optional
            default is False

        Returns
        -------
        file_path : Path or None
            None if no files were given
        """
        if overwrite is None:
            overwrite = False
        if reencode is None:
            reencode = False
        if not files:
            return
        if len(files) == 1:
            shutil.copy(files[0], output)
            return output

        if output.suffix not in [".aac", ".mp4", ".flac"]:
            raise AttributeError("Output must be a valid path to a .acc or "
                                 ".mp4 file")

        # Only rewrite files if its explicitly stated
        if output.is_file() and not overwrite:
            return output

        streams = [str(i) for i in files if i.suffix in [".mp4", ".aac"]]

        tmp = tempfile.NamedTemporaryFile(mode="w",
                                          prefix="concat_file",
                                          suffix=".txt")

        with open(tmp.name, "w") as f:
            [f.write(f"file '{stream}'\n") for stream in streams]

        # This is a bit of a hack, there's probably a better way to do it.
        concatenated = ffmpeg.input(Path(f.name), f='concat', safe=0)
        if reencode:
            out = ffmpeg.output(concatenated,
                                filename=output,
                                loglevel=FFMPEG_LOGLEVEL)
        else:
            out = ffmpeg.output(concatenated,
                                filename=output,
                                c="copy",
                                loglevel=FFMPEG_LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()

        tmp.close()
        return output

    @staticmethod
    @overload
    def find_breaks(
            performance: Performance, length: float,
            return_notes: Literal[True]) -> list[tuple[int, int]]:
        ...

    @staticmethod
    @overload
    def find_breaks(
            performance: Performance, length: float,
            return_notes: Optional[Literal[False]] = None) -> \
            list[tuple[float, float]]:
        ...

    @staticmethod
    def find_breaks(performance: Performance,
                    length: float,
                    return_notes: Optional[bool] = None) -> List[
            Union[tuple[float, float], tuple[int, int]]]:
        """
        Take a midi performance partitura object and find spots where nothing
        was played for the period of time specified.

        returns a list of tuples, where a tuple contains the start and end time
        of the break section. If return_notes is True, then it returns the
        note numbers instead of the timestamps.

        Parameters
        ----------
        return_notes : bool
            whether to return the note indexes instead of times
        performance : Performance
            the midi performance object
        length : float
            how many seconds nothing was played

        Returns
        -------
        breaks_list : List[Union[Tuple[float, float], Tuple[int, int]]]
            each tuple contains start and end times/notes for the sections
        """
        if return_notes is None:
            return_notes = False

        note_array = performance.note_array()
        if len(note_array.shape) != 1:
            raise AttributeError("Midi files with more than one track are "
                                 "unsupported.")

        breaks = []
        prev_time = note_array[0][0]
        prev_note = 0
        for no, i in enumerate(note_array):
            time = i[0]
            if time - prev_time > length:
                if return_notes:
                    breaks.append((prev_note, no))
                else:
                    breaks.append((prev_time, time))
            prev_time = time
            prev_note = no

        return breaks

    @staticmethod
    def get_first_time(performance: Performance) -> float:
        """
        Get the time of the first note in a performance.

        Parameters
        ----------
        performance : Performance

        Returns
        -------
        first_time : float
        """
        note_array = performance.note_array()
        return note_array[0][0]

    @staticmethod
    def get_last_time(performance: Performance) -> float:
        """
        Get the timestamp when the last note was played.

        Parameters
        ----------
        performance : Performance

        Returns
        -------
        last_time : float
        """
        note_array = performance.note_array()
        return note_array[-1][0]

    @staticmethod
    def get_last_offset(performance: Performance):
        """
        Last note in note array + duration of that note

        Parameters
        ----------
        performance : Performance

        Returns
        -------
        last_offset : float
        """
        return max([i["note_off"] for i in performance[0].notes])
        # For some reason, using the note array gives incorrect times. I'll
        # leave the code here for now and perhaps it gets fixed in the future.
        # note_array = performance.note_array()
        # return max(note_array["onset_sec"] + note_array["duration_sec"])

    @staticmethod
    def split_audio(audio_path: PathLike,
                    split_start: float,
                    split_end: float,
                    output: Path,
                    overwrite: Optional[bool] = None) -> PathLike:
        """
        Extract a section of an audio file given start and end points.

        Parameters
        ----------
        output : Path
            path where to output file
        split_end : float
            end of the split in seconds
        audio_path : PathLike
            path to audio file as a Path or string
        split_start : float
            the place in seconds at which to split audio
        overwrite : bool, optional
            bool, whether to overwrite already existing files

        Returns
        -------
        audio_file : PathLike
            path of new audio file, the same as `output`
        """
        if overwrite is None:
            overwrite = False

        if not output.suffix:
            raise AttributeError("Output must be a path to a file")
        elif output.is_file() and not overwrite:
            return output

        input_file = ffmpeg.input(audio_path)
        audio = input_file.audio
        trimmed = audio.filter("atrim", start=split_start, end=split_end)
        out = ffmpeg.output(trimmed, filename=output, loglevel=FFMPEG_LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()

        return output

    def get_len(self, audio_path: PathLike) -> float:
        """
        Get the length in seconds of a media file.

        Parameters
        ----------
        audio_path : path to audio file

        Returns
        -------
        length : float
        """
        metadata = self.ff_probe(audio_path)
        duration = float(metadata["format"]["duration"])
        return duration

    @staticmethod
    def ff_probe(filepath: PathLike):
        return ffmpeg.probe(filepath)

    @staticmethod
    def delete_files(files: List[Path]) -> None:
        """
        Delete a list of files.

        Parameters
        ----------
        files : List[Path]

        Returns
        -------
        None
        """
        [os.remove(i) for i in files]

    @staticmethod
    def trim_silence(file: Path,
                     output: Path,
                     overwrite: Optional[bool] = None,
                     threshold: Optional[int] = None) -> None:
        """
        Trim silence at start and end of a given file.

        Parameters
        ----------
        file : Path
            path to the file to trim
        output : Path
            path to output file
        overwrite : bool, optional
            whether to overwrite an existing file, default is False
        threshold : int, optional
            at what loudness level in decibels to detect sound, default is -20

        Returns
        -------
        None
        """
        if overwrite is None:
            overwrite = False
        if threshold is None:
            threshold = -20

        if not output.suffix:
            raise AttributeError("Output must be a path to a file")

        if output.is_file() and not overwrite:
            return

        input_file = ffmpeg.input(file)
        audio = input_file.audio

        trimmed = audio.filter(
            "silenceremove",
            start_periods=1,
            start_threshold=f"{threshold}dB"
        ).filter(
            "areverse"
        ).filter(
            "silenceremove",
            start_periods=1,
            start_threshold=f"{threshold}dB"

        ).filter(
            "areverse"
        )
        out = ffmpeg.output(trimmed, filename=output, loglevel=FFMPEG_LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()

    @staticmethod
    def extract_section(file: PathLike,
                        output_file: PathLike,
                        start: float,
                        end: float,
                        reencode: Optional[bool] = None):
        """
        Extract a section from a video given start and end points. Will
        overwrite files.

        Parameters
        ----------
        reencode : bool, optional
            whether to reencode the file or not
        output_file : PathLike
            Where to output new section
        file : PathLike
            the path to the video
        start : float
            the timestamp where to start the section from
        end : float
            the timestamp for where to end the section

        Returns
        -------
        None
        """
        if reencode is None:
            reencode = False

        ffmpeg_in = ffmpeg.input(file, ss=start)
        if reencode:
            out = ffmpeg_in.output(filename=output_file, to=end-start,
                                   loglevel=FFMPEG_LOGLEVEL)
        else:
            out = ffmpeg_in.output(filename=output_file, to=end-start,
                                   c="copy", loglevel=FFMPEG_LOGLEVEL)

        out = ffmpeg.overwrite_output(out)
        out.run()

    @staticmethod
    def get_decoded_duration(file: PathLike) -> float:
        """
        Get the duration of a file by decoding its audio. This will yield more
        accurate results than get_len.

        Parameters
        ----------
        file : PathLike

        Returns
        -------
        file_len : float
            in seconds
        """
        ffmpeg_in = ffmpeg.input(file).audio
        out = ffmpeg_in.output(filename="-", f='null')
        ffmpeg_return = out.run(capture_stderr=True)[1]

        # Parsing the output to get the time
        split_return = ffmpeg_return.split(b"\n")
        encode_sub = None
        for i in split_return:
            if i[:5] == b"size=":
                encode_sub = i.split(b"\r")[-1].split(b" ")
                encode_sub.reverse()
                break

        if encode_sub is None:
            raise AttributeError("Could not parse the file.")

        time = []
        for i in encode_sub:
            if b"time=" in i:
                time = str(i)[7:-1].split(":")
                break

        time = sum([j * float(i) for i, j in zip(time, [60*60, 60, 1])])

        return time

    @staticmethod
    def load_performance(file: PathLike) -> pt.performance.Performance:
        """
        Load a midi performance as a partitura performance object.

        Parameters
        ----------
        file : PathLike

        Returns
        -------
        performance : partitura.performance.Performance
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pt.load_performance_midi(file)

    @staticmethod
    def split_performance(performed_part: PerformedPart,
                          split_points: List[timestamps]) -> \
            List[PerformedPart]:
        """
        Take a performance and section timestamps and return a list of
        PerformedPart objects based on the timestamps.

        Parameters
        ----------
        performed_part : PerformedPart
        split_points : List[timestamps]
            timestamps showing start and end of sections

        Returns
        -------
        pp_list : List[PerformedPart]
            a list of sub-performances
        """
        subperformances: List[PerformedPart] = []
        for i in split_points:
            subperformances.append(
                slice_ppart_by_time(
                    ppart=performed_part,
                    start_time=i[0],
                    end_time=i[1],
                    clip_note_off=True,
                    reindex_notes=True
                )
            )
        return subperformances

    @staticmethod
    def read_raw_audio(filepath: PathLike,
                       sample_rate: int,
                       input_kwargs: Optional[Dict] = None) -> bytes:
        """
        Read audio from a file using FFMPEG.

        Parameters
        ----------
        filepath : PathLike
        sample_rate : int
        input_kwargs : Dict
            any additional arguments you want to pass

        Returns
        -------
        PCM_bytes : bytes
            the raw PCM audio as bytes
        """
        if input_kwargs is None:
            input_kwargs = {}

        out, _ = (
            ffmpeg.input(
                filepath, **input_kwargs
            ).output(
                '-', format='s16le', acodec='pcm_s16le', ac=1, ar=sample_rate,
                loglevel=FFMPEG_LOGLEVEL
            ).overwrite_output(
            ).run(
                capture_stdout=True
            )
        )
        return out

    def load_file_audio(self,
                        filepath: PathLike,
                        sample_rate: int) -> npt.NDArray:
        """
        Load audio from a file directly into a numpy array using FFMPEG.

        Parameters
        ----------
        filepath : PathLike
        sample_rate : int

        Returns
        -------
        PCM_array
            Numpy array containing the PCM audio data
        """
        raw_data = self.read_raw_audio(
            filepath=filepath,
            sample_rate=sample_rate
        )
        data_s16 = np.frombuffer(raw_data,
                                 dtype=np.int16)
        float_data = data_s16 * 0.5**15
        return float_data

    @staticmethod
    def load_video(filepath: PathLike,
                   resolution: Tuple[int, int]) -> npt.NDArray:
        """
        Load a video file directly into memory without the audio.

        Parameters
        ----------
        filepath : PathLike
        resolution : Tuple[int, int]
            (width, height), e.g. (1920, 1080)

        Returns
        -------
        video_array : npt.NDArray
        """
        out, _ = (
            ffmpeg
            .input(filepath)
            .output('pipe:', format='rawvideo', pix_fmt='rgb24')
            .run(capture_stdout=True)
        )
        video = (
            np
            .frombuffer(out, np.uint8)
            .reshape([-1, resolution[1], resolution[0], 3])
        )
        return video

    def get_no_frames(self, filepath: PathLike) -> int:
        """
        Find the number of frames in a video with ffprobe. Assumes that the
        video stream is at index zero.

        Parameters
        ----------
        filepath : PathLike
            path to a video file

        Returns
        -------
        no_frames : int
        """
        probe = self.ff_probe(filepath)["streams"][0]["nb_frames"]
