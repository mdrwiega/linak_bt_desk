#
#
#

import threading
from collections import deque



class CommandQueue():

    def __init__(self, connector):
        self.connection = connector
        self.queue = deque()
        self.currentCommand = None
        self.timer = None
        self.retries = 0
        self.lock = threading.RLock()

    def add(self, command):
        with self.lock:
            self.queue.appendleft(command)
            if self.timer != None:
                ## sending thread already running
                return 
            self._sendNextCommand()
    
    def markCommandHandled(self):
        ## indicate that command was handled
        with self.lock:
            oldCommand = self.currentCommand
            self.currentCommand = None
            return oldCommand
    
    def _sendNextCommand(self):
        with self.lock:
            if len(self.queue) < 1:
                return
            self.retries = 0
            self._resendCommand()
    
    def _timeout(self):
        with self.lock:
            if self.currentCommand == None:
                self._sendNextCommand()
                return
            if self.retries < 5:
                self.retries += 1
                self.queue.append(self.currentCommand)
                self._resendCommand()
                return
            ## could not send -- reached max number of retries -- send next command
            self.markCommandHandled()
            self._sendNextCommand()

    def _resendCommand(self):
        self.currentCommand = self.queue.pop()
        self.connection.send_dpg_command_raw( self.currentCommand )
        self.timer = threading.Timer(1, self._timeout, ())
        self.timer.start()                          ## call at most once
    
    