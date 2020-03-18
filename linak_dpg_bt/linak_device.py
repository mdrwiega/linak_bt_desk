#
#
#

import logging
from time import sleep
from threading import Thread

from bluepy import btle

import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.datatype as datatype
 
from .connection import BTLEConnection
from .desk_mover import DeskMover
from .command import DPGCommandType, DPGCommand, ControlCommand, DirectionalCommand
from linak_dpg_bt.datatype.desk_position import DeskPosition
from .threadcounter import getThreadName


_LOGGER = logging.getLogger(__name__)


def to_string(data, numberType):
    if numberType == 'hex':
        return to_hex_string(data)
    if numberType == 'bin':
        to_bin_string(data)
    return to_hex_string(data)
    
def to_hex_string(data):
    return " ".join("0x{:02X}".format(x) for x in data)

def to_bin_string(data):
    return " ".join( '0b{:08b}'.format(x) for x in data )


class DPGCommandReadError(Exception):
    pass


class WrongFavoriteNumber(Exception):
    pass


class NotificationHandler(Thread):

    logger = None
    

    def __init__(self, desk, namePrefix=None):
        if namePrefix is None:
            namePrefix = "NotifHndlr"
        threadName = getThreadName(namePrefix)
        Thread.__init__(self, name=threadName)
        self.desk = desk
        self.daemon = True
        self.work = True
    
    def stop(self):
        self.work = False
    
    def run(self):
        while self.work == True:
            try:
                connected = self.desk.processNotifications()
                if connected:
                    sleep(0.001)                      ## prevents starving other thread
                else:
                    sleep(0.5)                        ## not connected -- sleep 0.5s  
            except btle.BTLEException as e:
                self.logger.error("exception occurred: %s %s", type(e), e)
                break
            except ConnectionRefusedError as e:
                self.logger.error("exception occurred: %s %s", type(e), e)
                break

NotificationHandler.logger = _LOGGER.getChild(NotificationHandler.__name__)


class LinakDesk:

    logger = None
        
    CLIENT_ID = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
    
    
    def __init__(self, bdaddr):
        self._bdaddr = bdaddr
        self._conn = BTLEConnection(bdaddr)

        self._name = None
        self._manu = None
        self._model = None
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
        self._speedChangeCallback = None
        self._notificationHandler = NotificationHandler(self)
        self._setting_callbacks = []
        self._fav_callbacks = []
        self.logger.debug("Constructed %s object: %r", self.__class__.__name__, self)

    def __del__(self):
        self.logger.debug("Deleting %s object: %r", self.__class__.__name__, self)

    @property
    def name(self):
        return self._wait_for_variable('_name')
    
    @property
    def deviceType(self):
        model = self._wait_for_variable('_model')
        manu = self._wait_for_variable('_manu')
        return model + " " + manu
    
    @property
    def capabilities(self):
        return self._wait_for_variable('_capabilities').capString()
    
    @property
    def userType(self):
        return self._wait_for_variable('_userType')
    
    @property
    def reminder(self):
        return self._wait_for_variable('_reminder').info()

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
        self._connect()

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
    
    def _without_desk_offset(self, value):
        return datatype.DeskPosition(value.raw - self.desk_offset.raw)

    def _handle_dpg_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        ##self.logger.debug("Received notification from the device..")
        
