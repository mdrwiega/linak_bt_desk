"""
Taken from python-eq3bt/master/eq3bt/connection.py

A simple wrapper for bluepy's btle.Connection.
Handles Connection duties (reconnecting etc.) transparently.
"""

import logging
import codecs

import struct

from time import sleep

from bluepy import btle

from .command import DPGCommand
import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.constants as constants
from .synchronized import synchronized



_LOGGER = logging.getLogger(__name__)



class BTLEConnection(btle.DefaultDelegate):
    """Representation of a BTLE Connection."""

    def __init__(self, mac):
        """Initialize the connection."""
        btle.DefaultDelegate.__init__(self)

        self._conn = None
        self._mac = mac
        self._callbacks = {}
        self.currentCommand = None
#         self.dpgQueue = CommandQueue(self)


    @synchronized
    def __enter__(self):
        """
        Context manager __enter__ for connecting the device
        :rtype: btle.Peripheral
        :return:
        """
        
        if self._conn != None:
            return self
        
        _LOGGER.debug("Trying to connect to %s", self._mac)
        connected = False
        for _ in range(0,2):
            try:
                self._conn = btle.Peripheral()
                self._conn.withDelegate(self)
                self._conn.connect(self._mac, addrType='random')
                connected = True
            except btle.BTLEException as ex:
                _LOGGER.debug("Unable to connect to the device %s, retrying: %s", self._mac, ex)
                
        if connected == False:
            _LOGGER.error("Connection to %s failed", self._mac)
            raise ConnectionRefusedError("Connection to %s failed" % self._mac)

        _LOGGER.debug("Connected to %s", self._mac)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ### do not disconnect -- otherwise notification callbacks will be lost
        pass
        ## self.disconnect()

    def __del__(self):
        #TODO: make disconnection on CTRL+C
        self.disconnect()

    @synchronized
    def disconnect(self):
        if self._conn:
            self._conn.disconnect()
            self._conn = None

    def handleNotification(self, handle, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        if handle in self._callbacks:
#             _LOGGER.debug("Got notification from %s: %s", linak_service.Characteristic.find(handle), codecs.encode(data, 'hex'))
            self._callbacks[handle](handle, data)
        else:
            _LOGGER.debug("Got notification without callback from %s: %s", linak_service.Characteristic.find(handle), codecs.encode(data, 'hex'))

    @property
    def mac(self):
        """Return the MAC address of the connected device."""
        return self._mac

    def set_callback(self, handle, function):
        """Set the callback for a Notification handle. It will be called with the parameter data, which is binary."""
        self._callbacks[handle] = function

    @synchronized
    def make_request(self, handle, value, timeout=constants.DEFAULT_TIMEOUT, with_response=True):
        """Write a GATT Command without callback - not utf-8."""
        try:
            _LOGGER.debug("Writing request %s to %s w_resp=%s", codecs.encode(value, 'hex'), handle, with_response)
            self._conn.writeCharacteristic(handle, value, withResponse=with_response)
            if timeout:
                _LOGGER.debug("Waiting for notifications for %s", timeout)
                self._conn.waitForNotifications(timeout)
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    @synchronized
    def read_characteristic(self, handle):
        """Read a GATT Characteristic."""
        try:
            _LOGGER.debug("Reading value %s", handle)
            val = self._conn.readCharacteristic(handle)
            bytesVal = bytearray(val)
            _LOGGER.debug("Got value [%s]", " ".join("0x{:X}".format(x) for x in bytesVal) )
            return val
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    def subscribe_to_notification(self, notification_handle, notification_resp_handle, callback):
        self.make_request(notification_handle, struct.pack('BB', 1, 0), with_response=False)
        self.set_callback(notification_resp_handle, callback)

    def dpg_command(self, command_type):
#         ## new way
#         dpgCommandType = DPGCommandType.findType( command_type )
#         if dpgCommandType == None:
#             _LOGGER.error("Could not find command for value=%s", command_type)
#             return
#         self.send_dpg_read_command(dpgCommandType)
        self.currentCommand = command_type
        value = DPGCommand.wrap_read_command(command_type)
        self.make_request(constants.DPG_COMMAND_HANDLE, value)
        ### here notification callback is already handled
        self.currentCommand = None
        sleep(0.2)


    ## =======================================================
    
    
    def handleCurrentCommand(self):
        ##return self.dpgQueue.markCommandHandled()
        oldCommand = self.currentCommand
        self.currentCommand = None
        return oldCommand
        
    @synchronized
    def send_dpg_read_command(self, dpgCommandType):
        dpgCommand = DPGCommand.get_read_command(dpgCommandType)
        return self._send_command_repeated(linak_service.Characteristic.DPG, dpgCommand)
    
    @synchronized
    def send_dpg_write_command(self, dpgCommandType, data):
        dpgCommand = DPGCommand.get_write_command(dpgCommandType, data)
        return self._send_command_repeated(linak_service.Characteristic.DPG, dpgCommand)
    
    @synchronized
    def send_control_command(self, controlCommand):
        self._send_command_single(linak_service.Characteristic.CONTROL, controlCommand, False)
    
    @synchronized
    def send_directional_command(self, directionalCommand):
        self._send_command_single(linak_service.Characteristic.CTRL1, directionalCommand)
    
    def _send_command_repeated(self, characteristicEnum, commandObj, with_response = True):
        self.currentCommand = commandObj
        ##_LOGGER.debug("Waiting for notifications for %s", timeout)
        for rep in range(0, 8):
            self._send_command_single(characteristicEnum, commandObj, with_response)
            ##sleep(0.2)
            if self.currentCommand == None:
                ## command handled -- do not resent again
                return True
            else:
                _LOGGER.debug("Did not receive response: %s", rep)
        ### here notification callback is already handled
        ##_LOGGER.debug("Command handled")
        return False
                
    ### if with_response = True then exception will be raised in case of problems
    def _send_command_single(self, characteristicEnum, commandObj, with_response = True):
        self.currentCommand = commandObj
        value = commandObj.wrap_command()
        _LOGGER.debug("Sending %s: %s to %s w_resp=%s", commandObj, codecs.encode(value, 'hex'), characteristicEnum, with_response)
        self._write_to_characteristic_raw( characteristicEnum.handle(), value, with_response=with_response)

    @synchronized
    def write_to_characteristic_by_enum(self, characteristicEnum, value, with_response = True):
        _LOGGER.debug("Writing value %s to %s w_resp=%s", codecs.encode(value, 'hex'), characteristicEnum, with_response)
        self._write_to_characteristic_raw( characteristicEnum.handle(), value, with_response=with_response )
        if with_response == True:
            timeout = max(constants.DEFAULT_TIMEOUT, 1)
#             _LOGGER.debug("Wait for notifications for %s", timeout)
            succeed = self._conn.waitForNotifications(timeout)
            if succeed == False:
                _LOGGER.error("Waiting for notifications for %s FAILED", timeout)
#             _LOGGER.debug("Waiting done")
            
    def _write_to_characteristic_raw(self,handle, value, with_response = True):
        self._conn.writeCharacteristic( handle, value, withResponse=with_response)
        if with_response == True:
            timeout = max(constants.DEFAULT_TIMEOUT, 1)
#             _LOGGER.debug("Wait for notifications for %s", timeout)
            succeed = self._conn.waitForNotifications(timeout)
            if succeed == False:
                _LOGGER.error("Waiting for notifications for %s FAILED", timeout)
#             _LOGGER.debug("Waiting done")
    
    def subscribe_to_notification_enum(self, characteristicEnum, callback):
        _LOGGER.debug("Subscribing to %s", characteristicEnum)
        value = struct.pack('BB', 1, 0)
        self.write_to_characteristic_by_enum(characteristicEnum, value, False)
        notification_resp_handle = characteristicEnum.handle()
        self.set_callback(notification_resp_handle, callback)

    @synchronized
    def read_characteristic_by_enum(self, characteristicEnum):
        """Read a GATT Characteristic in sync mode."""
        try:
            _LOGGER.debug("Reading char: %s", characteristicEnum)
#             _LOGGER.debug("This: %s %s" % (self, self._conn) )
            handleValue = characteristicEnum.handle()
            retVal = self._conn.readCharacteristic(handleValue)
            bytesVal = bytearray(retVal)
            _LOGGER.debug("Got value [%s]", " ".join("0x{:X}".format(x) for x in bytesVal) )
            return retVal
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    @synchronized
    def get_characteristic_by_enum(self, characteristicEnum):
        """Read a GATT Characteristic."""
        try:
            uuidValue = characteristicEnum.uuid()
            _LOGGER.debug("Getting char: %s", characteristicEnum)
#             _LOGGER.debug("This: %s %s" % (self, self._conn) )
            chList = self._conn.getCharacteristics(uuid = uuidValue)
            if len(chList) != 1:
                _LOGGER.debug("Got many values - returning None")
                return None
            val = chList[0]
            return val
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    @synchronized
    def processNotifications(self):
        ##_LOGGER.error("Starting processing")
        self._conn.waitForNotifications(0.5)
        ##_LOGGER.error("Leaving processing")

