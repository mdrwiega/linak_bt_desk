'''
Implementation of method '@synchronized' decorator. it reflects functionality
of 'synchronized' keyword from Java language.
It accepts one optional argument -- name of lock field declared within object.

Usage examples:

    @synchronized
    def send_dpg_write_command(self, dpgCommandType, data):
        pass
        
    @synchronized()
    def send_dpg_write_command(self, dpgCommandType, data):
        pass

    @synchronized("myLock")
    def send_dpg_write_command(self, dpgCommandType, data):
        pass

'''


import threading



##
## Definition of function decorator
##
def synchronized_with_arg(lock_name = "_methods_lock"):
      
    def decorator(method):
        def synced_method(self, *args, **kws):
            lock = None
            if hasattr(self, lock_name) == False:
                lock = threading.RLock()
                setattr(self, lock_name, lock)
            else:
                lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)
        return synced_method

    return decorator
    
def synchronized(lock_name="_methods_lock"):
    if callable(lock_name):
        ### lock_name contains function to call
        return synchronized_with_arg("_methods_lock")(lock_name)
    else:
        return synchronized_with_arg(lock_name)

    