#
#
#

import codecs
import struct
import logging

from enum import Enum, unique


_LOGGER = logging.getLogger(__name__)
    

@unique
class DPGCommand(Enum):
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
    USER_ID = 134
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
#     GET_LOG_ENTRY(144);
    
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
    def parse_data(cls, data):
        type = data[1]
        value = data[2:]
        
        #TODO: implement
        
        return None
    
    def wrap_read_command(self):
        return struct.pack('BBB', 0x7F, self.value, 0x0)

