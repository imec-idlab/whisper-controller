from openvisualizer.eventBus      import eventBusClient
import multiping

class WhisperLinkTester(eventBusClient.eventBusClient):

    def __init__(self, eui):
        super(WhisperLinkTester, self).__init__("WhisperLinkTester", [])
        self.eui = eui
        self.linkTestVars = {
            'openLbrCatchPing': False,
            'node1': 0x00,
            'node2': 0x00,
        }

    def testLink(self, node1, node2):
        node1_id = [(int(node1, 16) & 0xff00) >> 8, int(node1, 16) & 0x00ff]
        node1_address = self.getMoteAddress(node1_id)

        node2_id = [(int(node2, 16) & 0xff00) >> 8, int(node2, 16) & 0x00ff]

        self.linkTestVars['node1'] = node1_id
        self.linkTestVars['node2'] = node2_id
        self.linkTestVars['openLbrCatchPing'] = True
        request = multiping.MultiPing([node1_address])
        request.send()

        res = request.receive(1)  # 1 second timeout
        if res[0]:
            print "Ping success."
        else:
            print "Ping failed."

    def getMoteAddress(self, node_id):
        node_address = self.eui[:]
        node_address[6] = node_id[0]
        node_address[7] = node_id[1]

        address = "bbbb::"
        count = 1
        for byte in node_address:
            address += "%02x" % byte
            if (count % 2) == 0:
                address += ":"
            count += 1
        return address[0:-1]

    def getOpenLbrCatchPing(self):
        return self.linkTestVars['openLbrCatchPing']

    def updatePingRequest(self, lowpan):
        self.eui[6] = self.linkTestVars['node2'][0]
        self.eui[7] = self.linkTestVars['node2'][1]

        # Get route to required stop
        route = self._dispatchAndGetResult(signal='getSourceRoute', data=self.eui)
        route.pop()

        dest_eui = self.eui[:]
        dest_eui[6] = self.linkTestVars['node1'][0]
        dest_eui[7] = self.linkTestVars['node2'][1]
        route.insert(0, dest_eui)

        lowpan['route'] = route
        lowpan['nextHop'] = route[-1]
        self.linkTestVars['openLbrCatchPing'] = False

        return lowpan