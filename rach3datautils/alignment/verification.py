from typing import Literal, Union, Optional, Callable

import numpy as np
import numpy.typing as npt
from dtw import dtw

from rach3datautils.types import PathLike
from rach3datautils.utils.track import Track

verification_issues = Literal["incorrect_len", "high_DTW"]


class Verify:
    """
    Contains modules useful for verifying alignment integrity.
    """

    def check_video_flac(self,
                         video: PathLike,
                         flac: PathLike) -> Union[verification_issues,
                                                  Literal[True]]:
        """
        Check whether a video and flac file are sufficiently aligned.

        Parameters
        ----------
        video : PathLike
        flac : PathLike

        Returns
        -------
        result : bool or string
            True if no issues were found, a string with the issue otherwise
        """

        video_track = Track(video)
        flac_track = Track(flac)

        if not self.check_len(video_track, flac_track):
            return "incorrect_len"
        elif not self.check_spectrogram(video_track, flac_track):
            return "high_DTW"
        return True

    @staticmethod
    def check_len(track_1: Track,
                  track_2: Track,
                  threshold: Optional[float] = None) -> bool:
        """
        Compare track lengths using a given threshold.

        Parameters
        ----------
        track_1 : Track
        track_2 : Track
        threshold : float, optional

        Returns
        -------
        bool
            whether the lengths are close enough according to the threshold
        """
        if threshold is None:
            threshold = 0.5

        if np.abs(track_1.frame_times[-1] -
                  track_2.frame_times[-1]) > threshold:
            return False
        return True

    def check_spectrogram(self,
                          track_1: Track,
                          track_2: Track,
                          dist_func: Optional[Callable] = None,
                          threshold: Optional[float] = None) -> bool:
        """
        Check the distance between two tracks spectrogram's. Additionally,
        checks whether the two given tracks length is close enough.

        Parameters
        ----------
        track_1 : PathLike
        track_2 : PathLike
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
            threshold = 2

        t1_spec = track_1.calc_log_spect_section()
        t2_spec = track_2.calc_log_spect_section()

        dist = dist_func(t1_spec[1], t2_spec[1])

        if dist > threshold:
            return False
        return True

    @staticmethod
    def spec_dtw(spec_1: npt.NDArray, spec_2: npt.NDArray) -> float:
        """
        Compare two spectrograms using DTW. Returns a number of best fit.

        Parameters
        ----------
        spec_1 : numpy array of first spectrogram
        spec_2 : numpy array of second spectrogram

        Returns
        -------
        score : float
            how close the two spectrograms are to each other
        """
        alignment = dtw(spec_1, spec_2)
        norm_dist: float = alignment.normalizedDistance

        return norm_dist
