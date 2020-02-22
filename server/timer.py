"""A python timer class"""
import time


class Timer:
    def __init__(self, duration):
        self.duration = duration
        self.reset()

    def reset(self):
        self.last_start = self.last_stop = time.time()
        self.running = False

    def start(self):
        self.last_start = time.time() - self.elapsed
        self.running = True
    
    def stop(self):
        self.last_stop = time.time()
        self.running = False
    
    @property
    def remaining(self):
        return self.duration - self.elapsed

    @remaining.setter
    def remaining(self, val):
        # if its a 5 sec timer and you want it to be at 2, then 5-2 or 3 sec should have
        #  elapsed
        self.elapsed = self.duration - val

    @property
    def elapsed(self):
        if self.running:
            return time.time() - self.last_start
        else:
            return self.last_stop - self.last_start
    
    @elapsed.setter
    def elapsed(self, val):
        if self.running:
            # if x sec have elapsed, it was started x seconds ago
            #  same as start except with custom value
            self.last_start = time.time() - val
        else:
            # I could change either last_stop or last_start
            #  so I guess I'll choose start
            # If x seconds have elapsed before last_stop, it was started
            #  x seconds ago
            self.last_start = self.last_stop - val
