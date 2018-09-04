#
#
#

import logging
from time import sleep
from threading import Thread

import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.datatype as datatype
 
import linak_dpg_bt.constants as constants
from .connection import BTLEConnection
from .desk_mover import DeskMover
from .datatype.desk_position import DeskPosition
from .command import DPGCommandType, DPGCommand, ControlCommand, DirectionalCommand
from .datatype.height_speed import HeightSpeed



_LOGGER = logging.getLogger(__name__)



class DPGCommandReadError(Exception):
    pass


class WrongFavoriteNumber(Exception):
    pass


class NotificationHandler(Thread):
    def __init__(self, desk):
        Thread.__init__(self)
        self.desk = desk
        self.daemon = True
        
    def run(self):
        while True:
            self.desk.processNotifications()


class LinakDesk:
    def __init__(self, bdaddr):
        self._bdaddr = bdaddr
        self._conn = BTLEConnection(bdaddr)

        self._name = None
        self._userType = None
        self._capabilities = None
        self._desk_offset = None
        self._fav_position_1 = None
        self._fav_position_2 = None
        self._fav_position_3 = None
        self._fav_position_4 = None
        self._height_speed = None
        self._mask = None
        self._posChangeCallback = None
        self._notificationHandler = NotificationHandler(self)

    @property
    def name(self):
        return self._wait_for_variable('_name')
    
    @property
    def userType(self):
        return self._wait_for_variable('_userType')

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

    def favorite_position(self, favIndex):
        return self._wait_for_variable('_fav_position_' + str(favIndex))

    @property
    def current_height(self):
        return self.height_speed.height
    
    @property
    def current_speed(self):
        return self.height_speed.speed

    @property
    def current_height_with_offset(self):
        return self._with_desk_offset(self.height_speed.height)

    @property
    def height_speed(self):
        return self._wait_for_variable('_height_speed')

    def read_dpg_data(self):
        self.initialize()

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

        currentCommand = self._conn.handleCurrentCommand()
        #if currentCommand == None:
        
        if DPGCommand.is_valid_response(data) == False:
            _LOGGER.debug("Received invalid response for command %s: %s", currentCommand, " ".join("0x{:X}".format(x) for x in data))
            return 

        _LOGGER.debug("Received response for command %s: %s", currentCommand, " ".join("0x{:X}".format(x) for x in data) )
        
        if currentCommand == DPGCommandType.PRODUCT_INFO:
            info = datatype.ProductInfo( data )
            _LOGGER.debug("Product info: %s", info)
        elif currentCommand == DPGCommandType.GET_SETUP:
            ## do nothing
            pass
        elif currentCommand == DPGCommandType.USER_ID:
            uId = datatype.UserId( data )
            _LOGGER.debug( "User id: %s", uId )
            self._userType = uId.type
        elif currentCommand == DPGCommandType.GET_CAPABILITIES:
            self._capabilities = datatype.Capabilities( data )
            _LOGGER.debug( "Caps: %s", self._capabilities )
        elif currentCommand == DPGCommandType.REMINDER_SETTING:
            reminder = datatype.ReminderSetting( data )
            _LOGGER.debug( "Reminder: %s", reminder )
        elif currentCommand == DPGCommandType.DESK_OFFSET:
            self._desk_offset = datatype.DeskPosition.create(data)
            _LOGGER.debug( "Desk offset: %s", self._desk_offset )
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_1:
            self._fav_position_1 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 1: %s", self._fav_position_1 )
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_2:
            self._fav_position_2 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 2: %s", self._fav_position_2 )
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_3:
            self._fav_position_3 = datatype.FavoritePosition(data)
            _LOGGER.debug( "Favorite 3: %s", self._fav_position_3 )
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_4:
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
        try:
            with self._conn as conn:
                """ We need to query for name before doing anything, without it device doesnt respond """

                peripheral = conn._conn
                services = peripheral.getServices()
                
                #### there is problem with services -- it arrives in random order
                ##for s in services:
                ##    self._handle_discovered_service(s)
    
                ### check if required services exist
                self._find_service(services, linak_service.Service.GENERIC_ACCESS)
                self._find_service(services, linak_service.Service.DPG)
                self._find_service(services, linak_service.Service.CONTROL)
                self._find_service(services, linak_service.Service.REFERENCE_OUTPUT)
                
                
                deviceName = conn.read_characteristic_by_enum(linak_service.Characteristic.DEVICE_NAME)
                self._name = deviceName.decode("utf-8")
                _LOGGER.debug("Received name: %s", self._name)
       
                conn.subscribe_to_notification_enum(linak_service.Characteristic.DPG, self._handle_dpg_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.ERROR, self._handle_error_notification)
                   
                maskData = conn.read_characteristic_by_enum(linak_service.Characteristic.MASK)
                self._mask = datatype.Mask( maskData )
                _LOGGER.debug("Received mask: %s", self._mask)
                   
                conn.subscribe_to_notification_enum(linak_service.Characteristic.HEIGHT_SPEED, self._handle_heigh_speed_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.TWO, self._handle_reference_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.THREE, self._handle_reference_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.FOUR, self._handle_reference_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.FIVE, self._handle_reference_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.SIX, self._handle_reference_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.SEVEN, self._handle_reference_notification)
                conn.subscribe_to_notification_enum(linak_service.Characteristic.EIGHT, self._handle_reference_notification)
       
                conn.send_dpg_read_command( DPGCommandType.USER_ID )
                conn.send_dpg_read_command( DPGCommandType.PRODUCT_INFO )
                conn.send_dpg_read_command( DPGCommandType.GET_SETUP )
                 
                conn.send_dpg_read_command( DPGCommandType.GET_CAPABILITIES )
                conn.send_dpg_read_command( DPGCommandType.REMINDER_SETTING )
                conn.send_dpg_read_command( DPGCommandType.DESK_OFFSET )
                                 
                heightData = conn.read_characteristic_by_enum(linak_service.Characteristic.HEIGHT_SPEED)
                self._handle_heigh_speed_notification( linak_service.Characteristic.HEIGHT_SPEED.handle(), heightData )
                 
                userId = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
                conn.send_dpg_write_command( DPGCommandType.USER_ID, userId )
       
                favNum = self.read_favorite_number()
                if favNum >= 1:
                    conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_1 )
                if favNum >= 2:
                    conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_2 )
                if favNum >= 3:
                    conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_3 )
                if favNum >= 4:
                    conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_4 )

    
            self._notificationHandler.start()
    
            _LOGGER.debug("Initialization done")
            
        except BaseException as e:
            _LOGGER.exception( "e" )
            raise e
     
    def set_position_change_callback(self, callback):
        self._posChangeCallback = callback

    def read_current_position(self):
        currPos = self.current_height_with_offset
        return currPos.cm
     
    def read_favorite_number(self):
        with self._conn:
            caps = self._wait_for_variable("_capabilities")
            if caps == None:
                return None
            return caps.memSize
        return None

    def read_favorite_values(self):
        favNumber = self.read_favorite_number()
        retList = []
        for i in range(favNumber):
            fav = self.favorite_position(i+1)
            if fav.position != None:
                favPos = self._with_desk_offset( fav.position )
                retList.append( favPos.human_cm )
            else:
                retList.append(None)
        return retList

    def moveUp(self):
        ## custom: 71, 64 | 0
        ## standard: 71, 0
