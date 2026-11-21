"""Bit-level reader and writer for Halo: Reach variant streams.

Reach packs its variant data most-significant bit first: the first value
written lands in the top bits of the first byte.
"""


class BitReader:
    def __init__(self, data):
        self._value = int.from_bytes(data, "big")
        self._total = len(data) * 8
        self.pos = 0

    @property
    def remaining(self):
        return self._total - self.pos

    def read(self, count):
        """The next `count` bits as an unsigned integer."""
        if count < 0:
            raise ValueError("negative bit count")
        end = self.pos + count
        if end > self._total:
            raise EOFError("read past the end of the stream (bit %d of %d)" % (end, self._total))
        value = (self._value >> (self._total - end)) & ((1 << count) - 1)
        self.pos = end
        return value

    def read_bool(self):
        return bool(self.read(1))

    def read_bytes(self, count):
        return self.read(count * 8).to_bytes(count, "big")


class BitWriter:
    def __init__(self):
        self._value = 0
        self.pos = 0

    def write(self, value, count):
        """Append `value` as `count` bits."""
        if count < 0:
            raise ValueError("negative bit count")
        value = int(value)
        if value < 0 or value >> count:
            raise ValueError("value %d does not fit in %d bits" % (value, count))
        self._value = (self._value << count) | value
        self.pos += count

    def write_bool(self, value):
        self.write(1 if value else 0, 1)

    def write_bytes(self, data):
        self.write(int.from_bytes(data, "big"), len(data) * 8)

    def to_bytes(self):
        """The stream so far, zero-padded to a whole byte."""
        pad = -self.pos % 8
        return (self._value << pad).to_bytes((self.pos + pad) // 8, "big")
