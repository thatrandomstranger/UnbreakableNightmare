from typing import Callable, Union

from formats.binary import BinaryReader, BinaryWriter
from formats.sound.sample_transform import change_sample_rate, change_channels
from formats.sound.sadl import SADL
import numpy as np
import os


class WaveFormat:
    EMPTY = 0
    WAVE_FORMAT_PCM = 0x0001
    IBM_FORMAT_ADPCM = 0x0002
    IBM_FORMAT_MULAW = 0x0007
    IBM_FORMAT_ALAW = 0x0006
    WAVE_FORMAT_EXTENSIBLE = 0xFFFE


class FmtChunk:
    chunk_size: int
    audio_format: int
    num_channels: int
    sample_rate: int
    byte_rate: int
    block_align: int
    bits_per_sample: int

    def read(self, rdr: BinaryReader):
        assert rdr.read(4) == b"fmt "
        assert rdr.read_uint32() == 0x10
        self.audio_format = rdr.read_uint16()
        self.num_channels = rdr.read_uint16()
        self.sample_rate = rdr.read_uint32()
        self.byte_rate = rdr.read_uint32()
        self.block_align = rdr.read_uint16()
        self.bits_per_sample = rdr.read_uint16()

    def write(self, wtr: BinaryWriter):
        wtr.write(b"fmt ")
        wtr.write_uint32(0x10)
        wtr.write_uint16(WaveFormat.WAVE_FORMAT_PCM)
        wtr.write_uint16(self.num_channels)
        wtr.write_uint32(self.sample_rate)
        self.byte_rate = self.sample_rate * self.bits_per_sample * self.num_channels // 8
        wtr.write_uint32(self.byte_rate)
        self.block_align = self.num_channels * self.bits_per_sample // 8
        wtr.write_uint16(self.block_align)
        wtr.write_uint16(self.bits_per_sample)


class DataChunk:
    chunk_size: int
    data: np.ndarray

    def read(self, rdr: BinaryReader, fmt_chunk: FmtChunk):
        assert rdr.read(4) == b"data"
        self.chunk_size = rdr.read_uint32()

        if fmt_chunk.bits_per_sample == 0x10:
            data = np.frombuffer(rdr.read(self.chunk_size), dtype="<h")
        elif fmt_chunk.bits_per_sample == 0x08:
            data = np.frombuffer(rdr.read(self.chunk_size), dtype="<b")
        else:
            raise NotImplementedError()
        data = data.reshape((-1, fmt_chunk.num_channels))
        self.data = data.swapaxes(0, 1)

    def change_sample_rate(self, target_rate, fmt_chunk: FmtChunk):
        self.data = change_sample_rate(self.data, fmt_chunk.sample_rate,
                                       target_rate)
        fmt_chunk.sample_rate = target_rate

    def change_channels(self, target_channels, fmt_chunk: FmtChunk):
        self.data = change_channels(self.data, target_channels)
        fmt_chunk.num_channels = target_channels

    def get_sample_bytes(self, fmt_chunk: FmtChunk):
        size = self.data.shape[0] * self.data.shape[1] * fmt_chunk.bits_per_sample // 8
        return size

    def write(self, wtr: BinaryWriter, fmt_chunk: FmtChunk):
        wtr.write(b"data")
        wtr.write_uint32(self.get_sample_bytes(fmt_chunk))
        wtr.write(self.data.swapaxes(0, 1).tobytes())


class WAV:
    file_id: int
    chunk_size: int
    fmt: FmtChunk
    data: DataChunk
    loop_flag: int
    loop_offset: int

    def __init__(self):
        self.fmt = FmtChunk()
        self.data = DataChunk()

    def read_stream(self, rdr):
        if not isinstance(rdr, BinaryReader):
            rdr = BinaryReader(rdr)

        assert rdr.read(4) == b"RIFF"
        self.chunk_size = rdr.read_uint32()
        assert rdr.read(4) == b"WAVE"

        self.fmt.read(rdr)

        if self.fmt.audio_format != WaveFormat.WAVE_FORMAT_PCM or self.fmt.bits_per_sample == 0x08:
            raise NotImplementedError()

        rdr.seek(0x24)

        data_id = rdr.read(4)
        while data_id != b"data":
            offset = rdr.read_uint32()
            rdr.seek(rdr.tell() + offset)
            data_id = rdr.read(4)
        rdr.seek(-4, os.SEEK_CUR)

        self.data.read(rdr, self.fmt)

    @classmethod
    def from_sadl(cls, sadl: SADL, progress_callback: Union[Callable, None] = None):
        wav_obj = cls()
        wav_obj.fmt.num_channels = sadl.channels
        wav_obj.fmt.sample_rate = sadl.sample_rate
        wav_obj.fmt.bits_per_sample = 0x10
        sadl.reset_decoding()
        wav_obj.data.data = sadl.decode(progress_callback=progress_callback)
        return wav_obj, wav_obj.data.data is not None

    def to_sadl(self, sadl: SADL, progress_callback: Union[Callable, None] = None):
        # TODO: Change to generate SADL (needed?)
        sadl.channels = min(self.fmt.num_channels, 2)
        sadl.sample_rate = self.fmt.sample_rate
        if sadl.sample_rate <= 16364:
            sadl.sample_rate = 16364
        else:
            sadl.sample_rate = 32728
        data = self.data.data
        if self.fmt.num_channels != sadl.channels:
            data = change_channels(data, sadl.channels)
        if self.fmt.sample_rate != sadl.sample_rate:
            data = change_sample_rate(data, self.fmt.sample_rate, sadl.sample_rate)
        return sadl.encode(data, progress_callback)

    def change_sample_rate(self, target_rate):
        if self.fmt.sample_rate == target_rate:
            return

        self.data.change_sample_rate(target_rate, self.fmt)

    def change_channels(self, target_channels):
        if self.fmt.num_channels == target_channels:
            return

        self.data.change_channels(target_channels, self.fmt)

    def write_stream(self, stream):
        if not isinstance(stream, BinaryWriter):
            wtr = BinaryWriter(stream)
        else:
            wtr = stream
        wtr.write(b"RIFF")
        self.chunk_size = 0x28 + self.data.get_sample_bytes(self.fmt)
        wtr.write_uint32(self.chunk_size)

        wtr.write(b"WAVE")
        self.fmt.write(wtr)
        self.data.write(wtr, self.fmt)
