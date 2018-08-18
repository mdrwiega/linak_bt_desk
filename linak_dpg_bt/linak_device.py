#
#
#

import logging
from time import sleep

import linak_dpg_bt
import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.datatype as datatype
 
import linak_dpg_bt.constants as constants
from .connection import BTLEConnection
from .desk_mover import DeskMover
from .datatype.desk_position import DeskPosition
from .dpg_command import *
from .datatype.height_speed import HeightSpeed


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
        self._capabilities = None
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
    def favorite_position_3(self):
        return self._wait_for_variable('_fav_position_3')
 
    @property
    def favorite_position_4(self):
        return self._wait_for_variable('_fav_position_4')

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

            self._name = conn.read_characteristic_by_enum(linak_service.Characteristic.DEVICE_NAME)

#             conn.subscribe_to_notification(constants.DPG_COMMAND_NOTIFY_HANDLE, 
#                                            constants.DPG_COMMAND_HANDLE, self._handle_dpg_notification)

            conn.subscribe_to_notification_enum(linak_service.Characteristic.DPG, self._handle_dpg_notification)

            # conn.dpg_command(constants.PROP_USER_ID)
            # conn.dpg_command(constants.PROP_GET_CAPABILITIES)
            conn.dpg_command(constants.PROP_DESK_OFFSET)
            conn.dpg_command(constants.PROP_MEMORY_POSITION_1)
            conn.dpg_command(constants.PROP_MEMORY_POSITION_2)
            
            conn.send_dpg_command(DPGCommand.PRODUCT_INFO)
            conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_3)
            conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_4)
            
            self._height_speed = HeightSpeed.from_bytes(conn.read_characteristic(constants.REFERENCE_OUTPUT_HANDLE))

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
        calculated_raw = DeskPosition.raw_from_cm(cm - self._desk_offset.cm)
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
        return DeskPosition(value.raw + self.desk_offset.raw)

    def _handle_dpg_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        ##_LOGGER.debug("Received notification from the device..")

#         ### convert string to byte array, required for Python2
#         data = bytearray(data)
        
        if DPGCommand.is_valid_response(data) == False:
            _LOGGER.debug("Received invalid response for command %s: %s", self._conn.currentCommand, " ".join("0x{:X}".format(x) for x in data))
            return 

        _LOGGER.debug("Received response for command %s: %s", self._conn.currentCommand, " ".join("0x{:X}".format(x) for x in data) )

        ## old way
        if self._conn.currentCommand == constants.PROP_GET_CAPABILITIES:
            self._capabilities = datatype.Capabilities( data )
            _LOGGER.debug( "Caps: %s", self._capabilities )
        elif self._conn.currentCommand == constants.PROP_DESK_OFFSET:
            self._desk_offset = datatype.DeskPosition.create(data)
            _LOGGER.debug( "Desk offset: %s", self._desk_offset )
        elif self._conn.currentCommand == constants.PROP_MEMORY_POSITION_1:
            self._fav_position_1 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 1: %s", self._fav_position_1 )
        elif self._conn.currentCommand == constants.PROP_MEMORY_POSITION_2:
            self._fav_position_2 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 2: %s", self._fav_position_2 )

        ## new way
        elif self._conn.currentCommand == DPGCommand.PRODUCT_INFO:
            info = datatype.ProductInfo( data )
            _LOGGER.debug("Product info: %s", info)
        elif self._conn.currentCommand == DPGCommand.GET_SETUP:
            pass
        elif self._conn.currentCommand == DPGCommand.USER_ID:
            uId = datatype.UserId( data )
            _LOGGER.debug( "User id: %s", uId )
        elif self._conn.currentCommand == DPGCommand.GET_CAPABILITIES:
            self._capabilities = datatype.Capabilities( data )
            _LOGGER.debug( "Caps: %s", self._capabilities )
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

    def _move_to_raw(self, raw_value):
        with self._conn as conn:
            current_raw_height = self.current_height.raw
            move_not_possible = (abs(raw_value - current_raw_height) < 10)

            if move_not_possible:
                _LOGGER.debug("Move not possible, current raw height: %d", current_raw_height)
                return

            DeskMover(conn, raw_value).start()


    # ===============================================================
     
    
    def initialize(self):
        _LOGGER.debug("Initializing the device")

        with self._conn as conn:
            """ We need to query for name before doing anything, without it device doesnt respond """
            
            ### on start:
            ## read GenericAccess.DEVICE_NAME
            ## setNotificationEnabled Services.DPG, DPG.DPG
            ## queueDPGCommand DeskControlCommand.USER_ID
            ## setNotificationEnabled Services.CONTROL, Control.ERROR
            ## read ReferenceOutput.MASK
            ## setNotificationEnabled Services.REFERENCE_OUTPUT all
            
            ## queueDPGCommand(DPGCommand.readCommand(DeskControlCommand.GET_SETUP));
            
            
            self._name = conn.read_characteristic_by_enum(linak_service.Characteristic.DEVICE_NAME)

            conn.subscribe_to_notification_enum(linak_service.Characteristic.DPG, self._handle_dpg_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.ERROR, self._handle_error_notification)
