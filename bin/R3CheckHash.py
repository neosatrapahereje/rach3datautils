import argparse as ap

from rach3datautils.extra.hashing import check_hashes

if __name__ == "__main__":
    parser = ap.ArgumentParser(
        prog="Hash Checker",
        description="Compare hashes from a file with hashes of videos in a "
                    "given video directory/s"
    )
    parser.add_argument(
        "-d",  "--video-directory",
        action="store",
        required=True,
        type=str,
        nargs="*"
    )
    parser.add_argument(
        "-hf", "--hash-file",
        action="store",
        type=str,
        required=True
    )
    args = parser.parse_args()

    check_hashes(hash_file=args.hash_file, video_dirs=args.video_directory)
