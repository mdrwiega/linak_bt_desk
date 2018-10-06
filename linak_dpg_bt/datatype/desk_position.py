#
#
#

import struct
import math


class DeskPosition:

    def __init__(self, raw):
        self._raw = raw

    @property
    def raw(self):
        return self._raw

    @property
    def cm(self):
        if self.raw == None:
            return None
        return round(self.raw / 100.0)
#         return math.ceil(self.raw / 100.0)

    @property
    def human_cm(self):
        if self.cm == None:
            return None
        return "%d cm" % self.cm
    
    def bytes(self):
        return self.bytes_from_raw( self.raw )
    
    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, self.raw)
    
    
    ## ======================================================


    @classmethod
    def create(cls, data):
        if data[2] != 1:
            ## not set
            return None
        return cls.from_bytes(data[3:])
    
    @classmethod
    def from_bytes(cls, data):
        offset = struct.unpack('<H', data[0:2])[0]
        return cls( offset )

    @classmethod
    def raw_from_cm(cls, cm):
        return math.ceil(cm * 100.0)

    @classmethod
    def bytes_from_raw(cls, raw):
        return struct.pack('<H', raw)

    @classmethod
    def from_cm(cls, cm):
        raw = cls.raw_from_cm(cm)
        return cls(raw)
    