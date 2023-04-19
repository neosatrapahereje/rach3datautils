import argparse as ap
from rach3datautils.utils.dataset import DatasetUtils
from rach3datautils.alignment.sync import load_and_sync, Sync
from rach3datautils.types import timestamps
from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm
import csv


parser = ap.ArgumentParser(
    prog="Audio Synchronizer",
    description="Use midi data and spectral analysis to find timestamps "
                "corresponding to the same note in 2 different audio "
                "files."
)
parser.add_argument(
    "-d", "--root-dir",
    action="store",
    required=True,
    help="The root directory containing midi, flac, and mp3 files.",
    type=str
)
parser.add_argument(
    "-fs", "--frame-size",
    action="store",
    required=False,
    default=None,
    help="Frame size when loading the FramedSignal object.",
    type=int
)
parser.add_argument(
    "-hs", "--hop-size",
    action="store",
    required=False,
    default=None,
    help="Hop size to use when generating FramedSignal object",
    type=int
)
parser.add_argument(
    "-ws", "--window-size",
    action="store",
    required=False,
    default=None,
    help="Window size to use when calculating distances.",
    type=int
)
parser.add_argument(
    "-ds", "--distance-function",
    action="store",
    required=False,
    default=None,
    help="Distance function to use, defaults to cosine.",
    type=str
)
parser.add_argument(
    "-s", "--stride",
    action="store",
    required=False,
    default=None,
    help="How many samples to move the window center between windows.",
    type=int
)
parser.add_argument(
    "-sp", "--search-period",
    action="store",
    required=False,
    default=None,
    help="How many seconds at the start and end to look through, smaller "
         "values mean faster performance and less likely to return an "
         "incorrect result. However if the first note isn't in the search "
         "period specified it wont be found.",
    type=int
)
parser.add_argument(
    "-sr", "--sample-rate",
    action="store",
    required=False,
    default=None,
    help="Sample rate to use when loading the audio files.",
    type=int
)
parser.add_argument(
    "-o", "--output-file",
    action="store",
    required=False,
    default=None,
    help="Where to store outputs as csv, if not set will just print the "
         "results.",
    type=str
)
parser.add_argument(
    "-ns", "--notes-index",
    action="store",
    required=False,
    default=None,
    help="What notes to look for, defaults to first and last.",
    type=str
)
args = parser.parse_args()


if args.distance_function == "manhatten":
    dist_func = Sync.manhatten_dist
elif args.distance_function == "cosine":
    dist_func = Sync.cos_dist
else:
    dist_func = None

dataset = DatasetUtils(root_path=Path(args.root_dir))

sessions = dataset.get_sessions([".mid", ".aac", ".flac"])

track_args = {
    "sample_rate": args.sample_rate,
    "frame_size": args.frame_size,
    "hop_size": args.hop_size
}
sync_args = {
    "notes_index": args.notes_index,
    "window_size": args.window_size,
    "stride": args.stride,
    "search_period": args.search_period
}
timestamps_list: List[Tuple[str, timestamps]] = []
for i in tqdm(sessions):
    timestamps_list.append(
        (
            str(i.id),
            load_and_sync(
                performance=i.performance,
                flac=i.flac.file,
                audio=i.audio.file,
                track_args=track_args,
                sync_args=sync_args,
                sync_distance_func=dist_func
            )
        )
    )

if args.output_file is None:
    print(timestamps_list)
    exit()

with open(args.output_file, "w") as f:
    csv_writer = csv.writer(f)
    csv_writer.writerow(["session_id", "first_note", "last_note"])
    csv_writer.writerows(timestamps_list)
