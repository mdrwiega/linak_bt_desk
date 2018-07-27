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
    
    def __str__(self):
        return "%s[%s %s %s %s %s %s, %s %s %s]" % (self.__class__.__name__,
                                                    self.reminder, self.cmEnabled, self.impulseUp, self.impulseDown, self.wake, self.guide, 
                                                    self.r1, self.r2, self.r3,
                                                )
    
    
class Reminder:
    
    def __init__(self, data):
        self.sit = data[0]
        self.stand = data[1]
    
    def __str__(self):
        return "%s[%s %s]" % (self.__class__.__name__, 
                                 self.sit, self.stand
                                 )
    