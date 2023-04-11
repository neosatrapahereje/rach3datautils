from rach3datautils.backup_files import check_hashes
import argparse as ap


if __name__ == "__main__":
    parser = ap.ArgumentParser(
        prog="Hash Checker",
        description="Compare hashes from a file with hashes of videos in a "
                    "given video directory/s"
    )

    parser.add_argument("-d",  "--video-directory", action="store", nargs="*")
    parser.add_argument("-hf", "--hash-file", action="store")

    args = parser.parse_args()

    check_hashes(hash_file=args.hash_file, video_dirs=args.video_directory)
