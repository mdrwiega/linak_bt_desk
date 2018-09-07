#
#
#

import logging
from time import sleep

from threading import Timer
from threading import Thread, Event, current_thread

import functools

import linak_dpg_bt.constants as constants
##import linak_dpg_bt.linak_service as linak_service
from .datatype.desk_position import DeskPosition
from .datatype.height_speed import HeightSpeed

from .synchronized import synchronized



_LOGGER = logging.getLogger(__name__)



class DeskMover:
    def __init__(self, conn, target):
        self._conn = conn
        self._target = target
        self._running = False
        self._stopTimer = Timer(30, self._stop_move)

    def start(self):
        _LOGGER.debug("Start move to: %d", self._target)

        self._running = True
        self._stopTimer.start()

        with self._conn as conn:
            conn.subscribe_to_notification(constants.REFERENCE_OUTPUT_NOTIFY_HANDLE, constants.REFERENCE_OUTPUT_HANDLE,
                                           self._handle_notification)

            for _ in range(150):
                if self._running:
                    self._send_move_to()
                    sleep(0.2)

    def _handle_notification(self, cHandle, data):
        hs = HeightSpeed.from_bytes(data)

        _LOGGER.debug("Current relative height: %s, speed: %f", hs.height.human_cm, hs.speed.parsed)

        if hs.speed.parsed < 0.001:
            self._stop_move()

    def _send_move_to(self):
        _LOGGER.debug("Sending move to: %d", self._target)
        self._conn.make_request(constants.MOVE_TO_HANDLE, DeskPosition.bytes_from_raw(self._target))

    def _stop_move(self):
        _LOGGER.debug("Move stopped")
        # send stop move
        self._running = False
        self._stopTimer.cancel()



class CommandThread(Thread):
    
    INTERVAL = 0.3
    
    
    def __init__(self, hFunction):
        super(CommandThread, self).__init__(target = self._thread_loop)
        self.daemon = True
        self.hFunction = hFunction
        self.stopEvent = Event()
        
    def stop(self):
        self.stopEvent.set()
        if current_thread() != self:
            ## called from other thread -- join
            self.join()
        
    def _thread_loop(self):
        while not self.stopEvent.is_set():
            if self.hFunction == None:
                _LOGGER.warning( "no handle function defined" )
                break
            self.hFunction()
            self.stopEvent.wait( self.INTERVAL )
        _LOGGER.debug( "thread terminated" )



class DeskMoverThread():

    def __init__(self, device):
        self.device = device
        self.thread = None

    @synchronized
    def moveUp(self):
        _LOGGER.info( "moving up" )
        self.stopMoving()
        self.spawnThread( self._handle_moveUp )
    
    @synchronized    
    def moveDown(self):
        _LOGGER.info( "moving down" )
        self.stopMoving()
        self.spawnThread( self._handle_moveDown )
        
    @synchronized    
    def moveToFav(self, favIndex):
        _LOGGER.info( "moving to fav %s" % (favIndex) )
        self.stopMoving()
        _LOGGER.info( "initializing new thread" )
        favHandler = functools.partial(self._handle_moveToFav, favIndex)
        self.spawnThread( favHandler )

    def stopMoving(self):
        currentThread = self.extractThread()
        if currentThread != None:
            _LOGGER.info( "stopping thread %s" % (currentThread) )
            currentThread.stop()
        _LOGGER.info( "stopping device" )
        self._handle_stop()

    def _handle_moveUp(self):
        self.device.moveUp()

    def _handle_moveDown(self):
        self.device.moveDown()

    def _handle_moveToFav(self, favIndex):
        self.device.moveToFav(favIndex)
        if self.device.current_speed.raw < 1:
            ## stopped moving
            _LOGGER.info( "device stopped" )
            self.stopMoving()

    def _handle_stop(self):
        self.device.stopMoving()

    @synchronized("thread_lock")
    def spawnThread(self, handler):
        self.thread = CommandThread( handler )
        self.thread.start()
        _LOGGER.info( "new thread spawned %s" % (self.thread) )
    
    @synchronized("thread_lock")
    def extractThread(self):
        tmpThread = self.thread
        self.thread = None
        return tmpThread
