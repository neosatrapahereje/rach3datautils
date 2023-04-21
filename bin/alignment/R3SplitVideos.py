import argparse as ap
import os
from pathlib import Path

from tqdm import tqdm

from rach3datautils.alignment.split import split_video_flac_mid
from rach3datautils.utils.dataset import DatasetUtils

parser = ap.ArgumentParser(
    prog="Midi Based Video and Audio Splitter",
    description="Split video and audio files where there are breaks in "
                "the music based on a midi file."
)
parser.add_argument(
    "-d", "--root_directory",
    action="store",
    help="Root directory of the dataset. If not set, the"
         "current working folder is used.",
    required=True
)
parser.add_argument(
    "-w", "--overwrite",
    action="store_true",
    help="Whether to overwrite the files if they already"
         "exist."
)
parser.add_argument(
    "-o", "--output_directory",
    action="store",
    help="Directory where to store output files.",
    default="./audio_split/"
)
args = parser.parse_args()


output_dir = Path(args.output_directory)

if output_dir.suffix:
    raise AttributeError("output_dir must be a path to a valid directory")

if not output_dir.exists():
    os.mkdir(output_dir)

dataset = DatasetUtils(args.root_directory)
subsessions = dataset.get_sessions(filetype=[".mid", ".mp4", ".flac",
                                             ".aac"])

for i in tqdm(subsessions):
    split_video_flac_mid(
        audio=i.audio.file,
        flac=i.flac.file,
        midi=i.midi.file,
        video=i.video.file,
        performance=i.performance,
        overwrite=args.overwrite,
        output_dir=output_dir
    )
