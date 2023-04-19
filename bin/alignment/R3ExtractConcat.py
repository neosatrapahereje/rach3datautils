import argparse
from rach3datautils.utils.dataset import DatasetUtils
import os
from typing import Literal
from rach3datautils.alignment.extract_and_concat import extract_and_concat
from pathlib import Path
from tqdm import tqdm


parser = argparse.ArgumentParser(
    prog="Extract audio/video and concatenate",
    description="Take a folder containing one or more complete sessions "
                "and combine all the sub-videos and audios into 1 session "
                "video or audio per session."
)
parser.add_argument(
    "-d", "--root_directory",
    action='store',
    required=True,
    help='The root directory where the dataset is '
         'located. All folders and subfolders in this '
         'directory will be searched.'
)
parser.add_argument(
    "-w", "--overwrite", action='store_true',
    help='If the concatenated files exist already, '
         'whether to overwrite them.'
)
parser.add_argument(
    "-o", "--output_dir", action='store',
    help='Where to output processed files. If the '
         'directory does not exist, a new one will be '
         'created.',
    required=True,
    default='./concat/'
)
parser.add_argument(
    "-a", "--audio", action="store_true",
    help="Whether to output only the audio."
)
parser.add_argument(
    "-v", "--video", action="store_true",
    help="Whether to concatenate the video files."
)
parser.add_argument(
    "-r", "--reencode", action="store_true",
    help="Whether to reencode the files when concatonating"
)
args = parser.parse_args()


output = Path(args.output_dir)
root_dir = Path(args.root_directory)
data_utils = DatasetUtils(root_path=root_dir)

# Check if the output dir exists, and if not create a new one
if output.suffix:
    raise AttributeError("Output must be a path to a directory")
elif not output.exists():
    os.mkdir(output)

filetypes: list[Literal[".mp4"]] = [".mp4"]

sessions = data_utils.get_sessions(filetype=filetypes)

for session in tqdm(sessions):
    extract_and_concat(
        session=session,
        output=output,
        audio=args.audio,
        video=args.video,
        overwrite=args.overwrite,
        reencode=args.reencode
    )