#         ### convert string to byte array, required for Python2
#         data = bytearray(data)

        currentCommand = self._conn.handleCurrentCommand()
        #if currentCommand == None:
        
        if DPGCommand.is_valid_response(data) == False:
            ## Error: DPG_Control packets needs to have 0x01 in first byte
            self.logger.debug("Received invalid response for command %s: %s", currentCommand, to_hex_string(data) )
            return

        if DPGCommand.is_valid_data(data) == False:
            ## received confirmation without data
            self.logger.debug("Received confirmation for command %s: %s", currentCommand, to_hex_string(data) )
            return

        self.logger.debug("Received response for command %s: %s", currentCommand, to_hex_string(data) )
        
        if currentCommand == DPGCommandType.PRODUCT_INFO:
            info = datatype.ProductInfo( data )
            self.logger.debug("Product info: %s", info)
        elif currentCommand == DPGCommandType.GET_SETUP:
            ## do nothing
            pass
        elif currentCommand == DPGCommandType.USER_ID:
            uId = datatype.UserId( data )
            self.logger.debug( "User id: %s", uId )
            self._userType = uId.type
        elif currentCommand == DPGCommandType.GET_CAPABILITIES:
            self._capabilities = datatype.Capabilities( data )
            self.logger.debug( "Caps: %s", self._capabilities )
        elif currentCommand == DPGCommandType.GET_SET_REMINDER_TIME:
            ##self._reminder = datatype.ReminderSetting( data )
            ##self.logger.debug( "Reminder: %s", self._reminder )
            pass
        elif currentCommand == DPGCommandType.REMINDER_SETTING:
            self._reminder = datatype.ReminderSetting.create( data )
            self.logger.debug( "Reminder: %s", self._reminder )
            self._call_setting_callbacks()
        elif currentCommand == DPGCommandType.DESK_OFFSET:
            self._desk_offset = datatype.DeskPosition.create(data)
            self.logger.debug( "Desk offset: %s", self._desk_offset )
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_1:
            self._fav_position_1 = datatype.FavoritePosition(data)
            self.logger.debug( "Favorite 1: %s", self._fav_position_1 )
            self._call_fav_callbacks(1)
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_2:
            self._fav_position_2 = datatype.FavoritePosition(data)
            self.logger.debug( "Favorite 2: %s", self._fav_position_2 )
            self._call_fav_callbacks(2)
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_3:
            self._fav_position_3 = datatype.FavoritePosition(data)
            self.logger.debug( "Favorite 3: %s", self._fav_position_3 )
            self._call_fav_callbacks(3)
        elif currentCommand == DPGCommandType.GET_SET_MEMORY_POSITION_4:
            self._fav_position_4 = datatype.FavoritePosition(data)
            self.logger.debug( "Favorite 4: %s", self._fav_position_4 )
            self._call_fav_callbacks(4)
        elif currentCommand == DPGCommandType.GET_LOG_ENTRY:
            logData = data[2:]
            if len(logData) > 4:
                logType = logData[0]
                if logType == 135:
                    self.logger.debug( "New position: %s", logData[1] )
                else:
                    self.logger.debug( "Log: %s", to_hex_string(logData) )
            else:
                self.logger.debug( "no log data" )
        else:
            self.logger.debug( "Command not handled: %r", currentCommand )

    def _move_to_raw(self, raw_value):
        with self._conn as conn:
            current_raw_height = self.current_height.raw
            move_not_possible = (abs(raw_value - current_raw_height) < 10)

            if move_not_possible:
                self.logger.debug("Move not possible, current raw height: %d", current_raw_height)
                return

            DeskMover(conn, raw_value).start()


    # ===============================================================
     
    
    def add_setting_callback(self, function):
        self._setting_callbacks.append( function )
        
    def remove_setting_callback(self, function):
        self._setting_callbacks.remove( function )
        
    def add_favorities_callback(self, function):
        self._fav_callbacks.append( function )
        
    def remove_favorities_callback(self, function):
        self._fav_callbacks.remove( function )
        
    def _call_setting_callbacks(self):
        for call in self._setting_callbacks:
            call()
            
    def _call_fav_callbacks(self, favNumber):
        for call in self._fav_callbacks:
            call(favNumber)
    
    def is_connected(self):
        if self._conn == None:
            return False
        return self._conn.isConnected()
    
    def initialize(self):
        try:
            self._connect()
            return True
        except BaseException as e:
            self.logger.error( "Initialization failed: %s %s", type(e), e )
            return False
    
    def _connect(self):
        self.logger.debug("Initializing the device")
        with self._conn as conn:
            """ We need to query for name before doing anything, without it device doesnt respond """

            peripheral = conn._conn
            ##self.print_services()
            services = peripheral.getServices()
            
            #### there is problem with services -- it arrives in random order
            ##for s in services:
            ##    self._handle_discovered_service(s)

            ### check if required services exist
            self._find_service(services, linak_service.Service.GENERIC_ACCESS)
            self._find_service(services, linak_service.Service.DPG)
            self._find_service(services, linak_service.Service.CONTROL)
            self._find_service(services, linak_service.Service.REFERENCE_INPUT)
            self._find_service(services, linak_service.Service.REFERENCE_OUTPUT)
               
            conn.subscribe_to_notification_enum(linak_service.Characteristic.HEIGHT_SPEED, self._handle_heigh_speed_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.TWO, self._handle_reference_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.THREE, self._handle_reference_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.FOUR, self._handle_reference_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.FIVE, self._handle_reference_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.SIX, self._handle_reference_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.SEVEN, self._handle_reference_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.EIGHT, self._handle_reference_notification)
            
            maskData = conn.read_characteristic_by_enum(linak_service.Characteristic.MASK)
            self._mask = datatype.Mask( maskData )
            self.logger.debug("Received mask: %s", self._mask)
            
            deviceName = conn.read_characteristic_by_enum(linak_service.Characteristic.DEVICE_NAME)
            self._name = deviceName.decode("utf-8")
            self.logger.debug("Received name: %s", self._name)
            
            try: 
                ## on IKEA branded devices MANUFACTURER characteristic returns binary content than 
                ## is impossible to convert to UTF-8 string. It leads to exception.
                manufacturer = conn.read_characteristic_by_enum(linak_service.Characteristic.MANUFACTURER)
                self._manu = manufacturer.decode("utf-8")
                self.logger.debug("Received manufacturer: %s", self._manu)
            except UnicodeDecodeError as e:
                self.logger.error( "Reading manufacturer failed: %s %s", type(e), e )
                self._manu = "<unknown manufacturer>"
                pass
            
            model = conn.read_characteristic_by_enum(linak_service.Characteristic.MODEL_NUMBER)
            self._model = model.decode("utf-8")
            self.logger.debug("Received model: %s", self._model)
            
            conn.subscribe_to_notification_enum(linak_service.Characteristic.DPG, self._handle_dpg_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.ERROR, self._handle_error_notification)
            conn.subscribe_to_notification_enum(linak_service.Characteristic.SERVICE_CHANGED, self._handle_service_notification)
            
            conn.send_dpg_read_command( DPGCommandType.USER_ID )
            
            response = conn.send_dpg_read_command( DPGCommandType.GET_SETUP )
            if response == False:
                return False
            
            conn.send_dpg_read_command( DPGCommandType.PRODUCT_INFO )
            
            self._read_capabilities()
            self._read_reminder_state()
            conn.send_dpg_read_command( DPGCommandType.DESK_OFFSET )
            
            conn.send_dpg_write_command( DPGCommandType.USER_ID, self.CLIENT_ID )
                             
            heightData = conn.read_characteristic_by_enum(linak_service.Characteristic.HEIGHT_SPEED)
            self._handle_heigh_speed_notification( linak_service.Characteristic.HEIGHT_SPEED.handle(), heightData )
   
            self._read_favorities_state()

            ## conn.send_dpg_read_command( DPGCommandType.GET_SET_REMINDER_TIME )
            ## conn.send_dpg_read_command( DPGCommandType.GET_LOG_ENTRY )
            
            heightNotification = conn.read_characteristic_by_handle(linak_service.Characteristic.HEIGHT_SPEED.handle() + 1)
            self.logger.debug("Notification status: %s", heightNotification)

        self._notificationHandler.start()

        self.logger.debug("Initialization done")
    
    def disconnect(self):
        if self._notificationHandler != None:
            self._notificationHandler.stop()
            self._notificationHandler.join()
            self._notificationHandler = None
        self._conn.disconnect()
    
    def set_position_change_callback(self, callback):
        self._posChangeCallback = callback
        
    def set_speed_change_callback(self, callback):
        self._speedChangeCallback = callback

    def set_disconnected_callback(self, callback):
        self._conn.set_disconnected_callback( callback )

    def read_current_position(self):
        currPos = self.current_height_with_offset
        return currPos.cmDouble()
    
    def read_current_speed(self):
        return self.current_speed.raw
     
    def read_reminder_values(self):
        return self._reminder.getReminders()
    
    def reminder_settings(self):
        return self._reminder
    
    def favorities(self):
        return [self._fav_position_1, self._fav_position_2, self._fav_position_3, self._fav_position_4]

    def read_favorite_positions(self):
        favNumber = self.read_favorite_number()
        retList = []
        for i in range(favNumber):
            fav = self.favorite_position(i+1)
            if fav.position != None:
                favPos = self._with_desk_offset( fav.position )
                retList.append( favPos.cm )
            else:
                retList.append(None)
        return retList
    
    def read_favorite_number(self):
        caps = self._wait_for_variable("_capabilities")
        if caps == None:
            return None
        return caps.memSize

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

    def set_favorite_position(self, favIndex, value):
        favNumber = favIndex+1
        fav = self.favorite_position(favNumber)
        if value==None:
            fav.position = None
            self.logger.info("changed position %s %s", str(favNumber), str(value))
        else:
            newValue = DeskPosition.from_cm(value)
            favPos = self._without_desk_offset( newValue )
            fav.position = favPos
            self.logger.info("changed position %s %s %s", str(favNumber), str(value), favPos)
        self._call_fav_callbacks(favNumber)

    def moveUp(self):
        ## custom: 71, 64 | 0
        ## standard: 71, 0