#             
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.HEIGHT_SPEED, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.TWO, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.THREE, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.FOUR, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.FIVE, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.SIX, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.SEVEN, self._handle_reference_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.EIGHT, self._handle_reference_notification)

            conn.send_dpg_command( DPGCommand.USER_ID )
#             conn.send_dpg_command( DPGCommand.USER_ID )
#             conn.send_dpg_command( DPGCommand.USER_ID )
#             conn.send_dpg_command( DPGCommand.USER_ID )

#             # conn.dpg_command(constants.PROP_USER_ID)
#             # conn.dpg_command(constants.PROP_GET_CAPABILITIES)
#             conn.dpg_command(constants.PROP_DESK_OFFSET)
#             conn.dpg_command(constants.PROP_MEMORY_POSITION_1)
#             conn.dpg_command(constants.PROP_MEMORY_POSITION_2)
#             
#             conn.send_dpg_command(DPGCommand.PRODUCT_INFO)
#             conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_3)
#             conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_4)
#             
#             self._height_speed = HeightSpeed.from_bytes(conn.read_characteristic(constants.REFERENCE_OUTPUT_HANDLE))
#             
#             self.moveUp()
#             
#             self.moveTo(80)
            
            ## =============== old
            
#         _LOGGER.debug("Querying the device..")
# 
#         with self._conn as conn:
#             """ We need to query for name before doing anything, without it device doesnt respond """
#             self._name = conn.get_characteristic_by_enum(linak_service.Characteristic.DEVICE_NAME).read()
#             
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.DPG, self._handle_dpg_notification)
#             conn.subscribe_to_notification_enum(linak_service.Characteristic.ERROR, self._handle_error_notification)
#             
#             self.print_services()
#             
#             ## fetch data on demand
# #             conn.send_dpg_command(DPGCommand.PRODUCT_INFO)
# #             conn.send_dpg_command(DPGCommand.GET_SETUP)
# #             conn.send_dpg_command(DPGCommand.USER_ID)
# #             conn.send_dpg_command(DPGCommand.GET_CAPABILITIES)
# #             conn.send_dpg_command(DPGCommand.REMINDER_SETTING)
#             conn.send_dpg_command(DPGCommand.DESK_OFFSET)
# #             
#             conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_1)
#             conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_2)
# #             conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_3)
# #             conn.send_dpg_command(DPGCommand.GET_SET_MEMORY_POSITION_4)
#             
# #             ## discovering services
# #             peripheral = conn._conn
# #             services = peripheral.getServices()
# #             for s in services:
# #                 self._handle_discovered_service(s)
# 
#             charData = conn.get_characteristic_by_enum(linak_service.Characteristic.HEIGHT_SPEED).read()
#             if charData != None:
#                 self._height_speed = datatype.HeightSpeed.from_bytes(charData)
#             
        _LOGGER.debug("Initialization done")

    def read_current_position(self):
        _LOGGER.debug("Reading current position")
        with self._conn as conn:
            conn.send_dpg_command(DPGCommand.DESK_OFFSET)
            charData = conn.read_characteristic_by_enum(linak_service.Characteristic.HEIGHT_SPEED)
            if charData == None:
                return None
            heightSpeed = datatype.HeightSpeed.from_bytes(charData)
            currPos = self._with_desk_offset(heightSpeed.height)
            return currPos.cm
        return None
     
    def read_favorite_number(self):
        _LOGGER.debug("Reading favourities number")
        with self._conn as conn:
            conn.send_dpg_command(DPGCommand.GET_CAPABILITIES)
            caps = self._wait_for_variable("_capabilities")
            if caps == None:
                return None
            return caps.memSize
        return None

    def moveTo(self, position):
        with self._conn as conn:
            command = DirectionalCommand( position )
            conn.send_directional_command( command )

    def moveUp(self):
        ## custom: 71, 64 | 0
        ## standard: 71, 0
        with self._conn as conn:
            conn.send_control_command( ControlCommand.MOVE_1_UP )
     
    def moveDown(self):
        ## custom: 70, 64 | 0
        ## standard: 70, 0
        with self._conn as conn:
            conn.send_control_command( ControlCommand.MOVE_1_DOWN )
     
    def stopMoving(self):
        ## custom: 255, 64 | 0
        ## standard: 255, 0
        with self._conn as conn:
            value = struct.pack('BB', 255, 0)
            conn.write_to_char( linak_service.Characteristic.CONTROL, value )

