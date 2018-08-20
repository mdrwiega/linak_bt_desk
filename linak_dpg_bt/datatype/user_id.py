#
#
#


class UserId:
    
    def __init__(self, data):
        self.type = "Guest"
        if data[2] == 1:
            self.type = "Owner"
        self.id = data[3:]
        ##self.id = "".join(map(chr, data[3:]))
        
    def __str__(self):
        return "%s[%s %s]" % (self.__class__.__name__, self.type, ' '.join("{:}".format(x) for x in self.id))
    