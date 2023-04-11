from partitura.performance import Performance
from pathlib import Path
from typing import Optional, Union, List, Tuple
from rach3datautils.exceptions import MissingFilesError
from rach3datautils.utils.multimedia import MultimediaTools
from rach3datautils.extra.backup_files import PathLike
from rach3datautils.utils.session import Session
from rach3datautils.alignment.sync import load_and_sync
import numpy as np
import numpy.typing as npt


timestamps = Tuple[float, float]
note_sections = Tuple[int, int]


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

    required = [subsession.midi.file, subsession.video.file,
                subsession.flac.file]
    if [i for i in required if i is None]:
        raise MissingFilesError("Midi and video are required for split_video "
                                "to function.")

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
        reencode=True  # For some reason, the splits end up being slightly
    )  # off sometimes if we don't re-encode


class Splits:
    """
    Class containing functions for calculating splits using midi files.
    """
    BREAK_SIZE = 5
    MIN_SECTION_SIZE = 60
    MAX_SECTION_SIZE = 180

    def __init__(self,
                 break_size: Optional[int] = None,
                 min_section_size: Optional[int] = None,
                 max_section_size: Optional[int] = None):
        if break_size is None:
            break_size = self.BREAK_SIZE
        if min_section_size is None:
            min_section_size = self.MIN_SECTION_SIZE
        if max_section_size is None:
            max_section_size = self.MAX_SECTION_SIZE

        self.break_size = break_size
        self.min_section_size = min_section_size
        self.max_section_size = max_section_size

    def get_split_points_sync(
            self,
            session: Session,
            break_size: Optional[Union[float, int]] = None
    ) -> List[timestamps]:
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
            raise MissingFilesError("get_split_points_sync requires a midi "
                                    "and audio file to be present in the "
                                    "session.")

        break_notes = MultimediaTools().find_breaks(
            midi=session.performance,
            length=break_size,
            return_notes=True
        )

        section_notes = self.breaks_to_sections(
            performance=session.performance,
            breaks=break_notes
        )
        sections = self.check_section_lengths(
            note_array=session.performance.note_array(),
            sections=section_notes
        )

        first_last_times = load_and_sync(
            flac=session.flac.file,
            performance=session.performance,
            audio=session.audio.file,
            sync_args={"notes_index": (0, -1),
                       "search_period": 180,
                       "window_size": 100},
            track_args={"hop_size": int(np.round(44100 * 0.1))}
        )
        note_array = session.performance.note_array()
        first_time = note_array['onset_sec'][0]

        section_times: List[timestamps] = []
        for i in sections:
            start_note = note_array['onset_sec'][i[0]] - first_time
            start_time = first_last_times[0] + start_note

            end_note = (note_array['onset_sec'][i[1]] +
                        note_array['duration_sec'][i[1]]) - first_time
            end_time = first_last_times[0] + end_note

            times = load_and_sync(
                flac=session.flac.file,
                audio=session.audio.file,
                performance=session.performance,
                sync_args={"notes_index": (i[0], i[1]),
                           "search_period": 15,
                           "start_end_times": (start_time, end_time),
                           "window_size": 1000},
                track_args={"hop_size": int(np.round(44100 * 0.005))}
            )
            section_times.append(times)

        return section_times

    @staticmethod
    def breaks_to_sections(
            performance: Performance,
            breaks: List[Tuple[int, int]]
    ) -> List[note_sections]:
        """
        Take a list with the output from find_breaks and convert it so that
        the notes are pointing to the start and end of the sections between
        breaks.

        Filters out sections with very few notes.

        Parameters
        ----------
        performance: Partitura performance
        breaks: output from break_notes

        Returns a list containing start and end of sections
        -------
        """
        prev_note: int = 0
        sections: List[note_sections] = []
        for i in breaks:
            sections.append((prev_note, i[0]))
            prev_note = i[1]

        sections.append((prev_note, len(performance.note_array()) - 1))

        return sections

    def check_section_lengths(
            self,
            note_array: npt.NDArray,
            sections: List[note_sections]
    ) -> List[note_sections]:
        """
        Check the lengths of sections to make sure they are within the limits
        set by max_section_len and min_section_len.
        """
        new_sections: List[note_sections] = []
        last_note = sections[0][0]
        for i in sections:
            sect_len = note_array["onset_sec"][i[1]] - \
                       note_array["onset_sec"][last_note]
            if sect_len < self.min_section_size:
                continue
            elif sect_len > self.max_section_size:
                shorter_sections = self._check_max_len(
                    note_array=note_array,
                    prev_note=last_note,
                    end_note=i[1]
                )
                last_len = note_array["onset_sec"][shorter_sections[-1][1]] - \
                    note_array["onset_sec"][shorter_sections[-1][0]]
                if last_len < self.min_section_size:
                    shorter_sections.pop(-1)

                new_sections.extend(shorter_sections)

            else:
                new_sections.append((last_note, i[1]))

            last_note = i[1]

        return new_sections

    def _check_max_len(self,
                       note_array: npt.NDArray,
                       prev_note: int,
                       end_note: int):
        sect_time = note_array["onset_sec"][end_note] - \
                    note_array["onset_sec"][prev_note]
        sect_len = end_note - prev_note
        if sect_time > self.max_section_size:
            midpoint = prev_note + sect_len // 2
            sections = [(prev_note, midpoint)]
            sections.extend(self._check_max_len(note_array,
                                                midpoint,
                                                end_note))
        else:
            return [(prev_note, end_note)]
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
            last_time = note_array['onset_sec'][i[1]] + \
                note_array['duration_sec'][i[1]]
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

        breakpoints = MultimediaTools.find_breaks(
            midi=midi,
            length=break_size,
            return_notes=True
        )
        breaks = self.breaks_to_sections(
            performance=midi,
            breaks=breakpoints,
        )
        breaks = self.check_section_lengths(
            note_array=midi.note_array(),
            sections=breaks,
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

        MultimediaTools.extract_section(
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
