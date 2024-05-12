import logging
import math
import multiprocessing
import time

from formats.binary import BinaryReader, BinaryWriter
from formats.sound.compression import adpcm, procyon
from formats.filesystem import FileFormat
import numpy as np
from typing import List, Callable, Union

from multiprocessing import shared_memory


# TODO: add loop support

def get_shared_memory(src_shape, src_name, src_type, dst_shape, dst_name, progress_shape, progress_type, progress_name):
    src_sh_m = shared_memory.SharedMemory(name=src_name)
    dst_sh_m = shared_memory.SharedMemory(name=dst_name)
    progress_sm = shared_memory.SharedMemory(name=progress_name)
    decoded = np.ndarray(src_shape, dtype=src_type, buffer=src_sh_m.buf)
    buffer = np.ndarray(dst_shape, dtype=np.uint8, buffer=dst_sh_m.buf)
    progress_buf = np.ndarray(progress_shape, dtype=progress_type, buffer=progress_sm.buf)
    return src_sh_m, dst_sh_m, progress_sm, decoded, buffer, progress_buf


def encode_channel_procyon(channel, num_samples, *buffer_data):
    src_sh_m, dst_sh_m, progress_sm, decoded, buffer, progress_buf = get_shared_memory(*buffer_data)
    buffer_off = 0
    procyon_decoder = procyon.Procyon()
    for i in range(0, num_samples, 30):
        block = decoded[channel][i:i + 30]
        destination = buffer[channel][buffer_off:buffer_off + 0x10]
        procyon_decoder.encode_block(block, destination)
        buffer_off += 0x10
        progress_buf[channel] = i
    src_sh_m.close()
    dst_sh_m.close()
    progress_sm.close()


def encode_channel_int_ima(channel, num_samples, *buffer_data):
    src_sh_m, dst_sh_m, progress_sm, decoded, buffer, progress_buf = get_shared_memory(*buffer_data)
    buffer_off = 0
    int_ima_encoder = adpcm.Adpcm(False)
    for i in range(0, num_samples, 30):
        block = decoded[channel][i:i + 30]
        destination = buffer[channel][buffer_off:buffer_off + 0xF]
        int_ima_encoder.compress(block, destination)
        buffer_off += 0xF
        progress_buf[channel] = i
    src_sh_m.close()
    dst_sh_m.close()
    progress_sm.close()


class Coding:
    EMPTY = 0
    INT_IMA = 0x70
    NDS_PROCYON = 0xB0


