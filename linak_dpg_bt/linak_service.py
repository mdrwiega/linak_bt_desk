#
#
#


from enum import Enum, EnumMeta, unique



class ServiceEnumMeta(EnumMeta):
    @classmethod
    def __call__(cls, value, *args, **kw):
        strval = str(value).upper()
        return EnumMeta.__call__(cls, strval, *args, **kw)
    

@unique
class Service(Enum):
    
    ## contains tow accessors: 'name' and 'value'
    
    GENERIC_ACCESS      = "00001800-0000-1000-8000-00805F9B34FB"
    REFERENCE_INPUT     = "99FA0030-338A-1024-8A49-009C0215F78A"
    REFERENCE_OUTPUT    = "99FA0020-338A-1024-8A49-009C0215F78A"
    DPG                 = "99FA0010-338A-1024-8A49-009C0215F78A"
    CONTROL             = "99FA0001-338A-1024-8A49-009C0215F78A"

#     GENERIC_ATTRIBUTE   = "00001801-0000-1000-8000-00805F9B34FB"
#     DEVICE_INFORMATION  = "0000180A-0000-1000-8000-00805F9B34FB"

    
    def uuid(self):
        return self.value

    def __str__(self):
        return "%s.%s[%s]" % (self.__class__.__name__, self.name, self.value ) 

    @classmethod
    def find(cls, value):
        strval = str(value).upper()
        for item in Service:
            if item.uuid() == strval:
                return item
        return None


class CharacteristicEnumMeta(EnumMeta):
    @classmethod
    def __call__(cls, value, *args, **kw):
        if isinstance(value, str):
            found = cls.findByUUID(value)
            if found != None:
                return found
        if isinstance(value, int):
            found = cls.findByHandle(value)
            if found != None:
                return found
        return EnumMeta.__call__(cls, value, *args, **kw)


        

@unique
class Characteristic(Enum):
    
    ## contains two accessors: 'name' and 'value'
    
    ## generic access
    DEVICE_NAME  = ("00002A00-0000-1000-8000-00805F9B34FB", 0x03)
    MANUFACTURER = ("00002A29-0000-1000-8000-00805F9B34FB", 0x18)
    MODEL_NUMBER = ("00002A24-0000-1000-8000-00805F9B34FB", 0x1A)
    
    ## reference input
    CTRL1 = ("99FA0031-338A-1024-8A49-009C0215F78A", 0x3A)      # move to
#     CTRL2 = ("99FA0032-338A-1024-8A49-009C0215F78A"
#     CTRL3 = ("99FA0033-338A-1024-8A49-009C0215F78A"
#     CTRL4 = ("99FA0034-338A-1024-8A49-009C0215F78A"

    ## reference output
    HEIGHT_SPEED = ("99FA0021-338A-1024-8A49-009C0215F78A", 0x1D)            ## ONE
    TWO          = ("99FA0022-338A-1024-8A49-009C0215F78A", 0x20)
    THREE        = ("99FA0023-338A-1024-8A49-009C0215F78A", 0x23)
    FOUR         = ("99FA0024-338A-1024-8A49-009C0215F78A", 0x26)
    FIVE         = ("99FA0025-338A-1024-8A49-009C0215F78A", 0x29)
    SIX          = ("99FA0026-338A-1024-8A49-009C0215F78A", 0x2C)
    SEVEN        = ("99FA0027-338A-1024-8A49-009C0215F78A", 0x2F)
    EIGHT        = ("99FA0028-338A-1024-8A49-009C0215F78A", 0x32)
    MASK         = ("99FA0029-338A-1024-8A49-009C0215F78A", 0x35)
#             DETECT_MASK(UUID.fromString("99FA002A-338A-1024-8A49-009C0215F78A"));

    DPG         = ("99FA0011-338A-1024-8A49-009C0215F78A", 0x14)
    
    CONTROL     = ("99FA0002-338A-1024-8A49-009C0215F78A", 0x0E)
    ERROR       = ("99FA0003-338A-1024-8A49-009C0215F78A", 0x10)


    def __init__(self, uuid, handle):
        self._uuid = uuid
        self._handle = handle

    def uuid(self):
        return self._uuid
     
    def handle(self):
        return self._handle


    def __str__(self):
        return "%s.%s[%s, %s]" % (self.__class__.__name__, self.name, self.uuid(), hex(self.handle()) )


    @classmethod
    def find(cls, value):
        if isinstance(value, str):
            found = cls.findByUUID(value)
            if found != None:
                return found
        if isinstance(value, int):
            found = cls.findByHandle(value)
            if found != None:
                return found
        return None
        
    @classmethod
    def findByUUID(cls, uuid):
        strval = str(uuid).upper()
        for item in Characteristic:
            if item.uuid() == strval:
                return item
        return None
    
    @classmethod
    def findByHandle(cls, handle):
        for item in Characteristic:
            if item.handle() == handle:
                return item
        return None

    @classmethod
    def printCharacteristic(cls, characteristic):
        val = "-rns-"
        if characteristic.supportsRead():
#             val = characteristic.read().decode("utf-8") 
            val = characteristic.read() 
        return "Char: %s[%s] %s %s %s" % (
                    characteristic.uuid, 
                    characteristic.uuid.getCommonName(), 
                    hex(characteristic.getHandle()), 
                    characteristic.propertiesToString(),
                    val
                )
 

