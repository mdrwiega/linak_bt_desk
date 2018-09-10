#
#
#


class ReminderSetting:
    
    def __init__(self, data):
        settings = data[2:]
        settingsByte = settings[0]
        
        self.reminder = settingsByte & 3
        self.cmEnabled = (settingsByte & 4) == 0
        self.impulseUp = (settingsByte & 8) != 0
        self.impulseDown = (settingsByte & 16) != 0
        self.wake = (settingsByte & 32) != 0
        self.guide = (settingsByte & 64) != 0
        
        self.r1 = Reminder(settings[1:3])
        self.r2 = Reminder(settings[3:5])
        self.r3 = Reminder(settings[5:7])
    
    def info(self):
        retString = ""
        if self.reminder & 1:
            retString += self.r1.info()
        if self.reminder & 2:
            retString += self.r2.info()
        if self.reminder & 4:
            retString += self.r3.info()
                        
        if self.cmEnabled == True:
            retString += "CM"
        else:
            retString += "cm"
        if self.impulseUp == True:
            retString += " IU"
        else:
            retString += " iu"
        if self.impulseDown == True:
            retString += " ID"
        else:
            retString += " id"
        if self.wake == True:
            retString += " W"
        else:
            retString += " w"
        if self.guide == True:
            retString += " G"
        else:
            retString += " g"
        return retString
    
    def __str__(self):
        return "%s[%s %s %s %s %s %s, %s %s %s]" % (self.__class__.__name__,
                                                    self.reminder, self.cmEnabled, self.impulseUp, self.impulseDown, self.wake, self.guide, 
                                                    self.r1, self.r2, self.r3,
                                                )
    
    
class Reminder:
    
    def __init__(self, data):
        self.sit = data[0]
        self.stand = data[1]
    
    def info(self):
        retString = str(self.sit) + " / " + str(self.stand)
        return retString
    
    def __str__(self):
        return "%s[%s %s]" % (self.__class__.__name__, 
                                 self.sit, self.stand
                                 )
    