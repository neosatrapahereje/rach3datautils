# Script for extracting audio from video files, and then concatenating it into
# the full parts.

# Let's set up some argument parsing for ease of use.
import argparse

parser = argparse.ArgumentParser(
    prog="Extract audio and concatenate",
    description="To be used with rach3 dataset. This script takes the video"
                "files, extracts the audio, and then combines the audios that"
                "come from the same recording. e.g the audio from the 2 files:"
                "rach_3_2022-03-20_p001 and rach_3_2022-03-20_p002 get combined"
                "into one file."
)

parser.add_argument("-d","--root_directory", action='store')

args = parser.parse_args()


# First we get a list of all the video files.
from pathlib import Path

if not args.root_directory:
    root_dir = "./"
else:
    root_dir = args.root_directory

video_files = Path(root_dir).rglob('*.mp4')


# Create an ffmpeg pipeline
import ffmpeg

stream = ffmpeg.input
