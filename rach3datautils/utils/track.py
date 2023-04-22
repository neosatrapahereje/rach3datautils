from pathlib import Path
from typing import Optional, TypedDict, Tuple, Union, Dict

import madmom
import numpy as np
import numpy.typing as npt
from madmom.audio.signal import FramedSignal

from rach3datautils.types import PathLike, timestamps
from rach3datautils.utils.multimedia import MultimediaTools


class TrackArgs(TypedDict, total=False):
    frame_size: Optional[int]
    sample_rate: Optional[int]
    hop_size: Optional[float]


class Track:
    """
    Class for a single audio track. Can take videos as well and will extract
    their audio when loading into memory.
    """
    FRAME_SIZE = 8372
    SAMPLE_RATE = 44100
    HOP_SIZE = int(np.round(SAMPLE_RATE * 0.025))

    def __init__(self,
                 filepath: PathLike,
                 frame_size: Optional[int] = None,
                 sample_rate: Optional[int] = None,
                 hop_size: Optional[float] = None):
        """
        Parameters
        ----------
        filepath : PathLike
            path to the audio or video file.
        frame_size : int, optional
            track frame size to use when loading, default: 8372
        sample_rate : int, optional
            sample rate to be used when loading, default: 44100
        hop_size : float, optional
            essentially the resolution, default: 1102
        """
        if frame_size is None:
            frame_size = self.FRAME_SIZE
        if sample_rate is None:
            sample_rate = self.SAMPLE_RATE
        if hop_size is None:
            hop_size = self.HOP_SIZE

        filepath = Path(filepath)

        if filepath.suffix == ".mp4":
            data = MultimediaTools().load_file_audio(filepath=filepath,
                                                     sample_rate=sample_rate)
        elif filepath.suffix == ".aac":
            data = filepath
        elif filepath.suffix == ".flac":
            data = filepath
        else:
            raise AttributeError("Filepath should point to an AAC file or "
                                 "mp4 file.")

        self.hop_size: int = hop_size
        self.sample_rate: int = sample_rate
        self.filepath: PathLike = filepath

        self.signal: FramedSignal = self.load_framed_signal(
            data=data,
            frame_size=frame_size,
            hop_size=hop_size,
            sample_rate=sample_rate
        )
        self.frame_times: npt.NDArray = self.calc_frame_times()

    def get_frame(self, time: float) -> int:
        """
        Get the closest frame to a certain timestamp is seconds. Inverse of
        get_time.

        Parameters
        ----------
        time : float
            timestamp in seconds

        Returns
        -------
        frame : int
            the frame index closest to the time given
        """
        return abs((self.frame_times - time)).argmin()

    def calc_frame_times(self) -> npt.NDArray:
        """
        Calculate the frame times of the signal.

        Returns
        -------
        frame_times : npt.NDArray
            has an index for every frame at which you can see the time
        """
        return np.arange(
            self.signal.shape[0]
        ) * (self.hop_size / self.sample_rate)

    @staticmethod
    def load_framed_signal(data: Union[PathLike, npt.NDArray],
                           frame_size: int,
                           hop_size: int,
                           sample_rate: int,
                           kwargs: Optional[Dict] = None) -> FramedSignal:
        """
        Load a file into a signal.

        Parameters
        ----------
        data : Union[PathLike, npt.NDArray]
            path to audio file or actual audio file data in numpy array.
        frame_size : int
            frame size to use when loading the Signal.
        hop_size : int
            hop size to use when loading the FramedSignal.
        sample_rate : int
            sample rate to use when loading the Signal.
        kwargs : Dict
            any additional arguments to be passed to madmom.audio.Signal

        Returns
        -------
        framed_signal : FramedSignal
        """
        if kwargs is None:
            kwargs = {}
        if isinstance(data, Path):
            data = str(data)

        signal = madmom.audio.Signal(
            data,
            sample_rate=sample_rate,
            num_channels=1,
            norm=True,
            **kwargs
        )
        f_signal = madmom.audio.FramedSignal(
            signal=signal,
            frame_size=frame_size,
            hop_size=hop_size
        )

        return f_signal

    def calc_log_spect_section(
            self,
            start: Optional[float] = None,
            end: Optional[float] = None,
            spectrogram_clip: Optional[Tuple[int, int]] = None
    ) -> Tuple[timestamps, npt.NDArray]:
        """
        Generate a certain section of the log_spectrogram given start and end
        points.
        Uses the logarithmic filtered spectrogram by default.

        spectrogram_clip specifies the start and end of the frequency bands
        index, useful for reducing ram usage and improving performance if you
        don't need the whole range of frequency bands.

        Parameters
        ----------
        start : float, optional
            start time in seconds, default zero
        end : float, optional
            end time in seconds, default is end of file
        spectrogram_clip : Tuple[int, int], optional
            tuple of indexes. Frequency bands within these
            indexes will be kept.

        Returns
        -------
        start_end_spectrogram : Tuple[time_section, npt.NDArray]
            exact start and end times of spectrogram, spectrogram
        """
        if start is None:
            start = 0
        if end is None:
            end = self.signal.shape[0]
        if spectrogram_clip is None:
            spectrogram_clip = (10, 40)

        start = self.get_frame(start)
        end = self.get_frame(end)

        if end - start <= 0:
            raise AttributeError("The given end should be larger than the "
                                 "start.")

        spec = np.array(
            madmom.audio.LogarithmicFilteredSpectrogram(
                self.signal[start:end][:]
            )
        )[:, spectrogram_clip[0]:spectrogram_clip[1]]

        return (self.frame_times[start], self.frame_times[end]), spec