# #     def _handle_discovered_service(self, service):
# #         if service.uuid == linak_service.Service.GENERIC_ACCESS:
# #             self._name = self._get_char_data_from_service(service, linak_service.GenericAccess.DEVICE_NAME)
# #         elif service.uuid == linak_service.Service.REFERENCEOUTPUT:
# #             charData = self._get_char_data_from_service(service, linak_service.Characteristic.HEIGHT_SPEED)
# #             if charData != None:
# #                 self._height_speed = datatype.HeightSpeed.from_bytes(charData)
# #             charData = self._get_char_data_from_service(service, linak_service.Characteristic.MASK)
# #             if charData != None:
# #                 maskData = bytearray(charData)
# #                 maskBit = maskData[0]
# #                 if maskBit == 1:
# #                     _LOGGER.debug("Connected to Desk" )
# #                 elif maskBit == 64:
# #                     _LOGGER.debug("Connected to LegRest" )
# #                 elif maskBit == 128:
# #                     _LOGGER.debug("Connected to BackRest" )
# #                 elif maskBit == 0:
# #                     _LOGGER.debug("Invalid actuator" )
# #                 else:
# #                     _LOGGER.debug("Unknown actuator" )
# #         elif service.uuid == linak_service.Service.DPG:
# #             dpgChar = self._get_char_from_service(service, linak_service.Characteristic.DPG)            
# #             if dpgChar != None:
# #                 self._conn.subscribe_to_char(dpgChar, self._handle_dpg_notification)
# #                 self._conn.command(dpgChar, DPGCommand.PRODUCT_INFO)
# # #                 self._conn.command(dpgChar, DPGCommand.USER_ID)
# # #                 self._conn.command(dpgChar, DPGCommand.GET_CAPABILITIES)
# # #                 self._conn.command(dpgChar, DPGCommand.REMINDER_SETTING)
# #                 self._conn.command(dpgChar, DPGCommand.DESK_OFFSET)
# # #                 self._conn.command(dpgChar, DPGCommand.GET_SETUP)
# #                 ## invalid commands
# #                 self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_1)
# #                 self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_2)
# # #                 self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_3)
# # #                 self._conn.command(dpgChar, DPGCommand.GET_SET_MEMORY_POSITION_4)
 
#     def print_services(self):
#         _LOGGER.debug("Discovering services")
#         with self._conn as conn:
#             peripheral = conn._conn
# #             serviceList = peripheral.getServices()
# #             for s in serviceList:
# #                 _LOGGER.debug("Service: %s[%s]", s.uuid, s.uuid.getCommonName())
# #                 charsList = s.getCharacteristics()
# #                 for ch in charsList:
# #                     charString = linak_service.Characteristic.printCharacteristic(ch)
# #                     _LOGGER.debug("Char: %s", charString)
#                     
#             _LOGGER.debug("Characteristics:")
#             charsList = peripheral.getCharacteristics()
#             for ch in charsList:
#                 charString = linak_service.Characteristic.printCharacteristic(ch)
#                 _LOGGER.debug("Char: %s", charString)
#                 
# #             _LOGGER.debug("Descriptors:")
# #             descList = peripheral.getDescriptors()
# #             for desc in descList:
# # #                 _LOGGER.debug("Desc: %s: %s", desc, desc.read())
# #                 _LOGGER.debug("Desc: %s", desc)


    def _handle_error_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) errors."""
         
        ### convert string to byte array
        data = bytearray(data)
 
        _LOGGER.debug("XXXXX Received error data: [%s]", " ".join("0x{:X}".format(x) for x in data) )
        
    def _handle_reference_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) reference."""
         
        ### convert string to byte array
        data = bytearray(data)
 
        _LOGGER.debug("Received reference data: [%s]", " ".join("0x{:X}".format(x) for x in data) )
        
    def processNotifications(self):
        with self._conn as conn:
            conn.waitForNotifications()
        