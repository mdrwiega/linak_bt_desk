#
#
#

import struct

from .desk_position import DeskPosition


class FavoritePosition:
    
    def __init__(self, data):
        if data[2] != 1:
            ## not set
            self.position = None
            self.opCounter = struct.unpack('<I', data[3:])[0]
        else:
            self.position = DeskPosition.create(data)
            self.opCounter = struct.unpack('<I', data[5:])[0]
        
    def isValid(self):
        return (self.position != None)
    
    def disable(self):
        self.position = None
    
    def getPosition(self):
        return self.position
    
    def counter(self):
        return self.opCounter
    
    @property
    def raw(self):
        return self.position.raw
    
    def getCm(self):
        self.position.cm
    
    def setCm(self, position):
        self.position = DeskPosition.from_cm(position)
        
    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, self.position)
    