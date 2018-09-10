#
#
#


from enum import Enum, unique



@unique
class ActuatorType(Enum):
    Invalid = ()
    Desk = ()
    LegRest = ()
    BackRest = ()
    Unknown = ()
    
    def __new__(cls):
        value = len(cls.__members__)  # note no + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
    
    
class Mask:
    
    def __init__(self, data):
        self.maskByte = data[0]
        self.actuator = ActuatorType.Unknown
        if self.maskByte & 1:
            self.actuator = ActuatorType.Desk
        elif self.maskByte & 64:
            self.actuator = ActuatorType.LegRest
        elif self.maskByte & 128:
            self.actuator = ActuatorType.BackRest
        elif self.maskByte == 0:
            self.actuator = ActuatorType.Invalid
        else:
            self.actuator = ActuatorType.Unknown
        
    def __str__(self):
        return "%s[%s %s]" % (self.__class__.__name__, self.actuator, hex(self.maskByte))
    