from openvisualizer.eventBus      import eventBusClient
import multiping
import time

class WhisperLinkTester(eventBusClient.eventBusClient):

    def __init__(self, eui,wc):
        super(WhisperLinkTester, self).__init__("WhisperLinkTester", [])
        self.eui = eui
        self.linkTestVars = {
            'openLbrCatchPing': False,
            'node1': 0x00,
            'node2': 0x00,
        }
	self.wcontroller=wc

    def testLink(self, node1, node2):
	lonMacA=0
	lonMacB=0
        node1_id = [(int(node1, 16) & 0xff00) >> 8, int(node1, 16) & 0x00ff]
        node1_address = self.getMoteAddress(node1_id)

        node2_id = [(int(node2, 16) & 0xff00) >> 8, int(node2, 16) & 0x00ff]
	node2_address = self.getMoteAddress(node2_id)

	print "Testing Link between "+str(node1_id)+" and "+str(node2_id)

	nodeA=str("0x{:02x}".format(node1_id[0]).split("x")[1])+":"+str("0x{:02x}".format(node1_id[1]).split("x")[1])
	nodeB=str("0x{:02x}".format(node2_id[0]).split("x")[1])+":"+str("0x{:02x}".format(node2_id[1]).split("x")[1])

        self.linkTestVars['node1'] = node1_id
        self.linkTestVars['node2'] = node2_id
	self.linkTestVars['openLbrCatchPing'] = True

	print "Pinging node "+str([node1_address])
	print "through node "+str([node2_address])
        request = multiping.MultiPing([node1_address])
        request.send()
	time.sleep( 5 )
        res = request.receive(3)  # 1 second timeout
        if res[0]:
            print "Ping success."
	    for m in self.wcontroller.topology.topology['nodes']:
		print "searching lonMacA "+str(m)
		if m['simpleID']==nodeA:
		    lonMacA=m['id']
		    print "lonMacA "+str(lonMacA)
		    break
	    for m in self.wcontroller.topology.topology['nodes']:
		print "searching lonMacB "+str(m)
		if m['simpleID']==nodeB:
		    lonMacB=m['id']
		    print "lonMacB "+str(lonMacB)
		    break
	    if lonMacA!=0 and lonMacB!=0:
		    if not any(d['mac'] == lonMacB for d in self.wcontroller.nodes[lonMacA]['neighbors']):
			print "Adding Link between "+str(nodeA)+" and "+str(nodeB)
		    	self.wcontroller.topology.addLink(lonMacA, lonMacB, 1, 0)
		
	    	    else:
			print "Link between "+str(nodeA)+" and "+str(nodeB)+" already exists"
	    else:
		print "Ping success. But there was an error adding the logical link."
        else:
            print "Ping failed."

    def simplePing(self, node1):

	print "Testing a ping to "+str(node1)
        node1_id = [(int(node1, 16) & 0xff00) >> 8, int(node1, 16) & 0x00ff]
        node1_address = self.getMoteAddress(node1_id)


        self.linkTestVars['node1'] = node1_id
        self.linkTestVars['openLbrCatchPing'] = False

	print "Pinging node "+str([node1_address])
        request = multiping.MultiPing([node1_address])
        request.send()

        res = request.receive(1)  # 1 second timeout
	time.sleep( 5 )
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

	print "eui "+str(self.eui[7])

        # Get route to required stop
        route = self._dispatchAndGetResult(signal='getSourceRoute', data=self.eui)

	if len(route)!=0:	#only if next hop is not the root
		route.pop()
	print "Updating next hop "+str(route)
	dest_eui = self.eui[:]

	dest_eui[6] = self.linkTestVars['node1'][0]
	dest_eui[7] = self.linkTestVars['node1'][1]

	print "dest eui "+str(dest_eui[7])

	route.insert(0, dest_eui)

	print "route is now "+str(route)

	lowpan['route'] = route
	lowpan['nextHop'] = route[-1]
	self.linkTestVars['openLbrCatchPing'] = False

	print "Returning "+str(lowpan)
        return lowpan
