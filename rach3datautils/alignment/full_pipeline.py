import argparse as ap
from .extract_and_concat_audio import main as extract_concat_audio
from .split_audio import main as split_audio
from .trim_silence import main as trim_silence
from pathlib import Path


def main(args: list[str] = None):
    """
    Run the preprocessing pipeline for the rach3 dataset.

    Possible args are: --root_dir, --overwrite, and --output_dir

    Where root_dir is the root of the dataset, overwrite is whether to
    overwrite already existing files, and output_dir is where to put the
    processed files.

    To specify args, supply a list like so: ['--root_dir=a_path', ...]
    The only required argument is root_dir.

    The preprocessing steps are as follows:
      1. Extract audio from sessions, and concatenate it into the full session
      2. Remove silences at start and end of these new files
      3. Split files where there are long silences

    The goal is to reduce time drift between the flac audio and the video.

    There is one important limitation, the output (or the current working dir
    if no output dir is specified), must be within the root_dir.
    For example: '-o root_dir/output/ -d root_dir/'
    """

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
                             'does not exist, a new one will be created.',
                        default='./processed_audio')

    args = parser.parse_args(args)

    output_dir = Path(args.output_dir)

    # Each function acts a little differently, so we need to cater to each
    # individually. Mostly the functions are coded to not need much
    # babysitting, however when the user specifies a custom output path we do
    # need to do a little work.
    all_args = [args_concat, args_split, args_trim] = [], [], []

    if args.overwrite:
        [i.append("-w") for i in all_args]

    if args.output_dir:
        trimmed_dir = str(output_dir.joinpath("trimmed/"))
        concat_dir = str(output_dir.joinpath("concatenated/"))
        split_dir = str(output_dir.joinpath("split/"))

        args_trim.extend(["-o", trimmed_dir, "-d", concat_dir])
        args_concat.extend(["-o", concat_dir, "-d", args.root_dir])
        args_split.extend(["-pd", trimmed_dir, "-o", split_dir,
                           "-d", args.root_dir])
    else:
        [i.extend(["-d", args.root_dir]) for i in all_args]

    extract_concat_audio(args_concat)
    trim_silence(args_trim)
    split_audio(args_split)

    print(f"Successfully processed files to: {args.output_dir}")


if __name__ == "__main__":
    main()
