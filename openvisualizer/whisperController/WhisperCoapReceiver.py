import time
from coap import coap, coapResource, coapDefines

import WhisperDefines
class WhisperCoapReceiver():

    def __init__(self, path,wcont):
        self.socket = coap.coap(udpPort=61620)
        self.socket.addResource(WhisperCoapServer(path,wcont))

    def __del__(self):
        self.socket.close()


class WhisperCoapServer(coapResource.coapResource):

    def __init__(self, path,wcontroller):
        super(WhisperCoapServer, self).__init__(path)
	self.wc=wcontroller

    def POST(self, options=[], payload=None):
        #print "Received CoAP message"
        #print "Payload: " + ''.join('{:02x}'.format(x) for x in payload)

        if int(payload[0]) == WhisperDefines.WHISPER_COMMAND_DIO:
            print "Received repsonse to dio command: "
            if int(payload[1]) == 0x00:
                print "Success"
            else:
                print "Failed"

        if int(payload[0]) == WhisperDefines.WHISPER_COMMAND_SIXTOP:
            print "Received response to sixtop command "+str(payload)
            print ''.join('{:02x}'.format(x) for x in payload)
            if len(payload) > 2:
                print "List response received"
                # TODO: add parsing of the received cell list
            else:
                if int(payload[1]) == 0x00:
                    print "Success"

		    newCell={}
		    macNodeTx=self.wc.last6PCommand[0]		
		    macNodeRx=self.wc.last6PCommand[1]	
		    ts= self.wc.last6PCommand[2]
		    ch= self.wc.last6PCommand[3]
		    newCell['ch']= int(ch)
		    newCell['tslot']=int(ts)
		    newCell['type']="DEDICATED"
		    newCell['rxNode']=macNodeRx
		    newCell['txNode']=macNodeTx

		    if macNodeTx not in self.wc.cellsToBeSent.keys():
		    	self.wc.cellsToBeSent[macNodeTx]={}
		    self.wc.cellsToBeSent[macNodeTx][ts]=newCell
		    self.wc.last6PCommand=[]

                else:
                    print "Failed"

        if int(payload[0]) == WhisperDefines.WHISPER_COMMAND_NEIGHBOURS:
            print "Received response to get neighbour command"

	    hexval="0x{:02x}".format(int(payload[1]))
	    wid=str(hexval.split("x")[1])	
		
	    hexval="0x{:02x}".format(int(payload[2]))
	    wid=wid+":"+str(hexval.split("x")[1])

            whisper_node_id = (payload[1] << 8) | payload[2]

	    print wid
	    for m in self.wc.nodes.keys():
		shortMac=str(m.split(':')[4])+":"+str(m.split(':')[5])
		if shortMac == wid:
			longWhisperMac=m
			break
	    print longWhisperMac

	    for a in self.wc.nodes.keys():
		 if a==self.wc.nodes[longWhisperMac]['macParent']:
			parentOfWhisperNode=a
			break

	    print parentOfWhisperNode

	    simpleIdparentOfWhisperNode=str(parentOfWhisperNode.split(':')[4])+":"+str(parentOfWhisperNode.split(':')[5])

	    print simpleIdparentOfWhisperNode

	    lnodes=[]

	    print self.wc.topology.getNodes()

	    for val in self.wc.topology.getNodes():
		lnodes.append(val['simpleID'])

	    print lnodes


            neigbours = []
            i = 3
            while i < len(payload):
                neigbours.append((payload[i] << 8) | payload[i + 1])
		
		hexval="0x{:02x}".format(payload[i])
		sval=str(hexval.split("x")[1])	
		
		hexval="0x{:02x}".format(payload[i + 1])
		sval=sval+":"+str(hexval.split("x")[1])	

		print "Adding Link between "+str(wid)+" and "+str(sval)

		if sval in lnodes:
			if sval == simpleIdparentOfWhisperNode:
				self.wc.topology.addLink(wid, sval, 1, 1)
			else:
				self.wc.topology.addLink(wid, sval, 1, 0)
			
                i += 2

            print "Neighbours of node: " + str(whisper_node_id) + ": "
            for n in neigbours:
                print " * " + str(n)

        return (coapDefines.COAP_RC_2_04_CHANGED, options, None)
