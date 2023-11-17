import argparse as ap
import csv
import os
from typing import List, Tuple

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
parser.add_argument(
    "-c", "--clean",
    help="Whether to delete invalid files from the directory.",
    required=False,
    action="store_true"
)
args = parser.parse_args()

dataset = DatasetUtils(root_path=args.root_dir)
sessions = dataset.get_sessions(filetype=[".mp4", ".flac", ".mid"])
sessions = dataset.remove_noncomplete(sessions, required=["flac.splits_list",
                                                          "video.splits_list",
                                                          "midi.splits_list"])

# (session_id, video_path, flac_path, issue)
invalid_session_list: List[Tuple[str, str, str, str]] = []
invalid_sessions: List[Session] = []
for session in tqdm(sessions):
    session.sort_audios()
    session.sort_videos()

    for video_split, flac_split, midi_split in zip(session.video.splits_list,
                                                   session.flac.splits_list,
                                                   session.midi.splits_list):
        integrity = Verify().run_checks(
            video=video_split,
            flac=flac_split,
            midi=midi_split
        )
        if integrity is not True:
            invalid_session_list.append((str(session.id),
                                         video_split,
                                         flac_split,
                                         integrity))
            if session not in invalid_sessions:
                invalid_sessions.append(session)

if args.output_filepath:
    with open(args.output_filepath, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["session_id", "video_path", "flac_path", "issue"])
        csv_writer.writerows(invalid_session_list)
else:
    print("session_id, video_path, flac_path, issue\n")
    [print(i) for i in invalid_session_list]

if args.clean:
    for i in invalid_sessions:
        for j in i.all_files():
            os.unlink(j)