#         self.logger.debug("Sending moveUp")
        with self._conn as conn:
            return conn.send_control_command( ControlCommand.MOVE_1_UP )
     
    def moveDown(self):
        ## custom: 70, 64 | 0
        ## standard: 70, 0
#         self.logger.debug("Sending moveDown")
        with self._conn as conn:
            return conn.send_control_command( ControlCommand.MOVE_1_DOWN )

    def moveToTop(self):
        ##return self.moveTo(32766)     ## 0x7FFE - maximal possible value to work
        return self.moveTo(30000)       ## 3 meters up
    
    def moveToBottom(self):
        return self.moveTo(0)

    def moveToFav(self, favIndex):
        fav = self.favorite_position(favIndex+1)
        if fav.position == None:
            return False
        pos = fav.position.raw
        return self.moveTo(pos)
     
    def moveTo(self, position):
        if position == None:
            return False
        with self._conn as conn:
            command = DirectionalCommand( position )
            return conn.send_directional_command( command )
     
    def stopMoving(self):
        with self._conn as conn:
#             self.logger.debug("Sending stopMoving")
            conn.send_control_command( ControlCommand.STOP_MOVING )

    def send_desk_height(self, cmValue):
        ## height = offset + piston
        ## offset = height - piston
        ## piston = height - offset
        piston = self.current_height
        newOffset = cmValue - piston.cmDouble()
        self._desk_offset.setFromCm( newOffset )
        
        with self._conn as conn:
            value = self._desk_offset.bytes()
            ## add 1 at beginning
            value = bytes([1]) + value
            self.logger.info("Sending offset: %s %s", value, to_hex_string(value) )
            conn.send_dpg_write_command( DPGCommandType.DESK_OFFSET, value )

    ## after reeiving this command device's display should activate
    def activate_display(self):
        with self._conn as conn:
            conn.send_control_command( ControlCommand.UNDEFINED )

    def read_capabilities(self):
        with self._conn as conn:
            conn.send_dpg_read_command( DPGCommandType.GET_CAPABILITIES )
            
    def _read_capabilities(self):
        self._conn.send_dpg_read_command( DPGCommandType.GET_CAPABILITIES )
        
    def read_reminder_state(self):
        with self._conn as conn:
            conn.send_dpg_read_command( DPGCommandType.REMINDER_SETTING )

    def _read_reminder_state(self):
        self._conn.send_dpg_read_command( DPGCommandType.REMINDER_SETTING )

    def send_reminder_state(self):
        with self._conn as conn:
            value = self._reminder.raw_data()
            self.logger.info("Sending reminder: %s %s %s", value, to_bin_string( value[0:1] ), to_hex_string(value[1:]) )
            conn.send_dpg_write_command( DPGCommandType.REMINDER_SETTING, value )
            ## refresh device/display state
            self.activate_display()    
            ## wait for device to react
            ## sleep(2)

    def selectReminder(self, number):
        self._reminder.switchReminder(number)
        self.send_reminder_state()
            
    def toggleCmInch(self, useCm):
        self._reminder.setCmUnit(useCm)
        self.send_reminder_state()
            
    def switchLightsReminder(self, state):
        self._reminder.switchLights(state)
        self.send_reminder_state()

    def read_favorities_state(self):
        with self._conn as conn:
            favNum = self.read_favorite_number()
            if favNum >= 1:
                conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_1 )
            if favNum >= 2:
                conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_2 )
            if favNum >= 3:
                conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_3 )
            if favNum >= 4:
                conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_4 )

    def _read_favorities_state(self):
        favNum = self.read_favorite_number()
        if favNum >= 1:
            self._conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_1 )
        if favNum >= 2:
            self._conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_2 )
        if favNum >= 3:
            self._conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_3 )
        if favNum >= 4:
            self._conn.send_dpg_read_command( DPGCommandType.GET_SET_MEMORY_POSITION_4 )
    
    def send_favorities_state(self):
        favNum = self.read_favorite_number()
        if favNum >= 1:
            self.send_fav(1)
        if favNum >= 2:
            self.send_fav(2)
        if favNum >= 3:
            self.send_fav(3)
        if favNum >= 4:
            self.send_fav(4)

    def send_fav(self, favIndex):
        favNumber = favIndex+1
        cmd = DPGCommandType.getMemoryPosition(favNumber)
        if cmd == None:
            raise RuntimeError("invalid command for fav: ", str(favNumber))
        fav = self.favorite_position( favNumber )
        if fav == None:
            raise RuntimeError("invalid fav for number: ", str(favNumber))
        pos = fav.getPosition()
        with self._conn as conn:
            value = None
            if pos == None:
                ## add 0 at beginning
                value = bytes([0])
            else:
                value = pos.bytes()
                ## add 1 at beginning
                value = bytes([1]) + value
            self.logger.info("Sending fav: %s %s %s %s", favNumber, value, to_bin_string( value ), to_hex_string( value ) )
            conn.send_dpg_write_command( cmd, value )

    def _find_service(self, services, linakService):
        findUUID = linakService.uuid()
        for s in services:
            serviceUUID = str(s.uuid).upper()
            if serviceUUID == findUUID:
                return s
        raise RuntimeError("service not found: ", linakService)

    def print_services(self):
        self.logger.debug("Discovering services")
        with self._conn as conn:
            peripheral = conn._conn
            serviceList = peripheral.getServices()
            for s in serviceList:
                sUuidString = linak_service.Service.printUUID(s.uuid)
                self.logger.debug("" )
                self.logger.debug("Service: %s", sUuidString)
                charsList = s.getCharacteristics()
                for ch in charsList:
                    charString = linak_service.Characteristic.printCharacteristic(ch)
                    self.logger.debug("%s", charString)

                descList = s.getDescriptors()
                for desc in descList:
                    descUuidString = linak_service.Characteristic.printUUID(desc.uuid)
                    self.logger.debug("Description: %s %s", descUuidString, hex(desc.handle) )
                      
