#
#
#

import struct
import math


class DeskPosition:
    
    @classmethod
    def create(cls, data):
        if data[2] != 1:
            ## not set
            return None
        return cls.from_bytes(data[3:])
    
    @classmethod
    def from_bytes(cls, data):
        return cls(struct.unpack('<H', data[0:2])[0])

    @classmethod
    def raw_from_cm(cls, cm):
        return math.ceil(cm * 100.0)

    @classmethod
    def bytes_from_raw(cls, raw):
        return struct.pack('<H', raw)

    @classmethod
    def from_cm(cls, cm):
        return cls(cls.raw_from_cm(cm))

    def __init__(self, raw):
        self._raw = raw

    @property
    def raw(self):
        return self._raw

    @property
    def cm(self):
        if self.raw == None:
            return None
        return math.ceil(self.raw / 100.0)

    @property
    def human_cm(self):
        if self.cm == None:
            return None
        return "%d cm" % self.cm
    
    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, self.human_cm)
    
