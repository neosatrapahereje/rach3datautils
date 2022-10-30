import ffmpeg
import os


class AudioVideoTools:
    """
    Contains useful ffmpeg pipelines for working with audio and video.
    """
    @staticmethod
    def extract_audio(filepath: str, output: str = None,
                      overwrite: bool = False) -> str:
        """
        Extract audio from a video file. Returns the filepath of the new audio
        file.
        """

        if output is None:
            output = filepath[:-4] + "_audio.mp3"

        # Only rewrite files if its explicitly stated
        if os.path.isfile(output) and not overwrite:
            return output
        else:
            video = ffmpeg.input(filepath)
            audio = video.audio
            out = ffmpeg.output(audio, output)
            out = ffmpeg.overwrite_output(out)
            out.run()
            return output

    @staticmethod
    def concat_audio(audio_files: list, output: str,
                     overwrite: bool = False) -> str:
        """
        Takes a list of audio files and concatenates them into one file. They
        will be concatenated in the order present within the list.
        Returns path to new audio file.
        """

        # Only rewrite files if its explicitly stated
        if os.path.isfile(output) and not overwrite:
            return output
        else:
            streams = []

            for i in audio_files:
                input = ffmpeg.input(i)
                streams.append(input)

            concatenated = ffmpeg.concat(*streams, v=0, a=1)
            out = ffmpeg.output(concatenated, output)
            out = ffmpeg.overwrite_output(out)
            out.run()
            return output
