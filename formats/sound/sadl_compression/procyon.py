import numpy as np


def clamp_unsigned(value, bytes_):
    size = 8*bytes_
    return ((value + (1 << size)) % (2 << size)) - (1 << size)


class Procyon:
    PROC_COEF = [[0, 0],
                 [0x3c, 0],
                 [115, -52],
                 [98, -55],
                 [122, -60]]

    def __init__(self):
        self.hist = [0, 0]

    def reset(self):
        self.hist = [0, 0]

    def clamp_hist(self):
        self.hist[0] = clamp_unsigned(self.hist[0], 4)
        self.hist[1] = clamp_unsigned(self.hist[1], 4)

    def decode_sample(self, sample, coef1, coef2, scale):
        error = sample
        error <<= (6 + scale)

        pred = (self.hist[0] * coef1 + self.hist[1] * coef2 + 32) >> 6

        sample = pred + error

        self.hist[1] = self.hist[0]
        self.hist[0] = sample
        self.clamp_hist()

        clamp = (sample + 32) >> 6
        if clamp > 32767:
            clamp = 32767
        if clamp < -32768:
            clamp = -32768
        clamp = clamp >> 6 << 6

        return clamp

    def encode_sample(self, sample, coef1, coef2, scale):
        value = sample << 6
        pred = (self.hist[0]*coef1 + self.hist[1]*coef2 + 32) >> 6
        error = value - pred
        error_scaled = error >> (scale + 6)

        result = error_scaled & 0xF
        result = (result + 8) % 16 - 8

        error_approx = result
        error_approx <<= (scale + 6)

        self.hist[1] = self.hist[0]
        self.hist[0] = pred + error_approx
        self.clamp_hist()

        sample_approx = pred + error_approx

        clamp = (sample_approx + 32) >> 6
        if clamp > 32767:
            clamp = 32767
        if clamp < -32768:
            clamp = -32768
        clamp = clamp >> 6 << 6

        diff = abs(sample - clamp)
        return result, diff

    def decode_block(self, block: np.ndarray) -> np.ndarray:
        buffer = np.zeros(shape=(30,), dtype=np.int32)

        header = block[0xF] ^ 0x80
        scale = header & 0xf
        coef_index = header >> 4

        coef1 = Procyon.PROC_COEF[coef_index][0]
        coef2 = Procyon.PROC_COEF[coef_index][1]

        for i in range(30):
            sample_byte = block[int(i // 2)] ^ 0x80

            if i & 1 == 1:
                sample = (sample_byte & 0xf0) >> 4
            else:
                sample = sample_byte & 0x0f
            sample = ((sample + 8) % 16) - 8
            buffer[i] = self.decode_sample(sample, coef1, coef2, scale)

        return buffer

    def encode_block(self, block: np.ndarray) -> np.ndarray:
        # TODO: Encoding improve performance (currently it's brute force)
        if len(block) < 30:
            block = np.append(block, [0]*(30 - len(block)))
        best_encoded, scale, coef_index = self.search_best_encode(block)

        result = np.ndarray((16,), dtype=np.uint8)
        current_value = 0
        for i, sample in enumerate(best_encoded):
            sample = (sample + 16) % 16  # Make positive
            if i % 2 == 0:  # low nibble
                current_value = sample
            else:  # high nibble
                current_value |= sample << 4
                result[i//2] = current_value ^ 0x80
        header = (coef_index << 4) | scale
        current_value = header
        result[-1] = current_value ^ 0x80
        return result

    def search_best_encode(self, block: np.ndarray):
        coef_index = 0
        scale = 0

        current_hist = [0, 0]
        current_hist[0] = self.hist[0]
        current_hist[1] = self.hist[1]
        new_hist = [0, 0]

        num_coef = 5
        num_scales = 12

        best_encoded = None
        min_difference = -1
        for temp_coef in range(num_coef):
            for temp_scale in range(num_scales):
                self.hist[0] = current_hist[0]
                self.hist[1] = current_hist[1]
                encoded, difference = self.get_encoding_difference(block, temp_coef, temp_scale, min_difference)

                if difference < min_difference or best_encoded is None:
                    min_difference = difference
                    best_encoded = encoded
                    coef_index = temp_coef
                    scale = temp_scale
                    new_hist[0] = self.hist[0]
                    new_hist[1] = self.hist[1]
                    if difference == 0:
                        return best_encoded, scale, coef_index
        self.hist = new_hist
        return best_encoded, scale, coef_index

    def get_encoding_difference(self, block: np.ndarray, coef_index, scale, min_difference):
        coef1 = self.PROC_COEF[coef_index][0]
        coef2 = self.PROC_COEF[coef_index][1]

        result = [0]*len(block)

        total_difference = 0

        for i, sample in enumerate(block):
            r, diff = self.encode_sample(sample, coef1, coef2, scale)
            result[i] = r
            total_difference += diff
            if total_difference > min_difference >= 0:
                # if we already know that this can't possibly be the best combination, we return
                return result, total_difference

        return result, total_difference
