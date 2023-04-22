import argparse as ap
from typing import List, Tuple
import csv

from tqdm import tqdm

from rach3datautils.alignment.verification import Verify
from rach3datautils.utils.dataset import DatasetUtils
from rach3datautils.utils.session import Session

parser = ap.ArgumentParser(
    prog="R3CheckIntegrity",
    description="Check the integrity of synced files and optionally output "
                "to a CSV."
)
parser.add_argument(
    "-d", "--root-dir",
    help="Directory containing files to be checked",
    type=str,
    required=True
)
parser.add_argument(
    "-o", "--output-filepath",
    help="Where to output the csv containing results. If no output is given "
         "results are printed to stdout.",
    required=False,
    type=str
)
args = parser.parse_args()

dataset = DatasetUtils(root_path=args.root_dir)
sessions = dataset.get_sessions(filetype=[".mp4", ".flac"])
sessions = dataset.remove_noncomplete(sessions, required=["flac.splits_list",
                                                          "video.splits_list"])

# (session_id, video_path, flac_path, issue)
invalid_session_list: List[Tuple[str, str, str, str]] = []

for session in tqdm(sessions):
    session.sort_audios()
    session.sort_videos()

    for video_split, flac_split in zip(session.video.splits_list,
                                       session.flac.splits_list):
        integrity = Verify().check_video_flac(
            video=video_split,
            flac=flac_split
        )
        if integrity is not True:
            invalid_session_list.append((str(session.id),
                                         video_split,
                                         flac_split,
                                         integrity))

if args.output_filepath:
    with open(args.output_filepath, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["session_id", "video_path", "flac_path", "issue"])
        csv_writer.writerows(invalid_session_list)
else:
    print("session_id, video_path, flac_path\n")
    [print(i) for i in invalid_session_list]
