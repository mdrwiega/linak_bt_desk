"""
Taken from python-eq3bt/master/eq3bt/connection.py

A simple wrapper for bluepy's btle.Connection.
Handles Connection duties (reconnecting etc.) transparently.
"""

import logging
import struct
from time import sleep
from functools import wraps

from bluepy import btle

from .command import DPGCommand
import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.constants as constants
from .synchronized import synchronized



_LOGGER = logging.getLogger(__name__)



def to_hex_string(data):
    ## return codecs.encode(data, 'hex')
    return " ".join("0x{:02X}".format(x) for x in data)


def DisconnectOnException(func):
    """Decorator calling 'disconnect()' on BTLE exception."""
    
    @wraps(func)
    def wrapper(*args):
        try:
            return func(*args)
        except btle.BTLEException as e:
            _LOGGER.error("bluetooth exception occurred: %s %s", type(e), e)
            connectionObj = args[0]
            connectionObj.disconnect()
            raise
    return wrapper


class BTLEConnection(btle.DefaultDelegate):
    """Representation of a BTLE Connection."""
    
    logger = None


    def __init__(self, mac):
        """Initialize the connection."""
        btle.DefaultDelegate.__init__(self)

        self._conn = None
        self._mac = mac
        self._callbacks = {}
        self.currentCommand = None
        self._disconnectedCallback = None
