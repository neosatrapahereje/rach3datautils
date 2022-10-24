import re
import os
import glob
from collections import defaultdict
import subprocess
import cv2
import sys
import numpy as np
from fractions import Fraction

from sys import platform

vpat = re.compile(
    "(.*)_([0-9]{4})-([0-9]{2})-([0-9]{2})_w_([0-9]{2})_([a-z]+)_*p*([0-9]*)_*v*([0-9]*).mp4"
)


class StreamInfo(object):
    def __init__(
        self,
        index,
        codec_name,
        codec_long_name,
        codec_type,
        *args,
        **kwargs,
    ):
        self.index = index
        self.codec_name = codec_name
        self.codec_long_name = codec_long_name
        self.codec_type = codec_type

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

        self.args = args


class VideoInfo(object):
    def __init__(
        self,
        video_streams=None,
        audio_streams=None,
        data_streams=None,
        duration=None,
    ):
        self.video_streams = video_streams or []
        self.audio_streams = audio_streams or []
        self.data_streams = data_streams or []
        self.duration = duration

    @property
    def width(self):
        width = np.array([s.width for s in self.video_streams])
        if not all(width == width[0]):
            raise ValueError("Streams with different widths")
        return width[0]

    @property
    def height(self):
        height = np.array([s.height for s in self.video_streams])
        if not all(height == height[0]):
            raise ValueError("Streams with different heights")
        return height[0]

    @property
    def frame_rate(self):
        fr = np.array([float(s.avg_frame_rate) for s in self.video_streams])
        return fr.mean()


def parse_codec_kwargs(kwargs):
    def _parse_kwarg(kwarg):
        try:
            name, val_ = kwarg.split("=")
        except:
            # Hack kwargs with a different format...
            # So far it only happens with
            # "TAG:handler_name=\nGoPro TCD" for GoPro videos
            return kwarg, kwargs

        try:
            val = float(val_)
            if val % 1 == 0:
                val = int(val_)

        except ValueError:
            try:
                num, den = val_.split("/")
                val = Fraction(int(num), int(den))
            except:
                val = str(val_)
        return name, val

    disposition = dict()
    parsed_kwargs = dict()
    tags = dict()
    for kwarg in kwargs:
        if kwarg.startswith("DISPOSITION:"):
            pass
            # name, val = _parse_kwarg(kwarg[12:])
            # disposition[name] = val
        elif kwarg.startswith("TAG:"):
            pass
            # name, val = _parse_kwarg(kwarg[4:])
            # tags[name] = val
        else:
            name, val = _parse_kwarg(kwarg)
            parsed_kwargs[name] = val
    # parsed_kwargs['disposition'] = disposition
    # parsed_kwargs['tags'] = tags
    return parsed_kwargs


def get_frame_rate(filename):
    if not os.path.exists(filename):
        sys.stderr.write("ERROR: filename {0} was not found!".format(filename))
        return -1
    out = subprocess.check_output(
        [
            "ffprobe",
            filename,
            "-v",
            "0",
            "-select_streams",
            "v",
            "-print_format",
            "flat",
            "-show_entries",
            "stream=r_frame_rate",
        ]
    ).decode("utf-8")
    rate = out.split("=")[1].strip()[1:-1].split("/")
    if len(rate) == 1:
        return float(rate[0])
    if len(rate) == 2:
        return float(rate[0]) / float(rate[1])
    return -1


def get_video_duration(filename):

    out = subprocess.check_output(
        [
            "ffprobe",
            "-i",
            filename,
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-hide_banner",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
        ]
    )

    return float(out)


def get_video_info(filename):

    if not os.path.exists(filename):
        raise ValueError("{0} was not found!".format(filename))

    out = (
        subprocess.check_output(["ffprobe", "-show_streams", "-i", filename])
        .decode("utf-8")
        .splitlines()
    )
    stream_dict = defaultdict(list)

    stream_idx = -1
    for l in out:
        # start of the stream
        if l == "[STREAM]":
            stream_idx += 1
        elif l == "[/STREAM]":
            pass
        else:
            stream_dict[stream_idx].append(l)

    video_streams = []
    audio_streams = []
    data_streams = []
    for s in stream_dict:
        try:
            stream = StreamInfo(**parse_codec_kwargs(stream_dict[s]))
        except:
            import pdb

            pdb.set_trace()

        if stream.codec_type == "video":
            video_streams.append(stream)
        elif stream.codec_type == "audio":
            audio_streams.append(stream)
        else:
            data_streams.append(stream)

    duration = get_video_duration(filename)

    return VideoInfo(
        video_streams=video_streams,
        audio_streams=audio_streams,
        data_streams=data_streams,
        duration=duration,
    )
