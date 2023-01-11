import ffmpeg
import os
from partitura.performance import Performance
from pathlib import Path
from typing import Union
from ffprobe import FFProbe


class AudioVideoTools:
    """
    Contains useful ffmpeg pipelines for working with audio and video.
    """

    def extract_audio(self, filepath: Path, output: Path = None,
                      overwrite: bool = False) -> Path:
        """
        Extract audio from a video file. Returns the filepath of the new audio
        file.
        """

        if output is None:
            output = Path(os.path.join(".", "audio_files",
                                       filepath.stem + "_audio.mp3"))

        if not self._check_path(output, overwrite=overwrite):
            return output

        video = ffmpeg.input(filepath)
        audio = video.audio
        out = ffmpeg.output(audio, filename=output)
        out = ffmpeg.overwrite_output(out)
        out.run()
        return output

    def concat_audio(self, audio_files: list, output: Path,
                     overwrite: bool = False) -> Path:
        """
        Takes a list of audio files and concatenates them into one file. They
        will be concatenated in the order present within the list.
        Returns path to new audio file.
        """

        # Only rewrite files if its explicitly stated
        if not self._check_path(output, overwrite=overwrite):
            return output

        streams = []

        for i in audio_files:
            ffmpeg_input = ffmpeg.input(i)
            streams.append(ffmpeg_input)

        concatenated = ffmpeg.concat(*streams, v=0, a=1)
        out = ffmpeg.output(concatenated, filename=output)
        out = ffmpeg.overwrite_output(out)
        out.run()
        return output

    @staticmethod
    def find_breaks(midi: Performance, length: float = 10) -> \
            list[tuple[float, float]]:
        """
        Take a midi performance partitura object and find spots where nothing
        was played for the period of time specified.

        returns a list of tuples, where a tuple contains the start and end time
        of the break section.

        Parameters
        ----------
        midi: the midi performance object
        length: how many seconds nothing was played
        -------
        """

        note_array = midi.note_array()
        if len(note_array.shape) != 1:
            raise AttributeError("Midi files with more than one track are "
                                 "unsupported.")

        breaks = []
        prev_time = note_array[0][0]
        for i in note_array:
            time = i[0]
            if time - prev_time > length:
                breaks.append((prev_time, time))
            prev_time = time

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

    def split_audio(self, audio_path: Union[Path, str], split_start: float,
                    split_end: float, output: Union[Path, str],
                    overwrite: bool = False) -> Union[Path, str]:
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
        if not self._check_path(output, overwrite=overwrite, create_dir=True):
            return output

        input_file = ffmpeg.input(audio_path)
        audio = input_file.audio
        trimmed = audio.filter("atrim", start=split_start, end=split_end)
        out = ffmpeg.output(trimmed, filename=output)
        out = ffmpeg.overwrite_output(out)
        out.run()

    @staticmethod
    def _check_path(path: Path, overwrite: bool, create_dir: bool = True):
        """
        Take a path and check if the folder exists. If it does not exist, either
        create it, or return false based on create_dir setting.

        Additionally, if a path to a file is specified, checks if the file
        already exists and returns true or false based on overwrite parameter.

        I'm pretty sure this function is buggy, there's def improvement to be
        done.
        """
        if path.exists() or path.parent.exists():
            if path.is_dir() or path.parent.is_dir():
                return True
            elif path.is_file and overwrite:
                return True
        else:
            if path.suffix == "":
                if create_dir:
                    os.mkdir(path)
                    return True
            elif path.parent and create_dir:
                os.mkdir(path.parent)
                return True
        return False

    @staticmethod
    def get_len(audio_path: Union[Path, str]) -> float:
        """
        Get the length in seconds of a media file.

        Parameters
        ----------
        audio_path: path to audio file
        -------
        """
        metadata = FFProbe(audio_path)
        duration = [float(i) for i in metadata.metadata["Duration"].split(":")]
        duration = duration[0] * 60 * 60 + duration[1] * 60 + duration[2]
        return duration

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

    def trim_silence(self, file: Path, output: Path,
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
        if not self._check_path(output, overwrite=overwrite, create_dir=True):
            return None

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
        out = ffmpeg.output(trimmed, filename=output)
        out = ffmpeg.overwrite_output(out)
        out.run()