class SADL(FileFormat):
    chunk_id: bytes
    original_header: bytes
    file_name: bytes

    file_size: int
    loop_flag: int
    loop_offset: int
    channels: int
    coding: int
    sample_rate: int
    num_samples: int
    volume_maybe: int
    interleave_block_size: int = 0x10

    buffer: np.ndarray

    ima_decoders: List[adpcm.Adpcm]
    procyon_objects: List[procyon.Procyon]
    blocks_done: int
    offset: List[int]

    def read_stream(self, stream):
        if not isinstance(stream, BinaryReader):
            rdr = BinaryReader(stream)
        else:
            rdr = stream
        # TODO: Figure out unknowns so as to not need the original header.
        self.original_header = rdr.read(0x100)
        rdr.seek(0)

        self.chunk_id = rdr.read(4)
        if self.chunk_id != b"sadl":
            raise ValueError("SADL does not start with magic value")
        rdr.seek(0x20)
        self.file_name = rdr.read_string(0x10)
        rdr.seek(0x31)
        self.loop_flag = rdr.read_uint8()
        self.channels = rdr.read_uint8()

        coding = rdr.read_uint8()
        if coding & 0x06 == 4:
            self.sample_rate = 32728
        elif coding & 0x06 == 2:
            self.sample_rate = 16364
        else:
            raise ValueError(f"Unrecognised sample rate value: {coding & 0x06}")

        self.coding = coding & 0xf0
        if self.coding != Coding.INT_IMA and self.coding != Coding.NDS_PROCYON:
            raise ValueError(f"Unrecognised coding value: {self.coding}")

        rdr.seek(0x40)
        self.file_size = rdr.read_uint32()

        if self.coding == Coding.INT_IMA:
            self.num_samples = int((self.file_size - 0x100) / self.channels * 2)
        elif self.coding == Coding.NDS_PROCYON:
            self.num_samples = int((self.file_size - 0x100) / self.channels / 16 * 30)

        rdr.seek(0x54)
        if self.loop_flag != 0:  # TODO??
            loop_raw = rdr.read_uint32()
            if self.coding == Coding.INT_IMA:
                self.loop_offset = int((loop_raw - 0x100) / self.channels * 2)
            elif self.coding == Coding.NDS_PROCYON:
                self.loop_offset = int((loop_raw - 0x100) / self.channels / 16 * 30)

        rdr.seek(0x60)
        self.volume_maybe = rdr.read_uint8()

        rdr.seek(0x68)
        v = rdr.read(0x6C-0x68)
        print("0x68-0x6C:", " ".join(hex(n)[2:] for n in v), self.loop_flag)

        rdr.seek(0x100)
        buffer = rdr.read(self.file_size - 0x100)
        buffer = np.frombuffer(buffer, dtype=np.uint8)
        buffer = np.copy(buffer)  # needed for cython
        buffer = buffer.reshape((-1, self.channels, 0x10))
        buffer = buffer.swapaxes(0, 1)
        self.buffer = buffer.reshape((buffer.shape[0], buffer.shape[1] * buffer.shape[2]))
        self.reset_decoding()

    def reset_decoding(self):
        self.offset = [0] * self.channels
        self.ima_decoders = []
        self.procyon_objects = []
        for i in range(self.channels):
            self.ima_decoders.append(adpcm.Adpcm(False))
            self.procyon_objects.append(procyon.Procyon())
        self.blocks_done = 0

    def write_stream(self, stream):
        if not isinstance(stream, BinaryWriter):
            wtr = BinaryWriter(stream)
        else:
            wtr = stream

        wtr.write(self.original_header)
        wtr.seek(0)
        wtr.write(self.chunk_id)
        wtr.seek(0x20)
        wtr.write_string(self.file_name, 0x10)
        wtr.seek(0x31)
        wtr.write_uint8(self.loop_flag)
        wtr.write_uint8(self.channels)

        coding = self.coding
        if self.sample_rate == 32728:
            coding |= 4
        elif self.sample_rate == 16364:
            coding |= 2
        else:
            raise NotImplementedError()
        wtr.write_uint8(coding)

        wtr.seek(0x54)
        if self.loop_flag != 0:
            if self.coding == Coding.INT_IMA:
                loop_raw = (self.loop_offset * self.channels / 2) + 0x100
            else:
                loop_raw = (self.loop_offset * self.channels * 16 / 30) + 0x100
            wtr.write_uint32(int(loop_raw))

        wtr.seek(0x60)
        wtr.write_uint8(self.volume_maybe)

        wtr.seek(0x100)
        buffer = self.buffer.copy()
        buffer = buffer.reshape((buffer.shape[0], buffer.shape[1] // 0x10, 0x10))
        buffer = buffer.swapaxes(0, 1)
        wtr.write(buffer.tobytes())

        size = wtr.tell()
        wtr.seek(0x08)
        wtr.write_uint32(size)
        wtr.seek(0x40)
        wtr.write_uint32(size)

    def _decode_helper(self, blocks, decoded: np.ndarray, progress_callback: Union[Callable, None],
                       offset_step: int, decoder_function: Callable):
        cancelled = False
        for chan in range(self.channels):
            if cancelled:
                break
            decoded_pos = 0
            for i in range(blocks):
                if cancelled:
                    break
                if i + self.blocks_done >= self.num_samples // 30:
                    break
                if progress_callback:
                    if progress_callback(i + chan * blocks, blocks * self.channels):
                        cancelled = True
                block = self.buffer[chan][self.offset[chan]:self.offset[chan] + offset_step]
                decoder_function(chan, block, decoded[chan][decoded_pos:decoded_pos + 30])
                decoded_pos += 30
                self.offset[chan] += offset_step
        self.blocks_done += blocks
        return cancelled

    def _decode_int_ima(self, blocks, decoded: np.ndarray, progress_callback: Union[Callable, None]):
        def decoder_int_ima(chan, src, dest):
            result = self.ima_decoders[chan].decompress(src)
            dest[-result.shape[0]:] = result

        return self._decode_helper(blocks, decoded, progress_callback, 0xF, decoder_int_ima)

    def _decode_procyon(self, blocks, decoded: np.ndarray, progress_callback: Union[Callable, None]):
        def decoder_procyon(chan, src, dest):
            self.procyon_objects[chan].decode_block(src, dest)

        return self._decode_helper(blocks, decoded, progress_callback, 0x10, decoder_procyon)

    def decode(self, blocks=-1, progress_callback: Union[Callable, None] = None):
        # 1 block = 30 samples (because of Procyon)
        max_blocks = self.num_samples // 30 - self.blocks_done
        if blocks == -1:
            blocks = max_blocks
        blocks = min(max_blocks, blocks)
        decoded = np.zeros((self.channels, blocks * 30), dtype=np.int16)

        if self.coding == Coding.INT_IMA:
            cancelled = self._decode_int_ima(blocks, decoded, progress_callback)
        elif self.coding == Coding.NDS_PROCYON:
            cancelled = self._decode_procyon(blocks, decoded, progress_callback)
        else:
            raise NotImplementedError()
        if cancelled:
            return None
        return decoded

    def _encode_helper(self, decoded: np.ndarray, progress_callback: Union[Callable, None],
                       encode_function: Callable):
        src_sh_mem = shared_memory.SharedMemory(create=True, size=decoded.nbytes)
        decoded_sh = np.ndarray(decoded.shape, dtype=decoded.dtype, buffer=src_sh_mem.buf)
        decoded_sh[:] = decoded[:]
        dst_sh_mem = shared_memory.SharedMemory(create=True, size=self.buffer.nbytes)
        buffer_sh = np.ndarray(self.buffer.shape, dtype=self.buffer.dtype, buffer=dst_sh_mem.buf)
        buffer_sh[:] = self.buffer[:]
        progress_buffer = np.array([0] * self.channels)
        sm_progress = shared_memory.SharedMemory(create=True, size=progress_buffer.nbytes)
        sh_progress = np.ndarray(progress_buffer.shape, dtype=progress_buffer.dtype,
                                 buffer=sm_progress.buf)

        processes = []
        for i in range(self.channels):
            processes.append(multiprocessing.Process(target=encode_function,
                                                     args=(i, self.num_samples,
                                                           decoded.shape, src_sh_mem.name, decoded.dtype,
                                                           self.buffer.shape, dst_sh_mem.name,
                                                           sh_progress.shape, sh_progress.dtype,
                                                           sm_progress.name)))
            processes[i].start()

        while any(x.is_alive() for x in processes):
            progress = sum(sh_progress)
            if progress_callback:
                if progress_callback(progress, self.num_samples * self.channels):
                    for process in processes:
                        process.kill()
                    src_sh_mem.close()
                    dst_sh_mem.close()
                    sm_progress.close()
                    return False
            time.sleep(0.05)

        self.buffer[:] = buffer_sh[:]
        src_sh_mem.close()
        dst_sh_mem.close()
        sm_progress.close()
        return True

    def _encode_int_ima(self, decoded: np.ndarray, progress_callback: Union[Callable, None]):
        self.buffer = np.zeros((decoded.shape[0], int(math.ceil(self.num_samples / 0x20) * 0x10)), dtype=np.uint8)
        return self._encode_helper(decoded, progress_callback, encode_channel_int_ima)

    def _encode_procyon(self, decoded: np.ndarray, progress_callback: Union[Callable, None] = None):
        # Professor Layton 2 only supports Procyon encoding
        self.buffer = np.zeros((decoded.shape[0], int(math.ceil(self.num_samples / 30)) * 16), dtype=np.uint8)
        return self._encode_helper(decoded, progress_callback, encode_channel_procyon)

    def encode(self, decoded: np.ndarray, progress_callback: Union[Callable, None] = None):
        self.num_samples = decoded.shape[1]
        if self.coding == Coding.NDS_PROCYON:
            return self._encode_procyon(decoded, progress_callback)
        elif self.coding == Coding.INT_IMA:
            return self._encode_int_ima(decoded, progress_callback)
        else:
            raise NotImplementedError()
