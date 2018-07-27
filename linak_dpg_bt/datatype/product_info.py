#
#
#


class ProductInfo:
    
    def __init__(self, data):
        self.version = data[2:]
        
    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, ' '.join("{:}".format(x) for x in self.version))
    