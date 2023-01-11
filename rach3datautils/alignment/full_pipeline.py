"""
Script that performs alignment centric preprocessing from start to end
on the rach3 dataset.

The steps are as follows:
  1. Extract audio from sessions, and concatenate it into the full session
  2. Remove silences at start and end of these new files
  3. Split files where there are long silences
"""

import argparse as ap
from extract_and_concat_audio import main as extract_concat_audio
from split_audio import main as split_audio
from trim_silence import main as trim_silence


parser = ap.ArgumentParser(
    prog="Audio Alignment Pipeline",
    description="To be used with rach3 dataset. Performs multiple steps in the "
                "audio alignment pipeline.")

parser.add_argument("-d", "--root_directory", action='store',
                    help='The root directory where the dataset is located. All'
                         'folders and subfolders in this directory will be'
                         'searched. The current working directory should also '
                         'be included.')
parser.add_argument("-w", "--overwrite", action='store_true',
                    help='Whether to overwrite any already existing files in '
                         'the locations specified.')
parser.add_argument("-o", "--output_dir", action='store',
                    help='Where to output processed files. If the directory'
                         'does not exist, a new one will be created.',
                    default='./processed_audio')


args = parser.parse_args()

extra_args = []
if args.overwrite:
    extra_args.append("-w")

extract_concat_audio([f"-d={args.root_directory}"] + extra_args)

trim_silence(["-d", args.root_directory] + extra_args)

split_audio(["-d", args.root_directory] + extra_args)


