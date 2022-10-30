# Script for extracting audio from video files, and then concatenating it into
# the full parts.


import argparse
from pathlib import Path
import ffmpeg
import os

# Let's set up some argument parsing for ease of use.
parser = argparse.ArgumentParser(
    prog="Extract audio and concatenate",
    description="To be used with rach3 dataset. This script takes the video"
                "files, extracts the audio, and then combines the audios that"
                "come from the same recording. e.g the audio from the 2 files:"
                "rach_3_2022-03-20_p001 and rach_3_2022-03-20_p002 get combined"
                "into one file.")

parser.add_argument("-d", "--root_directory", action='store')
parser.add_argument("-o", "--overwrite", action='store_true')
args = parser.parse_args()


# First we get a list of all the video files.
if not args.root_directory:
    root_dir = "./"
else:
    root_dir = args.root_directory

video_files = list(Path(root_dir).rglob('*.mp4'))

# Extract audio from all files and keep paths
all_audio_files = []

for i in video_files:
    i = str(i)
    audio_path = i[:-4]+"_audio.mp3"
    all_audio_files.append(audio_path)

    # Only rewrite files if its explicitly stated
    if os.path.isfile(audio_path) and not args.overwrite:
        continue
    else:
        video = ffmpeg.input(i)
        audio = video.audio
        out = ffmpeg.output(audio, audio_path)
        out = ffmpeg.overwrite_output(out)
        out.run()

