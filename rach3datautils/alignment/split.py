from partitura.performance import Performance
import argparse
from pathlib import Path
from typing import Optional, Union, List, Tuple
from rach3datautils.dataset_utils import DatasetUtils
from rach3datautils.exceptions import MissingSubsessionFilesError
from rach3datautils.video_audio_tools import AudioVideoTools
from rach3datautils.backup_files import PathLike
from rach3datautils.session import Session
from rach3datautils.alignment.sync import timestamps_spec
import os
import numpy as np


timestamps = Tuple[float, float]
note_sections = Tuple[int, int]


def main(root_dir: PathLike,
         output_dir: PathLike,
         overwrite: bool):
    """
    Detect pauses in playing based on midi file, and split audio at these
    pauses. The aim is to reduce time drifting between the video file and flac
    file.
    """
    output_dir = Path(output_dir)

    if output_dir.suffix:
        raise AttributeError("output_dir must be a path to a valid directory")

    if not output_dir.exists():
        os.mkdir(output_dir)

    dataset = DatasetUtils(root_dir)
    subsessions = dataset.get_sessions(filetype=[".mid", ".mp4", ".flac",
                                                 ".aac"])

    for i in subsessions:
        split_video_and_flac(
            subsession=i,
            overwrite=overwrite,
            output_dir=output_dir
        )


def split_video_and_flac(
        subsession: Session,
        output_dir: PathLike,
        overwrite: Optional[bool] = None,
        break_size: Optional[float] = None,
):
    """
    Split a video and flac according to breaks in its corresponding midi file.
    """
    if overwrite is None:
        overwrite = False

    required = [subsession.midi.file, subsession.video.trimmed,
                subsession.flac.file]
    if [i for i in required if i is None]:
        raise MissingSubsessionFilesError("Midi and video are required for "
                                          "split_video to function.")

    if not isinstance(output_dir, Path):
        output_dir: Path = Path(output_dir)

    midi = subsession.performance
    video = subsession.video.file
    flac = subsession.flac.file

    splits_vid = Splits().get_split_points_sync(
        session=subsession,
        break_size=break_size
    )
    splits_flac = Splits().get_split_points(
        midi=midi,
        break_size=break_size
    )
    split_at_timestamps(
        splits=splits_vid,
        file=video,
        output_dir=output_dir,
        overwrite=overwrite
    )
    split_at_timestamps(
        splits=splits_flac,
        file=flac,
        output_dir=output_dir,
        overwrite=overwrite,
        reencode=True
    )