#             self.logger.debug("Characteristics:")
#             charsList = peripheral.getCharacteristics()
#             for ch in charsList:
#                 charString = linak_service.Characteristic.printCharacteristic(ch)
#                 self.logger.debug("Char: %s", charString)
                  
#             self.logger.debug("Descriptors:")
#             descList = peripheral.getDescriptors()
#             for desc in descList:
# #                 self.logger.debug("Desc: %s: %s", desc, desc.read())
#                 self.logger.debug("Desc: %s", desc)


    def _handle_error_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) errors."""
         
        ### convert string to byte array
        data = bytearray(data)
 
        self.logger.debug("XXXXX Received error data: [%s]", to_hex_string(data) )
        
    def _handle_heigh_speed_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) reference."""
         
        ### convert string to byte array
        data = bytearray(data)
 
        self._height_speed = datatype.HeightSpeed.from_bytes( data )
        pos = self.current_height_with_offset.raw
        raw = self.current_height.raw
        self.logger.debug("Received height: %s %s data: %s", pos, raw, self._height_speed)
        
        for hand in self.logger.handlers:
            hand.flush()
        
        if self._posChangeCallback != None:
            self._posChangeCallback()
        if self._speedChangeCallback != None:
            self._speedChangeCallback()
            
    def _handle_reference_notification(self, cHandle, data):
        """Handle Callback from a Bluetooth (GATT) reference."""
        
        ### convert string to byte array
        
        data = bytearray(data)
        self.logger.debug("Received reference data: [%s]", to_hex_string(data) )
            
    def _handle_service_notification(self, cHandle, data):
        ### convert string to byte array
        
        data = bytearray(data)
        self.logger.debug("Received service data: [%s]", to_hex_string(data) )
        
    def processNotifications(self):
        return self._conn.processNotifications()
                
LinakDesk.logger = _LOGGER.getChild(LinakDesk.__name__)

