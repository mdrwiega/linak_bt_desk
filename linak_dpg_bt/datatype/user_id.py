#
#
#


class UserId:
    
    def __init__(self, data):
        self.version = data[2:]
        self.type = "Guest"
        if data[2] == 1:
            self.type = "Owner"
        self.id = data[2:]
        
    def __str__(self):
        return "%s[%s %s]" % (self.__class__.__name__, self.type, ''.join("{:}".format(x) for x in self.id))
    