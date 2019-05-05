import threading, time
from coap import coap, coapResource, coapDefines


class WhisperCoapSender(threading.Thread):

    def __init__(self, eui):
        super(WhisperCoapSender, self).__init__()
        self.eui = eui
        self.UDP_PORT = 61619
        self.socket = coap.coap(udpPort=self.UDP_PORT)
        self.running = True

    def get(self, mote_id):
        mote_ip = self.mote_id_to_address(mote_id)
        return self.socket.GET('coap://[{0}]/w'.format(mote_ip))

    def post(self, mote_id, dataToSend):
        mote_ip = self.mote_id_to_address(mote_id)
        self.socket.PUT('coap://[{0}]/w'.format(mote_ip), payload=dataToSend)

    def run(self):
        while self.running: time.sleep(1)

    def join(self, timeout=0):
        self.running = False
        super(WhisperCoapSender, self).join(timeout)

    def mote_id_to_address(self, mote_id):
        address = self.eui[:]
        address[6] = (int(mote_id, 16) & 0xff00) >> 8
        address[7] = int(mote_id, 16) & 0x00ff

        mote_ip = "bbbb::"
        count = 1
        for byte in address:
            mote_ip += "%02x" % byte
            if (count % 2) == 0:
                mote_ip += ":"
            count += 1

        return address[0:-1]
