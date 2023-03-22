import argparse as ap
from rach3datautils.alignment.extract_and_concat import extract_and_concat
from rach3datautils.alignment.split import split_video_and_flac
from rach3datautils.dataset_utils import DatasetUtils
from pathlib import Path
from rach3datautils.backup_files import PathLike
from tqdm import tqdm
import tempfile
import os


def main(root_dir: PathLike,
         output_dir: PathLike = None,
         overwrite: bool = False):
    """
    Run the preprocessing pipeline for the rach3 dataset.

    root_dir is the root of the dataset, overwrite is whether to
    overwrite already existing files, and output_dir is where to put the
    processed files.

    The preprocessing steps are as follows:
      1. Extract audio from sessions, and concatenate it into the full session
      3. Split files where there are long silences and remove intro/outro
         pauses

    The goal is to reduce time drift between the flac audio and the video by
    splitting them into smaller files.
    """
    if output_dir is None:
        output_dir = './processed'

    output_dir = Path(output_dir)

    if output_dir.suffix:
        raise AttributeError("output_dir should be a directory")
    if not output_dir.exists():
        os.mkdir(output_dir)

    with tempfile.TemporaryDirectory(dir="./") as tempdir:
        tempdir = Path(tempdir)

        dataset = DatasetUtils(root_path=[root_dir, tempdir])
        sessions = dataset.get_sessions(".mp4")

        # First we run extract_and_concat
        for subsession in tqdm(sessions, desc="concatenating files"):
            extract_and_concat(
                session=subsession,
                output=tempdir,
                overwrite=overwrite
            )
        sessions = dataset.get_sessions([".mid", ".mp4", ".flac", ".aac"])
        for subsession in tqdm(sessions, desc="splitting files"):
            split_video_and_flac(
                subsession=subsession,
                output_dir=output_dir,
                overwrite=overwrite
            )

    print(f"Successfully processed files to: {output_dir.absolute()}")


if __name__ == "__main__":
    parser = ap.ArgumentParser(
        prog="Audio Alignment Pipeline",
        description="To be used with rach3 dataset. Performs multiple steps "
                    "in the audio alignment pipeline.")

    parser.add_argument(
        "-d", "--root_dir",
        action='store',
        help='The root directory where the dataset is located. All folders '
             'and subfolders in this directory will be searched.'
    )
    parser.add_argument(
        "-w", "--overwrite",
        action='store_true',
        help='Whether to overwrite any already existing files in the '
             'locations specified.'
    )
    parser.add_argument(
        "-o", "--output_dir", action='store',
        help='Where to output processed files. If the directory does not '
             'exist, a new one will be created. Output directory must be '
             'within the input directory.',
        default='./processed_audio')

    args = parser.parse_args()

    main(output_dir=args.output_dir,
         overwrite=args.overwrite,
         root_dir=args.root_dir)
