import ffmpeg
import os
from partitura.performance import Performance
from pathlib import Path
from rach3datautils.misc import PathLike


class AudioVideoTools:
    """
    Contains useful ffmpeg pipelines for working with audio and video.
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
        elif not output.suffix == ".mp4":
            raise AttributeError("Output must either be None or a valid path "
                                 "to a .mp4 file")

        if output.is_file() and not overwrite:
            return output

        video = ffmpeg.input(filepath)
        audio = video.audio
        out = ffmpeg.output(audio, filename=output)
        out = ffmpeg.overwrite_output(out)
        out.run()
        return output

    @staticmethod
    def concat_audio(audio_files: list[PathLike], output: Path,
                     overwrite: bool = False) -> Path:
        """
        Takes a list of audio files and concatenates them into one file. They
        will be concatenated in the order present within the list.
        Returns path to new audio file.
        """

        if not output.suffix == ".mp3":
            raise AttributeError("Output must be a valid path to a .mp3 file")

        # Only rewrite files if its explicitly stated
        if output.is_file() and not overwrite:
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
        out = ffmpeg.output(trimmed, filename=output)
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
        """
        Run a probe on a file and return the result
        """
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
        out = ffmpeg.output(trimmed, filename=output)
        out = ffmpeg.overwrite_output(out)
        out.run()
