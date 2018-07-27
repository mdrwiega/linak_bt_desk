#
#
#


class Capabilities:
    
    def __init__(self, data):
        caps = data[2:]
        self.valid = False
        if len(caps) < 2:
            return
        capByte = caps[0]
        
        self.refByte = caps[1]
        
        self.memSize = capByte & 7
        self.autoUp = (capByte & 8) != 0
        self.autoDown = (capByte & 16) != 0
        self.bleAllow = (capByte & 32) != 0
        self.hasDisplay = (capByte & 64) != 0
        self.hasLight = (capByte & 128) != 0
    
    def __str__(self):
        refString = self._refString()
        return "%s[%s %s %s %s %s %s refs: %s]" % (self.__class__.__name__, 
                                                   self.memSize, self.autoUp, self.autoDown, self.bleAllow, self.hasDisplay, self.hasLight,
                                                   refString 
#                                                    format(self.refByte, '#010b')
                                                   )
    
    def _refString(self):
        ret = ""
        mask = 1
        for i in range(8):
            if self.refByte & mask != 0:
                ret += (str(i+1) + " ")
            mask = mask << 1
        return ret
    