class Splits:
    """
    Class containing functions for calculating splits using midi files.
    """
    BREAK_SIZE = 5
    MIN_SECTION_SIZE = 20

    def get_split_points_sync(
            self,
            session: Session,
            break_size: Optional[Union[float, int]] = None) -> \
            List[timestamps]:
        """
        Calculate split points in seconds for an aac/video and flac file using
        the sync function to identify correct start and end times for each
        section.

        Provides significantly better results than regular get_split_points.

        Parameters
        ----------
        session: Session object containing at least a midi, flac, and aac file.
        break_size: the amount of time between notes to be considered a break.

        Returns a list containing timestamps of sections
        -------

        """
        if break_size is None:
            break_size = self.BREAK_SIZE

        if [i for i in [session.audio.file, session.performance,
                        session.flac.file] if i is None]:
            raise MissingSubsessionFilesError("get_split_points_sync requires"
                                              " a midi and audio file to "
                                              "be present in the session.")

        break_notes = AudioVideoTools().find_breaks(
            midi=session.performance,
            length=break_size,
            return_notes=True
        )

        section_notes = self.breaks_to_sections(
            performance=session.performance,
            breaks=break_notes
        )

        first_last_times = timestamps_spec(
            subsession=session,
            notes_index=(0, -1),
            search_period=180,
            window_size=100,
            hop_size=int(np.round(44100 * 0.1))
        )
        note_array = session.performance.note_array()

        section_times: List[timestamps] = []
        for i in section_notes:
            start_time = first_last_times[1] + note_array['onset_sec'][i[0]]
            end_time = first_last_times[1] + note_array['onset_sec'][i[1]]

            times = timestamps_spec(
                subsession=session,
                notes_index=(i[0], i[1]),
                search_period=10,
                start_end_times=(start_time, end_time),
                window_size=1000,
                hop_size=int(np.round(44100 * 0.005))
            )[1:]

            section_times.append(times)

        return section_times

    def breaks_to_sections(self,
                           performance: Performance,
                           breaks: List[Tuple[int, int]],
                           min_section_size: Optional[int] = None) -> \
            List[note_sections]:
        """
        Take a list with the output from find_breaks and convert it so that
        the notes are pointing to the start and end of the sections between
        breaks.

        Filters out sections with very few notes.

        Parameters
        ----------
        min_section_size: the minimum amount of notes required in a section
        performance: Partitura performance
        breaks: output from break_notes

        Returns a list containing start and end of sections
        -------
        """
        if min_section_size is None:
            min_section_size = self.MIN_SECTION_SIZE

        prev_note: int = 0
        sections: List[note_sections] = []
        for i in breaks:
            if i[0] - prev_note < min_section_size:
                continue
            sections.append((prev_note, i[0]))
            prev_note = i[1]

        sections.append((prev_note, len(performance.note_array())-1))

        return sections

    @staticmethod
    def convert_to_timestamps(sections: List[note_sections],
                              performance: Performance) -> List[timestamps]:
        """
        Convert a list of note_sections to a list of timestamps
        """
        note_array = performance.note_array()
        timestamp_list: List[timestamps] = []
        for i in sections:
            first_time = note_array['onset_sec'][i[0]]
            last_time = note_array['onset_sec'][i[1]]
            timestamp_list.append((first_time, last_time))

        return timestamp_list

    def get_split_points(
            self,
            midi: Performance,
            break_size: Optional[Union[float, int]] = None
    ) -> List[timestamps]:
        """
        Calculate splits for a file according to midi timestamps.

        Parameters
        ----------
        midi: midi file to use when identifying breaks
        break_size: how much time is considered a break

        Returns a list containing start and stop times of all sections
        -------
        """
        if break_size is None:
            break_size = self.BREAK_SIZE

        breakpoints = AudioVideoTools.find_breaks(
            midi=midi,
            length=break_size,
            return_notes=True
        )
        breaks = self.breaks_to_sections(
            performance=midi,
            breaks=breakpoints,
        )
        breaks = self.convert_to_timestamps(breaks, performance=midi)

        return breaks


def split_at_timestamps(splits: list,
                        file: Path,
                        output_dir: Path,
                        overwrite: bool,
                        reencode: Optional[bool] = None):
    for split_no, (start, end) in enumerate(splits):
        output_path_video = output_dir.joinpath(
            file.stem + f"_split{split_no + 1}" + file.suffix
        )

        if output_path_video.exists() and not overwrite:
            return

        AudioVideoTools.extract_section(
            file=file,
            start=start,
            end=end,
            output_file=output_path_video,
            reencode=reencode
        )


def calc_splits(breakpoints: list,
                startpoint: Optional[float] = None) -> list:
    if startpoint is None:
        startpoint = 0

    splits = []
    prev_point = startpoint
    for m in breakpoints:
        difference = m - prev_point
        splits.append((prev_point, prev_point + difference))
        prev_point = prev_point + difference
    return splits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Midi Based Video and Audio Splitter",
        description="Split video and audio files where there are breaks in "
                    "the music based on a midi file."
    )
    parser.add_argument(
        "-d", "--root_directory",
        action="store",
        help="Root directory of the dataset. If not set, the"
             "current working folder is used.",
        required=True
    )
    parser.add_argument(
        "-w", "--overwrite",
        action="store_true",
        help="Whether to overwrite the files if they already"
             "exist."
    )
    parser.add_argument(
        "-o", "--output_directory",
        action="store",
        help="Directory where to store output files.",
        default="./audio_split/"
    )
    args = parser.parse_args()

    main(
        root_dir=args.root_directory,
        overwrite=args.overwrite,
        output_dir=args.output_directory
    )
