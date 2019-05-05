import time
from coap import coap, coapResource, coapDefines


class WhisperCoapReceiver():

    def __init__(self, path):
        self.socket = coap.coap(udpPort=61620)
        self.socket.addResource(WhisperCoapServer(path))

    def __del__(self):
        self.socket.close()


class WhisperCoapServer(coapResource.coapResource):

    def __init__(self, path):
        super(WhisperCoapServer, self).__init__(path)

    def POST(self, options=[], payload=None):
        print "Received CoAP message"
        print "Payload: " + payload
        time.sleep(0.5)
        return (coapDefines.COAP_RC_2_04_CHANGED, options, None)
