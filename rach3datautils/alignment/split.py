import partitura as pt
from partitura.performance import Performance
from pathlib import Path
from typing import Optional, Union, List, Tuple
from rach3datautils.exceptions import MissingFilesError
from rach3datautils.utils.multimedia import MultimediaTools
from rach3datautils.alignment.sync import load_and_sync
from rach3datautils.types import timestamps, note_sections, PathLike
import numpy as np
import numpy.typing as npt


def split_video_flac_mid(
        performance: Performance,
        video: Path,
        flac: Path,
        midi: Path,
        audio: Path,
        output_dir: PathLike,
        overwrite: Optional[bool] = None,
        break_size: Optional[float] = None,
):
    """
    Split video, flac, and midi files from the same session based on breaks
    in playing and maximum section sizes.
    Parameters
    ----------
    audio : Path
        subsession AAC audio
    performance : Performance
        subsession partitura performance object
    midi : Path
        subsession midi file
    video : Path
        full video for the subsession
    flac : Path
        subsession flac file
    output_dir : PathLike
        where to output the new splits
    overwrite : bool, optional
        whether to overwrite already existing files
    break_size : float, optional
        how long the maximum break should be

    Returns
    -------
    None
    """
    if overwrite is None:
        overwrite = False

    required = [midi, video, flac, performance]
    if [i for i in required if i is None]:
        raise MissingFilesError("Midi and video are required for split_video "
                                "to function.")

    if not isinstance(output_dir, Path):
        output_dir: Path = Path(output_dir)

    splits_vid = Splits().get_split_points_sync(
        audio=audio,
        flac=flac,
        performance=performance,
        break_size=break_size
    )
    splits_flac = Splits().get_split_points(
        performance=performance,
        break_size=break_size
    )
    split_va_at_timestamps(
        splits=splits_vid,
        file=video,
        output_dir=output_dir,
        overwrite=overwrite
    )
    split_va_at_timestamps(
        splits=splits_flac,
        file=flac,
        output_dir=output_dir,
        overwrite=overwrite,
        reencode=True  # For some reason, the splits end up being slightly
    )  # off sometimes if we don't re-encode. At least it's just the audio.
    split_midi_at_timestamps(
        splits=splits_flac,
        performance=performance,
        output_dir=output_dir,
        file=midi
    )


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
        """
        Parameters
        ----------
        break_size : int, optional
            how long in seconds is considered a break
        min_section_size : int, optional
            sections under this length in seconds will be cut out
        max_section_size : int, optional
            sections over this length in seconds will be split
        """
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
            audio: PathLike,
            performance: Performance,
            flac: PathLike,
            break_size: Optional[Union[float, int]] = None
    ) -> List[timestamps]:
        """
        Calculate split points in seconds for an aac file using the sync
        function to identify correct start and end times for each section.

        Provides significantly better results than regular get_split_points
        for files that may not be synchronized fully with the midi.

        Parameters
        ----------
        audio : PathLike
            full audio file that corresponds to the flac
        flac : PathLike
            flac file synced to midi
        performance : Performance
            partitura performance object
        break_size : Union[float, int], optional
            the amount of time between notes to be considered a break.

        Returns
        -------
        timestamp_list : List[timestamps]
            a list containing timestamps of the sections in seconds
        """
        if break_size is None:
            break_size = self.BREAK_SIZE

        if [i for i in [audio, performance, flac] if i is None]:
            raise MissingFilesError("get_split_points_sync requires a midi "
                                    "and audio file to be present in the "
                                    "session.")

        break_notes = MultimediaTools.find_breaks(
            performance=performance,
            length=break_size,
            return_notes=True
        )

        section_notes = self.breaks_to_sections(
            performance=performance,
            breaks=break_notes
        )
        sections = self.check_section_lengths(
            note_array=performance.note_array(),
            sections=section_notes
        )

        first_last_times = load_and_sync(
            flac=flac,
            performance=performance,
            audio=audio,
            sync_args={"notes_index": (0, -1),
                       "search_period": 180,
                       "window_size": 100},
            track_args={"hop_size": int(np.round(44100 * 0.1))}
        )
        note_array = performance.note_array()
        first_time = note_array['onset_sec'][0]

        section_times: List[timestamps] = []
        for i in sections:
            start_note = note_array['onset_sec'][i[0]] - first_time
            start_time = first_last_times[0] + start_note

            end_note = (note_array['onset_sec'][i[1]] +
                        note_array['duration_sec'][i[1]]) - first_time
            end_time = first_last_times[0] + end_note

            times = load_and_sync(
                flac=flac,
                audio=audio,
                performance=performance,
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
        performance : Performance
        breaks : List[Tuple[int, int]]
            output from break_notes

        Returns
        -------
        note_section_list : List[note_sections]
            a list containing start and end points of sections as tuples
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
        These limits are set when initializing the object.

        Parameters
        ----------
        note_array : npt.NDArray
            note array as generated by Performance.note_array()
        sections : List[note_sections]
            sections to be checked, using note indexes as start and end

        Returns
        -------
        note_section_list : List[note_sections]
            List containing new note sections.
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

        Parameters
        ----------
        sections : List[note_sections]
            list containing note sections (tuples with note indices)
        performance : Performance
            partitura performance object corresponding to sections

        Returns
        -------
        timestamps_list : List[timestamps]
            contains the sections converted to timestamps
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
            performance: Performance,
            break_size: Optional[Union[float, int]] = None
    ) -> List[timestamps]:
        """
        Calculate splits for a file according to midi timestamps.

        Parameters
        ----------
        performance : Performance
            midi file performance to use when identifying breaks
        break_size : Union[float, int], optional
            how much time in seconds is considered a break

        Returns
        -------
        timestamps_list : List[timestamps]
            Contains start and stop times of all sections as tuples
        """
        if break_size is None:
            break_size = self.BREAK_SIZE

        breakpoints = MultimediaTools.find_breaks(
            performance=performance,
            length=break_size,
            return_notes=True
        )
        breaks = self.breaks_to_sections(
            performance=performance,
            breaks=breakpoints,
        )
        breaks = self.check_section_lengths(
            note_array=performance.note_array(),
            sections=breaks,
        )
        breaks = self.convert_to_timestamps(breaks, performance=performance)

        return breaks


