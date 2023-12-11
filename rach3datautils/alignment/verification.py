from typing import Literal, Union, Optional, Callable

import numpy as np
import numpy.typing as npt
import partitura as pt
from fastdtw import fastdtw
from partitura.performance import Performance
from scipy.spatial.distance import cosine

from rach3datautils.types import PathLike
from rach3datautils.utils.multimedia import MultimediaTools
from rach3datautils.utils.track import Track

verification_issues = Literal["incorrect_len", "high_DTW", "midi_DTW"]


class Verify:
    """
    Contains modules useful for verifying alignment integrity.
    """

    def run_checks(self,
                   video: PathLike,
                   flac: PathLike,
                   midi: PathLike) -> Union[verification_issues,
                                            Literal[True]]:
        """
        Check whether a video and flac file are sufficiently aligned.

        Parameters
        ----------
        video : PathLike
        flac : PathLike
        midi: PathLike

        Returns
        -------
        result : bool or string
            True if no issues were found, a string with the issue otherwise
        """

        video_track = Track(video)
        flac_track = Track(flac)
        perf = pt.load_performance_midi(midi)

        if not self.check_len(video_track, flac_track, perf):
            return "incorrect_len"
#        elif not self.check_tracks(video_track, flac_track):
#            return "high_DTW"
#        elif not self.check_midi(perf, flac):
#            return "midi_DTW"
        return True

    @staticmethod
    def check_midi(midi: Performance,
                   flac: PathLike) -> bool:
        """
        Check a midi file against a flac file using their spectrogram's and
        DTW.

        Parameters
        ----------
        midi : Performance
        flac : PathLike

        Returns
        -------
        bool
        """
        # TODO
        return True

    @staticmethod
    def check_len(track_1: Track,
                  track_2: Track,
                  perf: Performance,
                  threshold: Optional[float] = None,
                  midi_early_threshold: Optional[float] = None) -> bool:
        """
        Compare track and performance lengths using a given threshold.

        Parameters
        ----------
        track_1 : Track
        track_2 : Track
        perf : Performance
        threshold : float, optional
            Maximal difference between lengths of two recordings before
            they're considered invalid. Default is 0.5 seconds.
        midi_early_threshold : float, optional
            Maximal difference between the last note-on and the end of a
            recording. Default is 5 seconds.

        Returns
        -------
        bool
            whether the lengths are close enough according to the threshold
        """
        if threshold is None:
            threshold = 0.5
        if midi_early_threshold is None:
            midi_early_threshold = 5

        last_note_mid = MultimediaTools.get_last_time(perf)
        duration_t1 = track_1.duration
        duration_t2 = track_2.duration

        if np.abs(duration_t1 - duration_t2) > threshold:
            return False
        elif last_note_mid > duration_t1 + threshold:
            return False
        elif last_note_mid > duration_t2 + threshold:
            return False
        elif last_note_mid < duration_t2 - midi_early_threshold:
            return False
        elif last_note_mid < duration_t1 - midi_early_threshold:
            return False
        return True

    def check_tracks(self,
                     track_1,
                     track_2) -> bool:
        """
        Check two tracks by comparing their spectrograms with DTW

        Parameters
        ----------
        track_1 : Track
        track_2 : Track

        Returns
        -------
        bool
        """
        t1_spec = track_1.calc_log_spect_section()
        t2_spec = track_2.calc_log_spect_section()

        return self.check_spectrogram(spect_1=t1_spec,
                                      spect_2=t2_spec)

    def check_spectrogram(self,
                          spect_1: npt.NDArray,
                          spect_2: npt.NDArray,
                          dist_func: Optional[Callable] = None,
                          threshold: Optional[float] = None) -> bool:
        """
        Check the distance between two tracks spectrogram's. Additionally,
        checks whether the two given tracks length is close enough.

        Parameters
        ----------
        spect_1 : npt.NDArray
        spect_2 : npt.NDArray
        dist_func : Callable distance function
            takes two numpy arrays and returns a float
        threshold : float
            at what value to say the alignment is not good

        Returns
        -------
        bool
            whether or not the tracks are sufficiently aligned
        """
        if dist_func is None:
            dist_func = self.spec_dtw
        if threshold is None:
            threshold = 10

        dist = dist_func(spect_1[1], spect_2[1])

        if dist > threshold:
            return False
        return True

    def spec_dtw(self, spec_1: npt.NDArray, spec_2: npt.NDArray) -> float:
        """
        Compare two spectrograms using DTW. Returns the normalized distance.

        Parameters
        ----------
        spec_1 : numpy array of first spectrogram
        spec_2 : numpy array of second spectrogram

        Returns
        -------
        score : float
            how close the two spectrograms are to each other
        """
        spec_1_norm = (spec_1-np.min(spec_1))/(np.max(spec_1)-np.min(spec_1))
        spec_2_norm = (spec_2-np.min(spec_2))/(np.max(spec_2)-np.min(spec_2))

        dist, path = fastdtw(spec_1_norm, spec_2_norm, dist=cosine)
        dist_norm = self._calculate_path_norm(
            path,
            (spec_1.shape[0], spec_2.shape[0])
        )
        return dist_norm

    @staticmethod
    def _calculate_path_norm(path: list[tuple[int, int]],
                             dims: tuple[int, int]):
        """
        Calculate the deviation of a DTW path from the diagonal and normalize
        it.

        Parameters
        ----------
        path : list[tuple[int, int]]
            DTW path
        dims : tuple[int, int]
            The max (x, y) dimensions of the path space

        Returns
        -------
        norm_dist : float
            The total distance divided by the optimal distance. Should always
            be more than 1. A higher number is worse.
        """
        optimal_slope = dims[1] / dims[0]
        area = 0
        for i in path:
            area += abs(i[1] - i[0] * optimal_slope)
        # Multiply by 100 because we'll get very small floats otherwise
        area_norm = (area / ((dims[1] * dims[0]) / 2)) * 100
        return area_norm
