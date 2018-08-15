#
#
#

from bluepy import btle

from enum import Enum, EnumMeta, unique



class StringEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kw):
        strval = str(value).upper()
        return EnumMeta.__call__(cls, strval, *args, **kw)
    

@unique
class Service(Enum, metaclass=StringEnumMeta):
    ## works for Python 2
    __metaclass__ = StringEnumMeta
    
    ## contains tow accessors: 'name' and 'value'
    
    GENERIC_ACCESS      = "00001800-0000-1000-8000-00805F9B34FB"
    REFERENCE_INPUT     = "99FA0030-338A-1024-8A49-009C0215F78A"
    REFERENCE_OUTPUT    = "99FA0020-338A-1024-8A49-009C0215F78A"
    DPG                 = "99FA0010-338A-1024-8A49-009C0215F78A"
    CONTROL             = "99FA0001-338A-1024-8A49-009C0215F78A"


    def __str__(self):
        return "%s.%s[%s]" % (self.__class__.__name__, self.name, self.value ) 


@unique
class Characteristic(Enum, metaclass=StringEnumMeta):
    ## works for Python 2
    __metaclass__ = StringEnumMeta
    
    ## contains tow accessors: 'name' and 'value'
    
    DEVICE_NAME = "00002A00-0000-1000-8000-00805F9B34FB"
#     ONE(UUID.fromString("99FA0031-338A-1024-8A49-009C0215F78A")),
#     TWO(UUID.fromString("99FA0032-338A-1024-8A49-009C0215F78A")),
#     THREE(UUID.fromString("99FA0033-338A-1024-8A49-009C0215F78A")),
#     FOUR(UUID.fromString("99FA0034-338A-1024-8A49-009C0215F78A"));

    HEIGHT_SPEED = "99FA0021-338A-1024-8A49-009C0215F78A"            ## ONE
    MASK         = "99FA0029-338A-1024-8A49-009C0215F78A"
    
#             TWO(UUID.fromString("99FA0022-338A-1024-8A49-009C0215F78A")),
#             THREE(UUID.fromString("99FA0023-338A-1024-8A49-009C0215F78A")),
#             FOUR(UUID.fromString("99FA0024-338A-1024-8A49-009C0215F78A")),
#             FIVE(UUID.fromString("99FA0025-338A-1024-8A49-009C0215F78A")),
#             SIX(UUID.fromString("99FA0026-338A-1024-8A49-009C0215F78A")),
#             SEVEN(UUID.fromString("99FA0027-338A-1024-8A49-009C0215F78A")),
#             EIGHT(UUID.fromString("99FA0028-338A-1024-8A49-009C0215F78A")),
#             DETECT_MASK(UUID.fromString("99FA002A-338A-1024-8A49-009C0215F78A"));

    DPG         = "99FA0011-338A-1024-8A49-009C0215F78A"
    
    COMMAND     = "99FA0002-338A-1024-8A49-009C0215F78A"
    ERROR       = "99FA0003-338A-1024-8A49-009C0215F78A"


    def __str__(self):
        return "%s.%s[%s]" % (self.__class__.__name__, self.name, self.value ) 

