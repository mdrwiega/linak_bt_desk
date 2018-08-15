#
#
#

from .desk_position import *


class FavoritePosition:
    
    def __init__(self, data):
        self.position = DeskPosition.create(data)
        
    @property
    def raw(self):
        return self.position.raw
        
    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, self.position)
    