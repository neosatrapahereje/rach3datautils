import argparse as ap
from rach3datautils.alignment import extract_and_concat
from rach3datautils.alignment import split
from rach3datautils.alignment import trim_silence
from pathlib import Path
from rach3datautils.backup_files import PathLike
import os


def main(root_dir: PathLike,
         output_dir: PathLike = None,
         overwrite: bool = False):
    """
    Run the preprocessing pipeline for the rach3 dataset.

    Where root_dir is the root of the dataset, overwrite is whether to
    overwrite already existing files, and output_dir is where to put the
    processed files.

    The preprocessing steps are as follows:
      1. Extract audio from sessions, and concatenate it into the full session
      2. Remove silences at start and end of these new files
      3. Split files where there are long silences

    The goal is to reduce time drift between the flac audio and the video.

    There is one important limitation, the output (or the current working dir
    if no output dir is specified), must be within the root_dir.
    For example: output_dir = 'root_dir/output/' root_dir = 'root_dir/'
    """
    if output_dir is None:
        output_dir = './processed'

    output_dir = Path(output_dir)

    if not output_dir.exists():
        os.mkdir(output_dir)

    trimmed_dir = str(output_dir.joinpath("trimmed/"))
    concat_dir = str(output_dir.joinpath("concatenated/"))
    split_dir = str(output_dir.joinpath("split/"))

    extract_and_concat.main(root_dir=root_dir,
                            output_dir=concat_dir,
                            overwrite=overwrite)
    trim_silence.main(root_dir=concat_dir,
                      output_dir=trimmed_dir,
                      overwrite=overwrite)
    split_audio.main(processed_dir=trimmed_dir,
                     output_dir=split_dir,
                     root_dir=root_dir,
                     overwrite=overwrite)

    print(f"Successfully processed files to: {output_dir.absolute()}")


if __name__ == "__main__":
    parser = ap.ArgumentParser(
        prog="Audio Alignment Pipeline",
        description="To be used with rach3 dataset. Performs multiple steps in "
                    "the audio alignment pipeline.")

    parser.add_argument("-d", "--root_dir", action='store',
                        help='The root directory where the dataset is located. '
                             'All folders and subfolders in this directory '
                             'will be searched. The current working directory '
                             'should also be included.')
    parser.add_argument("-w", "--overwrite", action='store_true',
                        help='Whether to overwrite any already existing files '
                             'in the locations specified.')
    parser.add_argument("-o", "--output_dir", action='store',
                        help='Where to output processed files. If the directory'
                             'does not exist, a new one will be created. '
                             'Output directory must be within the input '
                             'directory.',
                        default='./processed_audio')

    args = parser.parse_args()
    main(output_dir=args.output_dir,
         overwrite=args.overwrite,
         root_dir=args.root_dir)
