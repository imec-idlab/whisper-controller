import threading, time

class WhisperTester(threading.Thread):

    def __init__(self, controller):
        super(WhisperTester, self).__init__()
        self.command = ""
        self.interval = 30 # 30 seconds
        self.times = 5 # perform command 5 times
        self.controller = controller

    def setCommand(self, command):
        self.command = command

    def setInterval(self, interval):
        self.interval = interval

    def setTimes(self, times):
        self.times = times

    def run(self):
        for i in range(self.times):
            self.controller.parse(self.command, "emulated1")
            time.sleep(self.interval)
