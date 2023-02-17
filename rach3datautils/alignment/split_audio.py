import partitura as pt
import argparse
from pathlib import Path
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.backup_files import PathLike
import os


def main(root_dir: PathLike,
         output_dir: PathLike = None,
         processed_dir: PathLike = None,
         overwrite: bool = None):
    """
    Detect pauses in playing based on midi file, and split audio at these
    pauses. The aim is to reduce time drifting between the video file and flac
    file.
    """
    if root_dir is None:
        raise AttributeError("root_dir must be supplied!")
    if output_dir is None:
        output_dir = "./audio_split/"
    if processed_dir is None:
        processed_dir = "./trimmed_silence/"
    if overwrite is None:
        overwrite = False

    output_dir = Path(output_dir)
    pd = Path(processed_dir)
    root_dir = Path(root_dir)

    if output_dir.suffix:
        raise AttributeError("output_dir must be a path to a valid directory")
    elif not pd.is_dir():
        raise AttributeError("processed_directory must be a path to a valid "
                             "directory")

    if not output_dir.exists():
        os.mkdir(output_dir)
    if not pd.exists():
        os.mkdir(pd)

    a_d_tools = AudioVideoTools()

    # We are working with midi and audio files here, so lets gather those.
    dataset = DatasetUtils(root_dir)
    pd_util = DatasetUtils(pd)
    all_files = [
        i for i in dataset.get_files_by_type(filetype=["mid", "flac"])
        if dataset.is_valid_midi(i) or dataset.is_full_flac(i)]

    # Get all the full audio files from the processed folder.
    [all_files.append(i) for i in pd_util.get_files_by_type(["mp3"])
     if pd_util.is_trimmed(i)]

    # Get rid of the warmup files.
    all_files_no_warmup = [
        i for i in all_files if not DatasetUtils.is_warmup(i)]

    # Now we sort the files into a nice dictionary object.
    files = dataset.sort_by_date_and_session(all_files_no_warmup)

    # Finally we can start actually applying changes to the files, one
    # session at a time.
    for _, session in files.items():
        # Search for the files we need.
        midi_file, flac_file, full_audio_file = None, None, None
        for i in session:
            if i.suffix == ".mid":
                midi_file = i
            elif i.suffix == ".flac":
                flac_file = i
            elif i.suffix == ".mp3":
                full_audio_file = i

        if midi_file is None or flac_file is None or full_audio_file is None:
            raise AttributeError("Some files in the database are missing.")

        # Load midi file and find spots with no playing.
        midi = pt.load_performance_midi(midi_file)
        breaks = a_d_tools.find_breaks(midi)

        # Because we've trimmed the files to the first note, we need to shift
        # all the timestamps so that the first note has a time of zero.
        first_note = a_d_tools.get_first_time(midi)
        breaks -= first_note

        # Get duration of current file. Used to calculate where to split it.
        duration = a_d_tools.get_len(flac_file)

        # We also want the timestamp of the last note. This is necessary in
        # order to calculate the split points from the right.
        duration_midi = a_d_tools.get_last_time(midi)

        # Calculate the exact timestamps at which to split.
        breakpoints = []
        for m in breaks:
            breakpoints.append(m[0] + ((m[1] - m[0]) / 2))

        for i, b in enumerate(breakpoints):
            if b > duration / 2:
                breakpoints[i] = duration - (duration_midi - b)

        # Calculate exact timestamps at which to split file.
        splits = []
        prev_point = 0
        for m in breakpoints:
            difference = m - prev_point
            splits.append((prev_point, prev_point + difference))
            prev_point = prev_point + difference

        splits.append((splits[-1][1], duration))

        # Split files at the calculated timestamps
        for m, (n, o) in enumerate(splits):
            outputs = [(i, output_dir.joinpath(
                i.stem + f"_split{m+1}" + i.suffix))
                       for i in [flac_file, full_audio_file]]

            [a_d_tools.split_audio(audio_path=i[0],
                                   split_start=n,
                                   split_end=o,
                                   output=i[1],
                                   overwrite=overwrite) for i in outputs]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Midi Based Video and Audio Splitter",
        description="Split video and audio files where there are breaks in the "
                    "music."
    )

    parser.add_argument("-d", "--root_directory",
                        action="store",
                        help="Root directory of the dataset. If not set, the"
                             "current working folder is used.",
                        required=True)

    parser.add_argument("-w", "--overwrite",
                        action="store_true",
                        help="Whether to overwrite the files if they already"
                             "exist.")
    parser.add_argument("-o", "--output_dir",
                        action="store",
                        help="Directory where to store output files.",
                        default="./audio_split/")
    parser.add_argument("-pd", "--processed_directory",
                        action="store",
                        help="The directory where the full mp3 files are kept."
                             "Where the output of trim_silence.py went.",
                        default="./trimmed_silence/")

    args = parser.parse_args()
    main(root_dir=args.root_directory,
         overwrite=args.overwrite,
         output_dir=args.output_directory,
         processed_dir=args.processed_directory)