#         self.dpgQueue = CommandQueue(self)
        self.logger.debug("Constructed %s object: %r", self.__class__.__name__, self)

    @synchronized
    def __enter__(self):
        """
        Context manager __enter__ for connecting the device
        :rtype: btle.Peripheral
        :return:
        """
        
        if self._conn != None:
            return self
        
        self.connect()
        
        return self

    @synchronized
    def __exit__(self, exc_type, exc_val, exc_tb):
        ### do not disconnect -- otherwise notification callbacks will be lost
        pass

    @synchronized
    def __del__(self):
        #TODO: make disconnection on CTRL+C
        self.logger.debug("Deleting %s object: %r", self.__class__.__name__, self)
        self.disconnect()

    @synchronized
    @DisconnectOnException
    def connect(self):
        self.disconnect()
        
        self.logger.debug("Trying to connect to %s", self._mac)
        connected = False
        for _ in range(0,2):
            try:
                self._conn = btle.Peripheral()
                self._conn.withDelegate(self)
                self._conn.connect(self._mac, addrType='random')
                connected = True
                break
            except btle.BTLEException as ex:
                self.logger.debug( "Connection error: %s", ex )
                sleep(1)
                
        if connected == False:
            self.logger.error("Connection to %s failed", self._mac)
            raise ConnectionRefusedError("Connection to %s failed" % self._mac)

        self.logger.debug("Connected to %s", self._mac)
    
    @synchronized
    @DisconnectOnException
    def disconnect(self):
        if self._conn:
            self.logger.debug("disconnecting")
            self._conn.disconnect()
            self._conn = None
            if self._disconnectedCallback != None:
                self._disconnectedCallback()

    @synchronized
    def isConnected(self):
        return (self._conn != None)

    def set_disconnected_callback(self, callback):
        self._disconnectedCallback = callback

    def handleNotification(self, handle, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        if handle in self._callbacks:
#             self.logger.debug("Got notification from %s: %s", linak_service.Characteristic.find(handle), to_hex_string(data))
            callback = self._callbacks[handle]
            try:
                callback(handle, data)
            except TypeError as e:
                self.logger.error( "error: %s for %s", e, repr(callback) )
                raise e
        else:
            self.logger.debug("Got notification without callback from %s: %s", linak_service.Characteristic.find(handle), to_hex_string(data))

    @property
    def mac(self):
        """Return the MAC address of the connected device."""
        return self._mac

    def set_callback(self, handle, function):
        """Set the callback for a Notification handle. It will be called with the parameter data, which is binary."""
        self._callbacks[handle] = function

    @synchronized
    @DisconnectOnException
    def make_request(self, handle, value, timeout=constants.DEFAULT_TIMEOUT, with_response=True):
        """Write a GATT Command without callback - not utf-8."""
        try:
            charEnum = linak_service.Characteristic.findByHandle(handle)
            if charEnum == None:
                charEnum = handle
            self.logger.debug("Writing request %s to %s w_resp=%s", to_hex_string(value), charEnum, with_response)
            self._conn.writeCharacteristic(handle, value, withResponse=with_response)
            if timeout:
                self.logger.debug("Waiting for notifications for %s", timeout)
                self._waitForNotifications(timeout)
        except btle.BTLEException as ex:
            self.logger.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    def subscribe_to_notification(self, notification_handle, notification_resp_handle, callback):
        self.make_request(notification_handle, struct.pack('BB', 1, 0))
        self.set_callback(notification_resp_handle, callback)


    ## =======================================================
    
    
    def handleCurrentCommand(self):
        ##return self.dpgQueue.markCommandHandled()
        oldCommand = self.currentCommand
        self.currentCommand = None
        return oldCommand
        
    @synchronized
    @DisconnectOnException
    def send_dpg_read_command(self, dpgCommandType):
        dpgCommand = DPGCommand.get_read_command(dpgCommandType)
        return self._send_command_repeated(linak_service.Characteristic.DPG, dpgCommand)
    
    @synchronized
    @DisconnectOnException
    def send_dpg_write_command(self, dpgCommandType, data):
        dpgCommand = DPGCommand.get_write_command(dpgCommandType, data)
        return self._send_command_repeated(linak_service.Characteristic.DPG, dpgCommand)
    
    @synchronized
    @DisconnectOnException
    def send_control_command(self, controlCommand):
        return self._send_command_single(linak_service.Characteristic.CONTROL, controlCommand, False)
    
    @synchronized
    @DisconnectOnException
    def send_directional_command(self, directionalCommand):
        return self._send_command_single(linak_service.Characteristic.CTRL1, directionalCommand)
    
    def _send_command_repeated(self, characteristicEnum, commandObj, with_response = True):
        ##self.logger.debug("Waiting for notifications for %s", timeout)
        for rep in range(0, 3):
            self._send_command_single(characteristicEnum, commandObj, with_response)
            ##sleep(0.2)
            if self.currentCommand == None:
                ## command handled -- do not resent again
                return True
            
            self.logger.debug("Did not receive response: %s", rep)
        
        ### here notification callback is already handled
        ##self.logger.debug("Command handled")
        return False
                
    ### if with_response = True then exception will be raised in case of problems
    def _send_command_single(self, characteristicEnum, commandObj, with_response=True):
        self.currentCommand = commandObj
        value = commandObj.wrap_command()
        self.logger.debug("Sending %s: %s to %s w_resp=%s", commandObj, to_hex_string(value), characteristicEnum, with_response)
        return self._write_to_characteristic( characteristicEnum.handle(), value, with_response=with_response)
    
    @synchronized
    @DisconnectOnException
    def subscribe_to_notification_enum(self, characteristicEnum, callback):
        self.logger.debug("Subscribing to %s", characteristicEnum)
        value = struct.pack('BB', 1, 0)
        
        with_response=False
        
        self.logger.debug("Writing value %s:%s to %s w_resp=%s", type(value), to_hex_string(value), characteristicEnum, with_response)
        notificationHandle = characteristicEnum.handle() + 1                                ## +1 is required!
        self._write_to_characteristic( notificationHandle, value, with_response )
                
        notification_resp_handle = characteristicEnum.handle()
        self.set_callback(notification_resp_handle, callback)

    def _write_to_characteristic(self, handle, value, with_response=True):
        succeed = self._write_to_characteristic_raw(handle, value, with_response)
        if succeed == True:
            return succeed
        return self._pull_notifications()

    def _write_to_characteristic_raw(self, handle, value, with_response = True):
        self._conn.writeCharacteristic( handle, value, withResponse=with_response)
        if with_response == True:
            timeout = max(constants.DEFAULT_TIMEOUT, 1)
#             self.logger.debug("Wait for notifications for %s", timeout)
            return self._waitForNotifications(timeout)
        return True

    def _pull_notifications(self):
        """
        Force receiving notifications.
        
        This is workaround for case of not coming (missing) notifications -- just read something from device.
        """
        self.logger.debug("Receive notification timeout - trying to pull notification")
        handle = linak_service.Characteristic.DEVICE_NAME.handle()
        self._conn.readCharacteristic( handle )               ## device name
        timeout = max(constants.DEFAULT_TIMEOUT, 1)
        self._waitForNotifications(timeout)
        return True

    def _is_characteristic_readable(self, handle):
        #TODO: load all characteristics at connection time and cache Characteristic objects
        charList = self._conn.getCharacteristics( startHnd=handle, endHnd=handle )
        if len(charList) != 1:
            self.logger.warning("could not get characteristic")
            return True
        char = charList[0]
        return char.supportsRead()

    @synchronized
    @DisconnectOnException
    def read_characteristic_by_enum(self, characteristicEnum):
        """Read a GATT Characteristic in sync mode."""
        try:
            self.logger.debug("Reading char: %s", characteristicEnum)
#             self.logger.debug("This: %s %s" % (self, self._conn) )
            handleValue = characteristicEnum.handle()
            retVal = self._conn.readCharacteristic(handleValue)
            bytesVal = bytearray(retVal)
            self.logger.debug("Got value [%s]", to_hex_string(bytesVal) )
            return retVal
        except btle.BTLEException as ex:
            self.logger.error("Got exception from bluepy while making a request: %s", ex)
            if ex.estat != 1:
                raise ex
            ## try to read characteristic by uuid
            uuidValue = characteristicEnum.uuid()
            self.logger.debug("trying to access characteristic by uuid: %s", uuidValue)
            charsList = self._conn.getCharacteristics(uuid = uuidValue)
            charLen = len(charsList)
            if charLen != 1:
                raise btle.BTLEException( "unable to get single characteristic object from %s, got objects %s" %(uuidValue, charLen) )
                raise ex
            charObject = charsList[0] 
            return charObject.read()
        
    @synchronized
    @DisconnectOnException
    def read_characteristic_by_handle(self, characteristicHandle):
        """Read a GATT Characteristic in sync mode."""
        try:
            self.logger.debug("Reading char: %s", hex(characteristicHandle))
            retVal = self._conn.readCharacteristic(characteristicHandle)
            bytesVal = bytearray(retVal)
            self.logger.debug("Got value [%s]", to_hex_string(bytesVal) )
            return retVal
        except btle.BTLEException as ex:
            self.logger.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    @synchronized
    @DisconnectOnException
    def get_characteristic_by_enum(self, characteristicEnum):
        """Read a GATT Characteristic."""
        try:
            uuidValue = characteristicEnum.uuid()
            self.logger.debug("Getting char: %s", characteristicEnum)
#             self.logger.debug("This: %s %s" % (self, self._conn) )
            chList = self._conn.getCharacteristics(uuid = uuidValue)
            if len(chList) != 1:
                self.logger.debug("Got many values - returning None")
                return None
            val = chList[0]
            return val
        except btle.BTLEException as ex:
            self.logger.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    @synchronized
    @DisconnectOnException
    def processNotifications(self):
        if self.isConnected() == False:
            return False
        ##self.logger.error("Starting processing")
        self._waitForNotifications(0.5)
        ##self.logger.error("Leaving processing")
        return True

    def _waitForNotifications(self, timeout):
        return self._conn.waitForNotifications( timeout )

BTLEConnection.logger = _LOGGER.getChild(BTLEConnection.__name__)

