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

from .threadcounter import getThreadName



_LOGGER = logging.getLogger(__name__)



class DeskMover:
    
    logger = None
    
    
    def __init__(self, conn, target):
        self._conn = conn
        self._target = target
        self._running = False
        self._stopTimer = Timer(30, self._stop_move)

    def start(self):
        self.logger.debug("Start move to: %d", self._target)

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

        self.logger.debug("Current relative height: %s, speed: %f", hs.height.human_cm, hs.speed.parsed)

        if hs.speed.parsed < 0.001:
            self._stop_move()

    def _send_move_to(self):
        self.logger.debug("Sending move to: %d", self._target)
        self._conn.make_request(constants.MOVE_TO_HANDLE, DeskPosition.bytes_from_raw(self._target))

    def _stop_move(self):
        self.logger.debug("Move stopped")
        # send stop move
        self._running = False
        self._stopTimer.cancel()

DeskMover.logger = _LOGGER.getChild(DeskMover.__name__)


class CommandThread(Thread):
    """Call passed callable in separate thread until stop requested."""
    
    logger = None
    
    INTERVAL = 0.3
    
    
    def __init__(self, hFunction, namePrefix=None):
        threadName = getThreadName(namePrefix)
        super(CommandThread, self).__init__(target=self._thread_loop, name=threadName)
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
                self.logger.warning( "no handle function defined" )
                break
            ret = self.hFunction()
            if ret == False:
                self.logger.warning( "handler thread termination" )
                break
            self.stopEvent.wait( self.INTERVAL )
        self.logger.debug( "thread terminated" )
        
CommandThread.logger = _LOGGER.getChild(CommandThread.__name__)


class DeskMoverThread():
    
    logger = None
    

    def __init__( self, device ):   ## device type: linak_dpg_bt.linak_device.LinakDesk
        self.device = device
        self.thread = None

    @synchronized
    def moveUp(self):
        self.stopMoving()
        self.logger.info( "moving up" )
        self.spawnThread( self._handle_moveUp )
    
    @synchronized    
    def moveDown(self):
        self.stopMoving()
        self.logger.info( "moving down" )
        self.spawnThread( self._handle_moveDown )
        
    @synchronized    
    def moveToTop(self):
        self.stopMoving()
        self.logger.info( "moving top" )
        self.spawnThread( self._handle_moveTop )
        
    @synchronized    
    def moveToBottom(self):
        self.stopMoving()
        self.logger.info( "moving bottom" )
        self.spawnThread( self._handle_moveBottom )
        
    @synchronized    
    def moveToFav(self, favIndex):
        self.stopMoving()
        self.logger.info( "moving to fav %s" % (favIndex) )
        self.logger.info( "initializing new thread" )
        favHandler = functools.partial(self._handle_moveToFav, favIndex)
        self.spawnThread( favHandler )

    def stopMoving(self):
        currentThread = self.extractThread()
        if currentThread != None:
            self.logger.info( "stopping thread %s" % (currentThread) )
            currentThread.stop()
        self.logger.info( "stopping device" )
        self.device.stopMoving()

    @synchronized("thread_lock")
    def spawnThread(self, handler):
        self.thread = CommandThread( handler, namePrefix="DeskMover" )
        self.logger.info( "new thread spawned %s" % (self.thread) )
        self.thread.start()
    
    @synchronized("thread_lock")
    def extractThread(self):
        tmpThread = self.thread
        self.thread = None
        return tmpThread
    
    ## ========== thread actions ==========

    def _handle_moveUp(self):
        return self.device.moveUp()

    def _handle_moveDown(self):
        return self.device.moveDown()
        
    def _handle_moveTop(self):
        return self.device.moveToTop()
        
    def _handle_moveBottom(self):
        return self.device.moveToBottom()

    def _handle_moveToFav(self, favIndex):
        ret = self.device.moveToFav(favIndex)
        if ret == False:
            return False
        if self.device.current_speed.raw < 1:
            ## stopped moving
            self.logger.info( "device stopped" )
            self.stopMoving()
            return False
        return True

DeskMoverThread.logger = _LOGGER.getChild(DeskMoverThread.__name__)

