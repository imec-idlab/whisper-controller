
from coap import coap, coapResource, coapDefines


class WhisperCoapReceiver(coapResource.coapResource):

    def __init__(self, path):
        super(WhisperCoapReceiver, self).__init__(path)
        self.UDP_PORT = 61620

    def POST(self, options=[], payload=None):
        print "Received CoAP message"
        print "Payload: " + payload

        return coapDefines.COAP_RC_2_03_VALID,  options, None


