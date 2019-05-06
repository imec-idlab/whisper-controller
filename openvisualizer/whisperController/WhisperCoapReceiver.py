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
        print "Payload: " + ''.join('{:02x}'.format(x) for x in payload)

        if int(payload[0]) == 0x01:
            print "Received repsonse to dio command: "
            if int(payload[1]) == 0x00:
                print "Success"
            else:
                print "Failed"

        if int(payload[0]) == 0x04:
            print "Received response to get neighbour command"

            whisper_node_id = (payload[1] << 8) | payload[2]

            neigbours = []
            i = 3
            while i < len(payload):
                neigbours.append((payload[i] << 8) | payload[i + 1])
                i += 2

            print "Neighbours of node: " + str(whisper_node_id) + ": "
            for n in neigbours:
                print " * " + str(n)


        time.sleep(0.5)
        return (coapDefines.COAP_RC_2_04_CHANGED, options, None)
