#
#
#

import logging
from time import sleep

import linak_dpg_bt.constants as constants
from .connection import BTLEConnection
from .desk_mover import DeskMover
from .dpg_command import *

import linak_dpg_bt
import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.datatype as datatype


_LOGGER = logging.getLogger(__name__)


class DPGCommandReadError(Exception):
    pass


class WrongFavoriteNumber(Exception):
    pass


class LinakDesk:
    def __init__(self, bdaddr):
        self._bdaddr = bdaddr
        self._conn = BTLEConnection(bdaddr)

        self._name = None
        self._desk_offset = None
        self._fav_position_1 = None
        self._fav_position_2 = None
        self._height_speed = None

    @property
    def name(self):
        return self._wait_for_variable('_name')

    @property
    def desk_offset(self):
        return self._wait_for_variable('_desk_offset')

    @property
    def favorite_position_1(self):
        return self._wait_for_variable('_fav_position_1')

    @property
    def favorite_position_2(self):
        return self._wait_for_variable('_fav_position_2')

    @property
    def current_height(self):
        return self.height_speed.height

    @property
    def current_height_with_offset(self):
        return self._with_desk_offset(self.height_speed.height)

    @property
    def height_speed(self):
        return self._wait_for_variable('_height_speed')

    def read_dpg_data(self):
        _LOGGER.debug("Querying the device..")

        with self._conn as conn:
            """ We need to query for name before doing anything, without it device doesnt respond """
            self._name = conn.read_characteristic_by_uuid(linak_service.Characteristic.DEVICE_NAME).read()
            
            conn.subscribe_to_char_by_uuid(linak_service.Characteristic.DPG, self._handle_dpg_notification)
            conn.subscribe_to_char_by_uuid(linak_service.Characteristic.ERROR, self._handle_error_notification)
            
            conn.dpg_command(DPGCommand.PRODUCT_INFO)
            conn.dpg_command(DPGCommand.GET_SETUP)
            conn.dpg_command(DPGCommand.USER_ID)
            conn.dpg_command(DPGCommand.GET_CAPABILITIES)
            conn.dpg_command(DPGCommand.REMINDER_SETTING)
            conn.dpg_command(DPGCommand.DESK_OFFSET)
            
            
            ## invalid commands
            conn.dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_1)
            conn.dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_2)
            conn.dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_3)
            conn.dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_4)
            
#             ## discovering services
#             peripheral = conn._conn
#             services = peripheral.getServices()
#             for s in services:
#                 self._handle_discovered_service(s)

            charData = conn.read_characteristic_by_uuid(linak_service.Characteristic.HEIGHT_SPEED).read()
            if charData != None:
                self._height_speed = datatype.HeightSpeed.from_bytes(charData)
            

#     def dpg_command(self, command_type):
#         with self._conn as conn:
#             conn.dpg_command(command_type)

    def __str__(self):
        return "[%s] Desk offset: %s, name: %s\nFav1: %s, Fav2: %s Height with offset: %s" % (
            self._bdaddr,
            self.desk_offset.human_cm,
            self.name,
            self._with_desk_offset(self.favorite_position_1).human_cm,
            self._with_desk_offset(self.favorite_position_2).human_cm,
            self._with_desk_offset(self.height_speed.height).human_cm,
        )

    def move_to_cm(self, cm):
        calculated_raw = datatype.DeskPosition.raw_from_cm(cm - self._desk_offset.cm)
        self._move_to_raw(calculated_raw)

    def move_to_fav(self, fav):
        if fav == 1:
            raw = self.favorite_position_1.raw
        elif fav == 2:
            raw = self.favorite_position_2.raw
        else:
            raise DPGCommandReadError('Favorite with position: %d does not exists' % fav)

        self._move_to_raw(raw)

    def _wait_for_variable(self, var_name):
        value = getattr(self, var_name)
        if value is not None:
            return value

        for _ in range(0, 100):
            value = getattr(self, var_name)

            if value is not None:
                return value

            sleep(0.2)

        raise DPGCommandReadError('Cannot fetch value for %s' % var_name)

    def _with_desk_offset(self, value):
        return datatype.DeskPosition(value.raw + self.desk_offset.raw)

    def _handle_discovered_service(self, service):
        if service.uuid == linak_service.Service.GENERIC_ACCESS:
            self._name = self._get_char_data_from_service(service, linak_service.GenericAccess.DEVICE_NAME)
        elif service.uuid == linak_service.Service.REFERENCEOUTPUT:
            charData = self._get_char_data_from_service(service, linak_service.Characteristic.HEIGHT_SPEED)
            if charData != None:
                self._height_speed = datatype.HeightSpeed.from_bytes(charData)
            charData = self._get_char_data_from_service(service, linak_service.Characteristic.MASK)
            if charData != None:
                maskData = bytearray(charData)
                maskBit = maskData[0]
                if maskBit == 1:
                    _LOGGER.debug("Connected to Desk" )
                elif maskBit == 64:
                    _LOGGER.debug("Connected to LegRest" )
                elif maskBit == 128:
                    _LOGGER.debug("Connected to BackRest" )
                elif maskBit == 0:
                    _LOGGER.debug("Invalid actuator" )
                else:
                    _LOGGER.debug("Unknown actuator" )
        elif service.uuid == linak_service.Service.DPG:
            dpgChar = self._get_char_from_service(service, linak_service.Characteristic.DPG)            
            if dpgChar != None:
                self._conn.subscribe_to_char(dpgChar, self._handle_dpg_notification)
                self._conn.command(dpgChar, DPGCommand.PRODUCT_INFO)
