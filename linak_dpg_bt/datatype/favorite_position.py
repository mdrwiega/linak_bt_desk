#
#
#

from .desk_position import DeskPosition


class FavoritePosition:
    
    def __init__(self, data):
        self.position = DeskPosition.create(data)
        
    def isValid(self):
        return (self.position != None)
    
    def disable(self):
        self.position = None
    
    def getPosition(self):
        return self.position
    
    @property
    def raw(self):
        return self.position.raw
    
    def getCm(self):
        self.position.cm
    
    def setCm(self, position):
        self.position = DeskPosition.from_cm(position)
        
    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, self.position)
    