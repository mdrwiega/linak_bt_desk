"""
Taken from python-eq3bt/master/eq3bt/connection.py

A simple wrapper for bluepy's btle.Connection.
Handles Connection duties (reconnecting etc.) transparently.
"""

import logging
import codecs

import struct
from bluepy import btle

from time import sleep

from .dpg_command import DPGCommand
import linak_dpg_bt.linak_service as linak_service
import linak_dpg_bt.constants as constants


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

    def __enter__(self):
        """
        Context manager __enter__ for connecting the device
        :rtype: btle.Peripheral
        :return:
        """
        
        if self._conn != None:
            return self
        
        self._conn = btle.Peripheral()
        self._conn.withDelegate(self)
        _LOGGER.debug("Trying to connect to %s", self._mac)
        try:
            self._conn.connect(self._mac, addrType='random')
        except btle.BTLEException as ex:
            _LOGGER.debug("Unable to connect to the device %s, retrying: %s", self._mac, ex)
            try:
                self._conn.connect(self._mac, addrType='random')
            except Exception as ex2:
                _LOGGER.error("Second connection try to %s failed: %s", self._mac, ex2)
                raise

        _LOGGER.debug("Connected to %s", self._mac)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ### do not disconnect -- otherwise notification callbacks will be lost
        pass
        ## self.disconnect()

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if self._conn:
            self._conn.disconnect()
            self._conn = None

    def handleNotification(self, handle, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("Got notification from %s: %s", linak_service.Characteristic(handle), codecs.encode(data, 'hex'))
        if handle in self._callbacks:
            self._callbacks[handle](handle, data)
        else:
            _LOGGER.debug("Notification does not have callback")

    @property
    def mac(self):
        """Return the MAC address of the connected device."""
        return self._mac

    def set_callback(self, handle, function):
        """Set the callback for a Notification handle. It will be called with the parameter data, which is binary."""
        self._callbacks[handle] = function

    def make_request(self, handle, value, timeout=constants.DEFAULT_TIMEOUT, with_response=True):
        """Write a GATT Command without callback - not utf-8."""
        try:
            _LOGGER.debug("Writing request %s to %s with with_response=%s", codecs.encode(value, 'hex'), handle, with_response)
            self._conn.writeCharacteristic(handle, value, withResponse=with_response)
            if timeout:
                _LOGGER.debug("Waiting for notifications for %s", timeout)
                self._conn.waitForNotifications(timeout)
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    def read_characteristic(self, handle):
        """Read a GATT Characteristic."""
        try:
             _LOGGER.debug("Reading value %s", handle)
             val = self._conn.readCharacteristic(handle)
             bytes = bytearray(val)
             _LOGGER.debug("Got value [%s]", " ".join("0x{:X}".format(x) for x in bytes) )
             return val
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    def subscribe_to_notification(self, notification_handle, notification_resp_handle, callback):
        self.make_request(notification_handle, struct.pack('BB', 1, 0), with_response=False)
        self.set_callback(notification_resp_handle, callback)

    def dpg_command(self, command_type):
        self.currentCommand = command_type
        value = DPGCommand.wrap_read_command(command_type)
        self.make_request(constants.DPG_COMMAND_HANDLE, value)
        ### here notification callback is already handled
        self.currentCommand = None
        sleep(0.2)


    ## =======================================================
    
    
    def send_dpg_command(self, dpgCommand):
        self.send_command(linak_service.Characteristic.DPG, dpgCommand)
    
    def send_control_command(self, controlCommand):
        self.send_command(linak_service.Characteristic.CONTROL, controlCommand)
    
    def send_directional_command(self, directionalCommand):
        self.send_command(linak_service.Characteristic.CTRL1, directionalCommand)
    
    def send_command(self, characteristicEnum, commandObj, with_response = True):
        self.currentCommand = commandObj
        value = commandObj.wrap_command()
        _LOGGER.debug("Sending command %s[%s] to %s with_response=%s", commandObj, codecs.encode(value, 'hex'), characteristicEnum, with_response)
        self._conn.writeCharacteristic( characteristicEnum.handle(), value, withResponse=with_response)
#         characteristicObj = self.get_characteristic_by_enum(characteristicEnum)
#         characteristicObj.write(value, with_response)
        timeout = max(constants.DEFAULT_TIMEOUT, 1)
        ##_LOGGER.debug("Waiting for notifications for %s", timeout)
        self._conn.waitForNotifications(timeout)
        ### here notification callback is already handled
        ##_LOGGER.debug("Command handled")
        self.currentCommand = None
        sleep(0.2)
    
    def subscribe_to_notification_enum(self, characteristicEnum, callback):
        _LOGGER.debug("Subscribing to %s", characteristicEnum)
        value = struct.pack('BB', 1, 0)
        self.write_to_characteristic_by_enum(characteristicEnum, value, False)
        notification_resp_handle = characteristicEnum.handle()
        self.set_callback(notification_resp_handle, callback)

    def read_characteristic_by_enum(self, characteristicEnum):
        """Read a GATT Characteristic in sync mode."""
        try:
            _LOGGER.debug("Reading char: %s", characteristicEnum)
#             _LOGGER.debug("This: %s %s" % (self, self._conn) )
            handleValue = characteristicEnum.handle()
            retVal = self._conn.readCharacteristic(handleValue)
            bytes = bytearray(retVal)
            _LOGGER.debug("Got value [%s]", " ".join("0x{:X}".format(x) for x in bytes) )
            return retVal
        except btle.BTLEException as ex:
            _LOGGER.error("Got exception from bluepy while making a request: %s", ex)
            raise ex

    def write_to_characteristic_by_enum(self, characteristicEnum, value, with_response = True):
        ##_LOGGER.debug("Writing value %s to %s with with_response=%s", codecs.encode(value, 'hex'), characteristicEnum, with_response)
        self._conn.writeCharacteristic( characteristicEnum.handle(), value, withResponse=with_response)
#         charObj = self.get_characteristic_by_enum( characteristicEnum )
#         charObj.write(value, with_response)
        if with_response == True:
            timeout = max(constants.DEFAULT_TIMEOUT, 1)
            _LOGGER.debug("Waiting for notifications for %s", timeout)
            self._conn.waitForNotifications(timeout)

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

    def waitForNotifications(self):
        self._conn.waitForNotifications(1)
    
    
    