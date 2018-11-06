#
#
#


import struct



def to_bin_string(data):
    return " ".join( '0b{:08b}'.format(x) for x in data )

def to_bin_string7(data):
    return " ".join( '{:07b}'.format(x) for x in data )


class ReminderSetting:
    
    REMINDER_MASK     = 0b0000011   ##  3
    INCH_MASK         = 0b0000100   ##  4
    IMPULSE_UP_MASK   = 0b0001000   ##  8
    IMPULSE_DOWN_MASK = 0b0010000   ## 16
    WAKE_MASK         = 0b0100000   ## 32
    LIGHT_MASK        = 0b1000000   ## 64        ## bit is used only for activating the lights
    
    
    def __init__(self, data):
        settings = data[2:]
        flagsByte = settings[0]
        
        self.reminder    =  flagsByte & self.REMINDER_MASK
        self.inchEnabled = (flagsByte & self.INCH_MASK) != 0
        self.impulseUp   = (flagsByte & self.IMPULSE_UP_MASK) != 0
        self.impulseDown = (flagsByte & self.IMPULSE_DOWN_MASK) != 0
        self.wake        = (flagsByte & self.WAKE_MASK) != 0
        self.lightGuide  = (flagsByte & self.LIGHT_MASK) != 0
        
        self.r1 = Reminder(settings[1:3])
        self.r2 = Reminder(settings[3:5])
        self.r3 = Reminder(settings[5:7])
        
        self.opCounter = struct.unpack('<I', settings[7:11])[0]
    
    def info(self):
        retString = ""
        if self.reminder == 0:
            retString += "off"
        if self.reminder == 1:
            retString += self.r1.info()
        if self.reminder == 2:
            retString += self.r2.info()
        if self.reminder == 3:
            retString += self.r3.info()
                                                
        if self.lightGuide == True:
            retString += " L"
        else:
            retString += " l"
            
        if self.wake == True:
            retString += " W"
        else:
            retString += " w"
        
        if self.impulseDown == True:
            retString += " ID"
        else:
            retString += " id"
        
        if self.impulseUp == True:
            retString += " IU"
        else:
            retString += " iu"
            
        if self.inchEnabled == True:
            retString += " INCH"
        else:
            retString += " CM"
            
        return retString
    
    def state(self):
        flags =  self._getFlagsByte()
        return to_bin_string7( [flags] )
    
    def getReminderByIndex(self, number):
        if number == 1:
            return self.r1
        if number == 2:
            return self.r2
        if number == 3:
            return self.r3
        return None
    
    def currentReminder(self):
        if self.reminder == 1:
            return self.r1
        if self.reminder == 2:
            return self.r2
        if self.reminder == 3:
            return self.r3
        return None
    
    def currentReminderInfo(self):
        currReminder = self.currentReminder()
        if currReminder == None:
            return "None"
        else:
            return currReminder.info()
    
    def counter(self):
        return self.opCounter
    
    def raw_data(self):
        ret = []
        ret.append( self._getFlagsByte() )
        ret.append( self.r1.sit )
        ret.append( self.r1.stand )
        ret.append( self.r2.sit )
        ret.append( self.r2.stand )
        ret.append( self.r3.sit )
        ret.append( self.r3.stand )
        return bytearray( ret )
    
    def getReminders(self):
        retList = [] 
        retList.append( self.r1.data() )
        retList.append( self.r2.data() )
        retList.append( self.r3.data() )
        return retList
    
    def getRemindersList(self):
        retList = [] 
        retList.append( self.r1 )
        retList.append( self.r2 )
        retList.append( self.r3 )
        return retList        
    
    def getReminderIndex(self):
        return self.reminder
    
    def switchReminder(self, state):
        if state < 0:
            raise ValueError( "bad reminder number: %s, allowed in range [0, 3]" % ( state ) )
        if state > 3:
            raise ValueError( "bad reminder number: %s, allowed in range [0, 3]" % ( state ) )
        ## toggle
        if self.reminder == state:
            self.reminder = 0
        else:
            self.reminder = state
    
    def getCmUnit(self):
        return (self.inchEnabled == False)
    
    def setCmUnit(self, useCm):
        if useCm == True:
            self.inchEnabled = False
        else:
            self.inchEnabled = True
            
    def getAutomaticUp(self):
        return self.impulseUp
    
    def setAutomaticUp(self, state):
        if state == True:
            self.impulseUp = True
        else:
            self.impulseUp = False
            
    def getAutomaticDown(self):
        return self.impulseDown
    
    def setAutomaticDown(self, state):
        if state == True:
            self.impulseDown = True
        else:
            self.impulseDown = False
                
    def getWake(self):
        return self.wake
        
    def setWake(self, state):
        if state == True:
            self.wake = True
        else: 
            self.wake = False
            
    def getLights(self):
        return self.lightGuide
        
    def setLights(self, state):
        if state == True:
#             if self.reminder == 0:
#                 self.switchReminder(1)
            self.lightGuide = True
        else:
#             self.switchReminder(0) 
            self.lightGuide = False
    
    def _getFlagsByte(self):
        flags = self.reminder
        if self.inchEnabled == True:
            flags = flags | self.INCH_MASK
        if self.impulseUp == True:
            flags = flags | self.IMPULSE_UP_MASK
        if self.impulseDown == True:
            flags = flags | self.IMPULSE_DOWN_MASK
        if self.wake == True:
            flags = flags | self.WAKE_MASK
        if self.lightGuide == True:
            flags = flags | self.LIGHT_MASK
        return flags
    
    def __str__(self):
        flags =  self._getFlagsByte()
        return "%s[%s %s %s %s]" % (self.__class__.__name__,
                                                    to_bin_string( [flags] ),
                                                    self.r1, self.r2, self.r3,
                                                )
    
    @classmethod
    def create(cls, data):
        if len(data) < 8:
            return None
        return ReminderSetting(data)
    
    
    
class Reminder:
    
    def __init__(self, data):
        self.sit = data[0]
        self.stand = data[1]
    
    def info(self):
        retString = str(self.sit) + "/" + str(self.stand)
        return retString
    
    def data(self):
        return (self.sit, self.stand)
    
    def __str__(self):
        return "%s[%s %s]" % (self.__class__.__name__, 
                                 self.sit, self.stand
                                 )
    