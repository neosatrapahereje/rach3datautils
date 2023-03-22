import ffmpeg
import os
from partitura.performance import Performance
from pathlib import Path
import tempfile
from rach3datautils.misc import PathLike
from rach3datautils.config import DEBUG
from typing import Optional, Union, overload, Literal
import shutil

if DEBUG:
    LOGLEVEL = "debug"
else:
    LOGLEVEL = "quiet"


class AudioVideoTools:
    """
    Contains useful ffmpeg pipelines for working with audio and video, as well
    as other utility functions.
    """
    @staticmethod
    def extract_audio(filepath: Path, output: Path = None,
                      overwrite: bool = False) -> Path:
        """
        Extract audio from a video file. Returns the filepath of the new audio
        file. If no output is specified outputs the file in the same folder
        as the original video.
        """

        if output is None:
            output = Path(os.path.join(".", "audio_files",
                                       filepath.stem + "_audio.mp3"))
        elif not output.suffix == ".aac":
            raise AttributeError("Output must either be None or a valid path "
                                 "to a .acc file")

        if output.is_file() and not overwrite:
            return output

        video = ffmpeg.input(filepath)
        out = ffmpeg.output(video.audio, filename=output, c="copy",
                            loglevel=LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()
        return output

    @staticmethod
    def concat(files: list[Optional[Path]], output: Path,
               overwrite: Optional[bool] = None) -> Optional[Path]:
        """
        Takes a list of audio or video files and concatenates them into one
        file. They will be concatenated in the order present within the list.
        Returns path to new audio file.
        If only one file is given, it will simply be copied to the output
        location.
        """
        if overwrite is None:
            overwrite = False
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
        out = ffmpeg.output(concatenated, filename=output, c="copy",
                            loglevel=LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()

        return output

    @staticmethod
    @overload
    def find_breaks(
            midi: Performance, length: float,
            return_notes: Literal[True]) -> list[tuple[int, int]]:
        ...

    @staticmethod
    @overload
    def find_breaks(
            midi: Performance, length: float,
            return_notes: Optional[Literal[False]] = None) -> \
            list[tuple[float, float]]:
        ...

    @staticmethod
    def find_breaks(midi: Performance,
                    length: float,
                    return_notes: Optional[bool] = None) -> \
            list[Union[tuple[float, float], tuple[int, int]]]:
        """
        Take a midi performance partitura object and find spots where nothing
        was played for the period of time specified.

        returns a list of tuples, where a tuple contains the start and end time
        of the break section. If return_notes is True, then it returns the
        note numbers instead of the timestamps.

        Parameters
        ----------
        return_notes: bool, whether to return the note indexes instead of times
        midi: the midi performance object
        length: how many seconds nothing was played
        -------
        """
        if return_notes is None:
            return_notes = False

        note_array = midi.note_array()
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
    def get_first_time(midi: Performance) -> float:
        """
        Get the time of the first note in a performance.
        """
        note_array = midi.note_array()
        return note_array[0][0]

    @staticmethod
    def get_last_time(midi: Performance) -> float:
        """
        Get the timestamp when the last note was played.
        """
        note_array = midi.note_array()
        return note_array[-1][0]

    @staticmethod
    def split_audio(audio_path: PathLike, split_start: float,
                    split_end: float, output: Path,
                    overwrite: bool = False) -> PathLike:
        """
        Extract a section of an audio file given start and end points.

        Parameters
        ----------
        output: path where to output file
        split_end: end of the split in seconds
        audio_path: path to audio file as a Path or string
        split_start: the place in seconds at which to split audio
        overwrite: bool, whether to overwrite already existing files
        -------
        """
        # Only rewrite files if its explicitly stated
        if not output.suffix:
            raise AttributeError("Output must be a path to a file")
        elif output.is_file() and not overwrite:
            return output

        input_file = ffmpeg.input(audio_path)
        audio = input_file.audio
        trimmed = audio.filter("atrim", start=split_start, end=split_end)
        out = ffmpeg.output(trimmed, filename=output, loglevel=LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()

    def get_len(self, audio_path: PathLike) -> float:
        """
        Get the length in seconds of a media file.

        Parameters
        ----------
        audio_path: path to audio file
        -------
        """
        metadata = self.ff_probe(audio_path)
        duration = float(metadata["format"]["duration"])
        return duration

    @staticmethod
    def ff_probe(filepath: PathLike):
        return ffmpeg.probe(filepath)

    @staticmethod
    def delete_files(files: list[Path]) -> None:
        """
        Simply delete a list of files.
        Parameters

        ----------
        files: a list of filepaths to be deleted
        -------
        """
        [os.remove(i) for i in files]

    @staticmethod
    def trim_silence(file: Path, output: Path,
                     overwrite: bool = False, threshold: int = -20) -> None:
        """
        Trim silence at start and end of a given file.

        Parameters
        ----------
        file: path to the file to trim
        output: path to output file
        overwrite: whether to overwrite an existing file
        threshold: at what loudness level in decibels to detect sound
        -------
        """
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
        out = ffmpeg.output(trimmed, filename=output, loglevel=LOGLEVEL)
        out = ffmpeg.overwrite_output(out)
        out.run()

    @staticmethod
    def extract_section(file: PathLike,
                        output_file: PathLike,
                        start: float,
                        end: float,
                        reencode: Optional[bool] = None
                        ):
        """
        Extract a section from a video given start and end points. Will
        overwrite files.
        Parameters
        ----------
        reencode: whether to reencode the file or not
        output_file: Where to output new section
        file: the path to the video
        start: the timestamp where to start the section from
        end: the timestamp for where to end the section

        Returns None
        -------
        """
        if reencode is None:
            reencode = False

        ffmpeg_in = ffmpeg.input(file, ss=start)
        if reencode:
            out = ffmpeg_in.output(filename=output_file, to=end-start,
                                   loglevel=LOGLEVEL)
        else:
            out = ffmpeg_in.output(filename=output_file, to=end-start,
                                   c="copy", loglevel=LOGLEVEL)

        out = ffmpeg.overwrite_output(out)
        out.run()

    @staticmethod
    def get_decoded_duration(file: PathLike) -> float:
        """
        Get the duration of a file by decoding its audio. This will yield more
        accurate results than get_len.
        Returns length in seconds
        """
        ffmpeg_in = ffmpeg.input(file).audio
        out = ffmpeg_in.output(filename="-", f='null')
        ffmpeg_return = out.run(capture_stderr=True)[1]

        # Parsing the output to get the time
        encode_out = ffmpeg_return.split(b"\n")[46].split(b"\r")
        encode_sub = encode_out[-1].split(b" ")
        encode_sub.reverse()
        time = []
        for i in encode_sub:
            if b"time=" in i:
                time = str(i)[7:-1].split(":")
                break

        time = sum([j * float(i) for i, j in zip(time, [60*60, 60, 1])])

        return time
