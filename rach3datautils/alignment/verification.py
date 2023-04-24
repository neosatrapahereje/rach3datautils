from typing import Literal, Union, Optional, Callable

import numpy as np
import numpy.typing as npt
from fastdtw import fastdtw
from scipy.spatial.distance import cosine
from partitura.performance import Performance
import partitura as pt

from rach3datautils.types import PathLike
from rach3datautils.utils.track import Track
from rach3datautils.utils.multimedia import MultimediaTools

verification_issues = Literal["incorrect_len", "high_DTW"]


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
        elif not self.check_tracks(video_track, flac_track):
            return "high_DTW"
        elif not self.check_midi(midi, flac):
            return "midi_DTW"
        return True

    def check_midi(self,
                   midi: Performance,
                   flac: PathLike) -> Literal[True, "midi_DTW"]:
        # TODO
        ...

    @staticmethod
    def check_len(track_1: Track,
                  track_2: Track,
                  perf: Performance,
                  threshold: Optional[float] = None) -> bool:
        """
        Compare track and performance lengths using a given threshold.

        Parameters
        ----------
        track_1 : Track
        track_2 : Track
        perf : Performance
        threshold : float, optional

        Returns
        -------
        bool
            whether the lengths are close enough according to the threshold
        """
        if threshold is None:
            threshold = 0.5

        last_note_mid = MultimediaTools.get_last_offset(perf)
        last_note_t1 = track_1.frame_times[-1]
        last_note_t2 = track_2.frame_times[-1]

        if np.abs(last_note_t1 - last_note_t2) > threshold:
            return False
        elif np.abs(last_note_mid - last_note_t1) > threshold or \
                np.abs(last_note_mid - last_note_t2) > threshold:
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
            threshold = 2

        dist = dist_func(spect_1[1], spect_2[1])

        if dist > threshold:
            return False
        return True

    @staticmethod
    def spec_dtw(spec_1: npt.NDArray, spec_2: npt.NDArray) -> float:
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
        dist_norm = 1 - dist
        return dist_norm
