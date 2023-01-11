import partitura as pt
import argparse
from pathlib import Path
from dataset_utils import DatasetUtils
from video_audio_tools import AudioVideoTools


def main(args: list[str] = None):
    """
    Detect pauses in playing based on midi file, and split audio at these pauses.
    The aim is to reduce time drifting between the video file and flac file.
    """
    parser = argparse.ArgumentParser(
        prog="Midi Based Video and Audio Splitter",
        description="Split video and audio files where there are breaks in the "
                    "music."
    )

    parser.add_argument("-d", "--root_directory",
                        action="store",
                        help="Root directory of the dataset. If not set, the"
                             "current working folder is used.",
                        default="./trimmed_silence")

    parser.add_argument("-w", "--overwrite",
                        action="store_true",
                        help="Whether to overwrite the files if they already"
                             "exist.")
    parser.add_argument("-o", "--output_dir",
                        action="store",
                        help="Directory where to store output files.",
                        default="./audio_split")
    parser.add_argument("-pd", "--processed_directory",
                        action="store",
                        help="The directory where the full mp3 files are kept."
                             "Where the output of trim_silence.py went.",
                        default="./trimmed_silence")

    args = parser.parse_args(args)
    output_dir = Path(args.output_dir)
    pd = Path(args.processed_directory)
    a_d_tools = AudioVideoTools()

    # We are working with midi and audio files here, so lets gather those.
    dataset = DatasetUtils(args.root_directory)
    pd_util = DatasetUtils(pd)
    all_files = [
        i for i in dataset.get_files_by_type(filetype=["mid"])
            if dataset.is_valid_midi(i)]

    # Get all the full audio files from the processed folder.
    [all_files.append(i) for i in pd_util.get_files_by_type(["mp3", "flac"])
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

        # Calculate the exact timestamps at which to split.
        breakpoints = []
        for m in breaks:
            breakpoints.append(m[0] + ((m[1] - m[0]) / 2))

        # Get duration of current file. Used to calculate where to split it.
        duration = a_d_tools.get_len(flac_file)

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
            outputs = [output_dir.joinpath(i.stem + f"_split{m+1}" + i.suffix)
                       for i in [flac_file, full_audio_file]]

            [a_d_tools.split_audio(audio_path=flac_file,
                                  split_start=n,
                                  split_end=o,
                                  output=i,
                                  overwrite=args.overwrite)
            for i in outputs]

if __name__ == "__main__":
    main()