def split_va_at_timestamps(splits: List[timestamps],
                           file: Path,
                           output_dir: Path,
                           overwrite: bool,
                           reencode: Optional[bool] = None):
    """
    Split a video or audio given a list of timestamps and output to a
    directory. Split names are calculated based on the original file.

    Parameters
    ----------
    splits : List[timestamps]
        list of section timestamps
    file : Path
        the original file to be split
    output_dir : Path
        directory where to put new splits
    overwrite : bool
        whether to overwrite any already existing files
    reencode : bool, optional
        whether to reencode the file, will increase runtime greatly

    Returns
    -------
    None
    """
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


def split_midi_at_timestamps(splits: List[timestamps],
                             performance: Performance,
                             output_dir: Path,
                             file: Path):
    """
    Split a performance and save it to midi files.
    Parameters
    ----------
    splits : List[timestamps]
        list of section timestamps
    performance : Performance
        the performance corresponding to the original midi file
    output_dir : Path
        where to output the new splits
    file : Path
        the original midi file to be split

    Returns
    -------
    None
    """
    subperfs = MultimediaTools.split_performance(
        performed_part=performance[0],
        split_points=splits
    )
    for split_no, pp_split in enumerate(subperfs):
        output_path_mid = output_dir.joinpath(
            file.stem + f"_split{split_no + 1}" + file.suffix
        )
        pt.save_performance_midi(
            performance_data=pp_split,
            out=output_path_mid
        )


def calc_splits(breakpoints: List[float],
                startpoint: Optional[float] = None) -> List[timestamps]:
    """
    Essentially invert a list of breakpoints, return the time between the
    breakpoints.

    Parameters
    ----------
    breakpoints : List[float]
        list containing breakpoints
    startpoint : float, optional
        the point to start calculating from, in case the first section
        does not start an zero

    Returns
    -------
    timestamps_list : List[timestamps]
        contains the timestamps between the breakpoints
    """
    if startpoint is None:
        startpoint = 0

    splits: List[timestamps] = []
    prev_point = startpoint
    for m in breakpoints:
        difference = m - prev_point
        splits.append((prev_point, prev_point + difference))
        prev_point = prev_point + difference

    return splits
