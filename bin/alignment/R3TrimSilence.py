import argparse as ap
from pathlib import Path
from rach3datautils.utils.dataset import DatasetUtils
from rach3datautils.utils.session import Session
from rach3datautils.alignment.trim_silence import trim
from rach3datautils.exceptions import MissingFilesError
from typing import List
from tqdm import tqdm


parser = ap.ArgumentParser(
    prog="Silence Trimmer",
    description="Trim silence at start and end of all videos in dataset "
                "based on note detection from midi/flac files."
)
parser.add_argument(
    "-d", "--root_directory",
    action="store",
    help="Root directory where the dataset files are "
         "stored.",
    required=True
)
parser.add_argument(
    "-w", "--overwrite",
    action="store_true",
    help="Whether to overwrite the trimmed files if they"
         "already exist"
)
parser.add_argument(
    "-o", "--output_directory",
    action="store",
    help="Folder where the output should go.",
    required=True
)
args = parser.parse_args()


if args.overwrite is None:
    overwrite = False

output_dir = Path(args.output_directory)
if output_dir.suffix:
    raise AttributeError("Output directory should not have a suffix as "
                         "it is a directory.")
if not output_dir.exists():
    output_dir.mkdir()

dataset = DatasetUtils(root_path=args.root_directory)

subsessions = dataset.get_sessions(filetype=[".aac", ".flac", ".mp4",
                                             ".mid"])

fail_list: List[Session] = []
for i in tqdm(subsessions):
    output_file = output_dir.joinpath(str(i.id) + "_trimmed.mp4")
    if output_file.exists() and not args.overwrite:
        continue

    try:
        trim(audio=i.audio.file,
             flac=i.flac.file,
             midi=i.midi.file,
             video=i.video.file,
             performance=i.performance,
             output_file=output_file)

    except MissingFilesError:
        fail_list.append(i)

if fail_list:
    print("Trimming failed for following files:\n",
          [i.id for i in fail_list])