#         _LOGGER.debug("Sending moveUp")
        with self._conn as conn:
            conn.send_control_command( ControlCommand.MOVE_1_UP )
     
    def moveDown(self):
        ## custom: 70, 64 | 0
        ## standard: 70, 0
#         _LOGGER.debug("Sending moveDown")
        with self._conn as conn:
            conn.send_control_command( ControlCommand.MOVE_1_DOWN )

    def moveToFav(self, favIndex):
        fav = self.favorite_position(favIndex+1)
        if fav.position == None:
            return
        pos = fav.position.raw
        self.moveTo(pos)
     
    def moveTo(self, position):
        if position == None:
            return
        with self._conn as conn:
            command = DirectionalCommand( position )
            conn.send_directional_command( command )
     
    def stopMoving(self):
        with self._conn as conn:
#             _LOGGER.debug("Sending stopMoving")
            conn.send_control_command( ControlCommand.STOP_MOVING )

    def _find_service(self, services, linakService):
        findUUID = linakService.uuid()
        for s in services:
            serviceUUID = str(s.uuid).upper()
            if serviceUUID == findUUID:
                return s
        raise RuntimeError("service not found: ", linakService)

    def print_services(self):
        _LOGGER.debug("Discovering services")
        with self._conn as conn:
            peripheral = conn._conn
            serviceList = peripheral.getServices()
            for s in serviceList:
                _LOGGER.debug("Service: %s[%s]", s.uuid, s.uuid.getCommonName())
                charsList = s.getCharacteristics()
                for ch in charsList:
                    charString = linak_service.Characteristic.printCharacteristic(ch)
                    _LOGGER.debug("Char: %s", charString)

                descList = s.getDescriptors()
                for desc in descList:
    #                 _LOGGER.debug("Desc: %s: %s", desc, desc.read())
                    _LOGGER.debug("Desc: %s", desc)
                      
#             _LOGGER.debug("Characteristics:")
#             charsList = peripheral.getCharacteristics()
#             for ch in charsList:
#                 charString = linak_service.Characteristic.printCharacteristic(ch)
#                 _LOGGER.debug("Char: %s", charString)
                  
#             _LOGGER.debug("Descriptors:")
#             descList = peripheral.getDescriptors()
#             for desc in descList:
# #                 _LOGGER.debug("Desc: %s: %s", desc, desc.read())
#                 _LOGGER.debug("Desc: %s", desc)


    def _handle_error_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) errors."""
         
        ### convert string to byte array
        data = bytearray(data)
 
        _LOGGER.debug("XXXXX Received error data: [%s]", " ".join("0x{:X}".format(x) for x in data) )
        
    def _handle_heigh_speed_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) reference."""
         
        ### convert string to byte array
        data = bytearray(data)
 
        self._height_speed = datatype.HeightSpeed.from_bytes( data )
        pos = self.current_height_with_offset
        _LOGGER.debug("Received height: %s data: %s", pos, self._height_speed)
        
        if self._posChangeCallback != None:
            self._posChangeCallback()
            
    def _handle_reference_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) reference."""
        
        ### convert string to byte array
        
        data = bytearray(data)
        _LOGGER.debug("Received reference data: [%s]", " ".join("0x{:X}".format(x) for x in data) )
        
    def processNotifications(self):
        with self._conn as conn:
            while True:
                conn.processNotifications()
                sleep(0.1)                      ## prevents starving other thread
        