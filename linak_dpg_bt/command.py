#
#
#

import struct
import logging

from enum import Enum, unique

import linak_dpg_bt.linak_service as linak_service


_LOGGER = logging.getLogger(__name__)


@unique
class DPGCommandType(Enum):
    ## contains tow accessors: 'name' and 'value'
     
    PRODUCT_INFO = 8
    GET_SETUP = 10            ## does not work
#     CURRENT_TIME(22),
    GET_CAPABILITIES = 128
    DESK_OFFSET = 129           ## 0x81
#     GET_OEM_ID(TransportMediator.KEYCODE_MEDIA_RECORD),
#     GET_OEM_NAME(131),
#     GET_SET_COMPANY_ID(132),
#     GET_SET_COMPANY_NAME(133),
    USER_ID = 134               ## 0x86
#     GET_SET_REMINDER_TIME(135),
    REMINDER_SETTING = 136
    GET_SET_MEMORY_POSITION_1 = 137
    GET_SET_MEMORY_POSITION_2 = 138
    GET_SET_MEMORY_POSITION_3 = 139
    GET_SET_MEMORY_POSITION_4 = 140
#     READ_WRITE_REFERENCE_SPEED_1(216),
#     READ_WRITE_REFERENCE_SPEED_2(217),
#     READ_WRITE_REFERENCE_SPEED_3(218),
#     READ_WRITE_REFERENCE_SPEED_4(219),
#     READ_WRITE_REFERENCE_SPEED_5(220),
#     READ_WRITE_REFERENCE_SPEED_6(221),
#     READ_WRITE_REFERENCE_SPEED_7(222),
#     READ_WRITE_REFERENCE_SPEED_8(223),
#     GET_MASSAGE_PARAMETERS(244),
#     GET_SET_MASSAGE_VALUES(245),
    GET_LOG_ENTRY = 144
    

    @classmethod
    def findType(cls, value):
        for item in DPGCommandType:
            if item.value == value:
                return item
        return None



class DPGCommand():    
    
    @classmethod
    def get_read_command(cls, commandType):
        return DPGCommand(commandType)
    
    @classmethod
    def get_write_command(cls, commandType, data):
        return DPGCommand(commandType, data)
    
    @classmethod
    def is_valid_response(cls, data):
        if data[0] != 0x1:
#             raise DPGCommandReadError('DPG_Control packets needs to have 0x01 in first byte.')
            _LOGGER.debug('Error: DPG_Control packets needs to have 0x01 in first byte.')
            return False
        if data[1] < 0x1:
            _LOGGER.debug("These are not the data you're looking for - move along")
            return False 
        return True
    
    @classmethod
    def wrap_read_command(cls, command):
        ## 0x7F is Byte.MAX_VALUE
        return struct.pack('BBB', 0x7F, command, 0x0)
    
    @classmethod
    def wrap_write_command(cls, command, data):
        ## 0x7F is Byte.MAX_VALUE
        ## 0x80 is Byte.MIN_VALUE
        header = struct.pack('BBB', 0x7F, command, 0x80)
        buffer = bytes()
        for val in data:
            buffer += struct.pack('B', val)
        return header + buffer
    
    
    ## ====================================================================
    
    
    def __init__(self, commandType, data = None):
        self.type = commandType
        self.data = data
     
    def __eq__(self, other):
        if isinstance(other, int):
            return False
        if isinstance(other, DPGCommandType):
            return self.type == other
        else:
            return NotImplemented
     
    def wrap_command(self):
        command = self.type.value
        if self.data == None:
            ## read mode
            return self.wrap_read_command(command)
        else:
            return self.wrap_write_command(command, self.data)
    
    def get_receiver(self):
        return linak_service.Characteristic.DPG
    
    def is_read_operation(self):
        return (self.data == None)
    
    def __str__(self):
        return 'DPGCommand[%s, %s]' % (self.type.name, self.data)



@unique
class ControlCommand(Enum):
    ## contains tow accessors: 'name' and 'value'
    
    MOVE_1_DOWN = 70
    MOVE_1_UP = 71
    
    UNDEFINED = 254             ## used as stop 
    STOP_MOVING = 255
    
    
    def wrap_command(self):
        ## 0x7F is Byte.MAX_VALUE
        isCustomSpeed = False
        functionBit = 0
        if isCustomSpeed:
            return struct.pack('BB', self.value, 64 | functionBit)
        else:
            return struct.pack('BB', self.value, 0x0)
        
    def get_receiver(self):
        return linak_service.Characteristic.CONTROL
        
    def is_read_operation(self):
        return True
    
        
class DirectionalCommand():

    def __init__(self, position):
        self._position = position
    
    def wrap_command(self):
        return struct.pack('BB', 0x0, self._position)
    
    def get_receiver(self):
        return linak_service.Characteristic.CTRL1
    
    def is_read_operation(self):
        return True
    
    
    