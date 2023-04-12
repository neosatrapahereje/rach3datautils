import argparse as ap
from rach3datautils.extra.backup_files import backup_dir


parser = ap.ArgumentParser(
    description="Script for syncing two directories"
)
parser.add_argument(
    "-d1",
    action="store",
    type=str,
    required=True
)
parser.add_argument(
    "-d2",
    action="store",
    type=str,
    required=True
)
parser.add_argument(
    "-f", "--filetype",
    action="store",
    type=str,
    required=False,
    default=None
)
parser.add_argument(
    "-cbd", "--cut-by-date",
    action="store",
    type=str,
    required=False,
    default=None
)
args = parser.parse_args()

backup_dir(
    dir1=args.d1,
    dir2=args.d2,
    filetype=args.filetype,
    cut_by_date=args.cut_by_date
)
