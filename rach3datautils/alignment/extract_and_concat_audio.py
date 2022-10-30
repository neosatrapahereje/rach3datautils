# Script for extracting audio from video files, and then concatenating it into
# the full parts.


import argparse
from pathlib import Path
from video_audio_tools import AudioVideoTools

# Let's set up some argument parsing for ease of use.
parser = argparse.ArgumentParser(
    prog="Extract audio and concatenate",
    description="To be used with rach3 dataset. This script takes the video"
                "files, extracts the audio, and then combines the audios that"
                "come from the same recording. e.g the audio from the 2 files:"
                "rach_3_2022-03-20_p001 and rach_3_2022-03-20_p002 get "
                "combined into one file.")

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
prev_file = str(video_files[0])
current_file = [prev_file]
video_files.append("None")
for i in video_files[1:]:
    if str(i)[:-7]+str(i)[-4:] == prev_file[:-7]+prev_file[-4:]:
        current_file.append(i)
    else:
        AudioVideoTools.concat_audio(
            audio_files=
            [AudioVideoTools.extract_audio(
                filepath=str(j), overwrite=args.overwrite)
                for j in current_file],
            output=prev_file[:-9]+"_full.mp3",
            overwrite=args.overwrite)
        current_file = [i]

    prev_file = str(i)