#                 self._conn.command(dpgChar, DPGCommand.USER_ID)
#                 self._conn.command(dpgChar, DPGCommand.GET_CAPABILITIES)
#                 self._conn.command(dpgChar, DPGCommand.REMINDER_SETTING)
                self._conn.command(dpgChar, DPGCommand.DESK_OFFSET)
#                 self._conn.command(dpgChar, DPGCommand.GET_SETUP)
                ## invalid commands
                self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_1)
                self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_2)
#                 self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_3)
#                 self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_4)
        
    def _get_char_from_service(self, service, characteristicUuid):
        charList = service.getCharacteristics(characteristicUuid)
        if len(charList) == 1:
            return charList[0]
        return None
    
    def _get_char_data_from_service(self, service, characteristicUuid):
        charObj = self._get_char_from_service(service, characteristicUuid)
        if charObj != None:
            return charObj.read()
        return None
        
    def _handle_dpg_notification(self, data):
        """Handle Callback from a Bluetooth (GATT) request."""
#         _LOGGER.debug("Received notification from the device..")
        
        ### convert string to byte array
        data = bytearray(data)

        _LOGGER.debug("Received notification data: [%s]", " ".join("0x{:X}".format(x) for x in data) )

        if DPGCommand.is_valid_response(data) == False:
            return 

        _LOGGER.debug("Received response for command: %s", self._conn.currentCommand)

        if self._conn.currentCommand == DPGCommand.PRODUCT_INFO:
            info = datatype.ProductInfo( data )
            _LOGGER.debug("Product info: %s", info)
        elif self._conn.currentCommand == DPGCommand.GET_SETUP:
            pass
        elif self._conn.currentCommand == DPGCommand.USER_ID:
            uId = datatype.UserId( data )
            _LOGGER.debug( "User id: %s", uId )
        elif self._conn.currentCommand == DPGCommand.GET_CAPABILITIES:
            caps = datatype.Capabilities( data )
            _LOGGER.debug( "Caps: %s", caps )
        elif self._conn.currentCommand == DPGCommand.REMINDER_SETTING:
            reminder = datatype.ReminderSetting( data )
            _LOGGER.debug( "Reminder: %s", reminder )
        elif self._conn.currentCommand == DPGCommand.DESK_OFFSET:
            self._desk_offset = datatype.DeskPosition.create(data)
            _LOGGER.debug( "Desk offset: %s", self._desk_offset )
        elif self._conn.currentCommand == DPGCommand.GET_SET_MEMORY_POSITION_1:
            self._fav_position_1 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 1: %s", self._fav_position_1 )
        elif self._conn.currentCommand == DPGCommand.GET_SET_MEMORY_POSITION_2:
            self._fav_position_2 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 2: %s", self._fav_position_2 )
        elif self._conn.currentCommand == DPGCommand.GET_SET_MEMORY_POSITION_3:
            self._fav_position_3 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 3: %s", self._fav_position_3 )
        elif self._conn.currentCommand == DPGCommand.GET_SET_MEMORY_POSITION_4:
            self._fav_position_4 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 4: %s", self._fav_position_4 )
        else:
            _LOGGER.debug( "Command not handled" )

    def _handle_error_notification(self, data):
        """Handle Callback from a Bluetooth (GATT) errors."""
        
        ### convert string to byte array
        data = bytearray(data)

        _LOGGER.debug("Received error data: [%s]", " ".join("0x{:X}".format(x) for x in data) )
        

    def _move_to_raw(self, raw_value):
        with self._conn as conn:
            current_raw_height = self.current_height.raw
            move_not_possible = (abs(raw_value - current_raw_height) < 10)

            if move_not_possible:
                _LOGGER.debug("Move not possible, current raw height: %d", current_raw_height)
                return

            DeskMover(conn, raw_value).start()
