import logging
log = logging.getLogger('logger_whisper')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

import time
from pydispatch import dispatcher
from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus import eventBusClient
from WhisperParser import WhisperParser
from WhisperDioParser import WhisperDioParser
from WhisperSixtopParser import WhisperSixtopParser
from WhisperLinkTesting import WhisperLinkTester
from WhisperCoapSender import WhisperCoapSender
from WhisperCoapReceiver import WhisperCoapReceiver
from WhisperTester import WhisperTester
from SwitchParentAlgorithm import SwitchParentAlgorithm
import WhisperDefines

import json 

import threading
from WhisperTopology import WhisperTopology
from WhisperProxy import WhisperProxy
import openvisualizer.openvisualizer_utils as u
from Queue import Queue


class WhisperController(eventBusClient.eventBusClient):


    #OUTPUT_SERIAL_PORT_ROOT		= "emulated1"
    OUTPUT_SERIAL_PORT_ROOT		= "/dev/ttyUSB0"

    SLOTS_PER_SLOTFRAME			= 101
    ACTIVE_SLOTS			= 1
    NUMCHANS				= 16
		
    ROOT_MAC				= "mac"
    #WHISPERNODE_MAC			= "92:cc:00:00:00:04"
    WHISPERNODE_MAC			= "4b:00:06:13:0a:84"

    WILDCARD  = '*'
    PROTO_WHISPER = 'whisper'

    MINHOPRANKINCREASE			= 256

    _TARGET_INFORMATION_TYPE            = 0x05
    _TRANSIT_INFORMATION_TYPE           = 0x06

    def __init__(self,app):
        super(WhisperController, self).__init__("WhisperController", [])

        #self.eui = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, 0x00, 0x00]
	self.eui = [0x00, 0x12, 0x4b, 0x00, 0x06, 0x13, 0x00, 0x00]

	#self.ipRoot="1415:92cc:0:1"
	self.ipRoot="0012:4b00:0613:0656"

        # give this thread a name
        self.name = 'whisper_controller'

	self.nodes={}
	self.queue = Queue()

	self.app=app

        # create parsers
        self.parser = WhisperParser()
        self.dio_parser = WhisperDioParser(self.eui)
        self.parser.attachSubparser("dio", self.dio_parser.parse)
        self.sixtop_parser = WhisperSixtopParser(self.eui)
        self.parser.attachSubparser("6p", self.sixtop_parser.parse)
	self.last6PCommand=[]
	self.cellsToBeSent={}

        # Whisper link tester
        self.link_tester = WhisperLinkTester(self.eui,self)

	#whisper topology
	self.topology=WhisperTopology(self)

	#whisper switch parent algorithm
	self.algorithm=None

	#whisper proxy
	self.wProxy=WhisperProxy(self)
	self.networkPrefix = None
	self.networkPrefixFormatted = None		

        # CoAP
        self.coap_receiver = WhisperCoapReceiver("/w",self)
        self.coap_sender = WhisperCoapSender(self.eui)

        #self.tester = WhisperTester(self)
        #self.tester.setCommand("dio 3 2 5000 root".split(' '))
        #self.tester.setInterval(10)
        #self.tester.setTimes(5)

	#get network prefix
	eventBusClient.eventBusClient.__init__(
		    self,
		    name                  = 'whisperController',
		    registrations         =  [
			{
		            'sender'      : self.WILDCARD,
		            'signal'      : 'networkPrefixForWhisper',
		            'callback'    : self._networkPrefix_notif_inWhisper,
		        },
		]
	)

	# register for receiving DAOs as well
	self.register(
		sender            = self.WILDCARD,
		signal            = (self.PROTO_WHISPER),
		callback          = self._fromMoteDataLocal_notif_whisper,
	)

	print "Init done"
#	self.stateLock            = threading.Lock()
#	self.threads = [threading.Thread(target=self._monitoring)]

#	for thread in self.threads:
#            thread.setDaemon(True)
#            thread.start()

    def parse(self, command, serialport):
        dataToSend = self.parser.parse(command)
        print command
	print dataToSend
        if not dataToSend:
            if command[0] == "neighbours":
		print "Sending neighbour command"
                # Initialize data to send + indicate fake dio command
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, WhisperDefines.WHISPER_COMMAND_NEIGHBOURS]

            if command[0] == "link_info":
                # Initialize data to send + indicate fake dio command
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, WhisperDefines.WHISPER_COMMAND_LINK_INFO]

            if command[0] == "link":
                self.link_tester.testLink(command[1], command[2])
                return

            if command[0] == "start_test":
                self.tester.start()
                return

            if command[0] == "ping":
                self.link_tester.simplePing(command[1])
                return
	    if command[0] == "start":
		print "Init additional thread to monitor"
		self.stateLock            = threading.Lock()
		self.threads = [threading.Thread(target=self._monitoring)]

		for thread in self.threads:
		    thread.setDaemon(True)
		    thread.start()
	        return

        if dataToSend:
	    print command
            if command[-1] == "root":
                self._sendToMoteProbe(serialport, dataToSend)
                return
            else:
                try:
		    print "Sending CoAP message "+str(command[-1])+" "+str(dataToSend)
                    self.coap_sender.post(command[-1], dataToSend)
                except Exception as e:
                    pass
                
                return
        else:
            print "Whisper command failed."

    def _sendToMoteProbe(self, serialport, dataToSend):
        dispatcher.send(
            sender=self.name,
            signal='fromMoteConnector@' + serialport,
            data=''.join([chr(c) for c in dataToSend])
        )

    def getLinkTester(self):
        return self.link_tester

    def __del__(self):
        self.coap_sender.join()

    def _updateRootSchedule(self):

	print "Updating Root Schedule"

	if self.ipRoot=="1415:92cc:0:1":	#sim mode
		ms = self.app.getMoteState("0001")
	else:
		ms = self.app.getMoteState(self.ipRoot.split(':')[3])
	obj = json.loads(ms.getStateElem(ms.ST_SCHEDULE).toJson('data'))
	for entry in obj:
		if entry['type'] == "2 (RX)":
		    print entry	
		    if entry['neighbor'] != " (anycast)":
		        
			ch=entry['channelOffset']
			ts=entry['slotOffset']

			macBytes=[00,00,00,00,00,00]
			i=0
			for s in entry['neighbor'].split('-')[2:]:
			
			    if i==5:
				macBytes[i]=s.split(' ')[0]
			    else:
				macBytes[i]=s
			    i+=1
			print macBytes
			mac=(':'.join(macBytes))
		
			if mac not in self.cellsToBeSent.keys():
				self.cellsToBeSent[mac]={}
			if ts not in self.cellsToBeSent[mac].keys():
				newCell={}
				newCell['ch']= int(ch)
				newCell['tslot']=int(ts)
				newCell['type']="DEDICATED"
				newCell['rxNode']=self.ROOT_MAC
				newCell['txNode']=mac
				self.cellsToBeSent[mac][ts]=newCell	
		    else:
			print "This is an autonomous cell. It will be addded through the root's neighbor information"		    	
			    
    #used for debug
    def _removeCell(self):
        
	print "Stoping monitoring thread"
	
	#cells received from whisper commands
	print "Before "+str(self.cellsToBeSent)
	print "Before DB "+str(self.nodes)

	for node in self.cellsToBeSent.keys():
		print "Checking old cells for node "+str(node)+" cells: "+str(self.cellsToBeSent[node])
		print "Node "+str(node)+" has cells id DB: "+str(self.nodes[node]["cells"])
		for ts in self.cellsToBeSent[node].keys():
			print "ts "+str(ts)
			if ts=='10':	#for testing
				print "removing from db "+str(self.nodes[node]["cells"][ts]) 
				del self.nodes[node]["cells"][ts]
				print "removing from cells to be sent "+str(self.cellsToBeSent[node][ts]) 
				del self.cellsToBeSent[node][ts]
		
	print "After "+str(self.cellsToBeSent)
	print "After DB "+str(self.nodes)


    def _monitoring(self):
        
	print "Starting monitoring thread"
	time.sleep( 1 )
	print "Monitoring init"
	
	command=[]
	command.append('neighbours')
#	if self.ipRoot=="1415:92cc:0:1":	#sim mode
#		command.append(int(str(self.WHISPERNODE_MAC.split(':')[4])+""+str(self.WHISPERNODE_MAC.split(':')[5])))
#	else:
	command.append(str(self.WHISPERNODE_MAC.split(':')[4])+""+str(self.WHISPERNODE_MAC.split(':')[5]))
	self.parse(command,self.OUTPUT_SERIAL_PORT_ROOT)

	nodeA=False
	nodeB=False
	
	firstLoop=1
	
	while True:

		print "Init loop"
		#example for test link that is not known
		time.sleep( 5 )
		
		#send info about the root
		self._updateRootSchedule()
		self.queue.put(self.nodes[self.ROOT_MAC])
		if firstLoop==1:
			print "Loop! first one"
			
			#we get the ids of the root and the whispernode, we don't need to test these links
			for nodeId in self.nodes.keys():
				if self.nodes[nodeId]['root']==1:
					rootID=self.nodes[nodeId]['mac']
				if self.nodes[nodeId]['isWhisperNode']=="true":
					whisperNodeID=self.nodes[nodeId]['mac']
			print "Whisper node is "+str(whisperNodeID)
			print "Root node is "+str(rootID)
			for nodeId in self.nodes.keys():

				if self.nodes[nodeId]['mac']==rootID or self.nodes[nodeId]['mac']==whisperNodeID: 	#skip the root and the whisper node
					continue
#				if self.nodes[nodeId]['mac'].split(':')[-1]!="84":	#TODO provisional hack for testing only the links for the example
#					continue
		
				for nLinkWith in self.nodes.keys():
					print self.nodes[nLinkWith]['mac']
					if self.nodes[nodeId]['mac']==self.nodes[nLinkWith]['mac']:	#it's me!
						continue

					#TODO provisional hack for testing only the links connecting 84
#					if self.nodes[nLinkWith]['mac'].split(':')[-1]=="39" or self.nodes[nLinkWith]['mac'].split(':')[-1]=="89":
#						continue

					#TODO provisional hack for testing only the links connecting 84
					if self.nodes[nLinkWith]['mac'].split(':')[-1]=="02" or self.nodes[nLinkWith]['mac'].split(':')[-1]=="03":
						continue

					if self.nodes[nodeId]['macParent']==self.nodes[nLinkWith]['mac']:
						#"its my parent"
						continue				
					if self.nodes[nLinkWith]['mac'] == whisperNodeID:
						#"its a wishper node"
						continue
					if self.nodes[nLinkWith]['mac']==self.ROOT_MAC:
						print "Skipping link with root node"
						#"its a root node"
						continue
					if any(d['mac'] == self.nodes[nLinkWith]['mac'] for d in self.nodes[nodeId]['neighbors']):
						#"its already my neighbor"
						continue
					print "It seems that the link "+str(nodeId)+" - "+str(nLinkWith)+" could exist"
					nodeA=str(self.nodes[nodeId]['mac'].split(':')[4])+":"+str(self.nodes[nodeId]['mac'].split(':')[5])
					nodeB=str(self.nodes[nLinkWith]['mac'].split(':')[4])+":"+str(self.nodes[nLinkWith]['mac'].split(':')[5])
					nodeAFull=self.nodes[nodeId]['mac']
					nodeBFull=self.nodes[nLinkWith]['mac']
					break
				if nodeA != False and nodeB != False:
					break  			
			
			
			print "done"
			firstLoop=self._testLink(nodeAFull,nodeBFull )
		time.sleep( 10 )	

    def _testLink(self,nodeA,nodeB):
        '''
        Test the connectivity between two neighbors (non-parent child)
		-	First add a cell between them
		-	Second does a source ping 
		-	Order matters!
        '''

	print "Testing Link between "+str(nodeA)+" and "+str(nodeB)
	
	if nodeA == False or nodeB == False:
		return 1

	#TODO use a valid cell or process the error in case of schedule collision

	if nodeB == str(self.ROOT_MAC.split(':')[4])+":"+str(self.ROOT_MAC.split(':')[5]):
		nB=str(nodeA.split(':')[-2])+""+str(nodeA.split(':')[-1])
		nA=str(nodeB.split(':')[-2])+""+str(nodeB.split(':')[-1])

	else:
		nA=str(nodeA.split(':')[-2])+""+str(nodeA.split(':')[-1])
		nB=str(nodeB.split(':')[-2])+""+str(nodeB.split(':')[-1])


	print "Allocating TX cell between "+str(nA)+" and "+str(nB)	
	#first we allocate a TX cell from a to B
	command=[]
	command.append('6p')
	command.append('add')
#	if self.ipRoot=="1415:92cc:0:2":	#sim mode
#		command.append(str(int(str(nA))))
#		command.append(str(int(str(nB))))
#	else:
	command.append(str(nA))
	command.append(str(nB))
	command.append('TX')
	command.append('cell')
	command.append('10')
	command.append('10')
#	if self.ipRoot=="1415:92cc:0:2":	#sim mode
#		command.append(str(int(str(self.WHISPERNODE_MAC.split(':')[4])+""+str(self.WHISPERNODE_MAC.split(':')[5]))))	#whisper
#	else:
	command.append(str(self.WHISPERNODE_MAC.split(':')[4])+""+str(self.WHISPERNODE_MAC.split(':')[5]))	#whisper
	self.last6PCommand.append(nodeA)	#tx
	self.last6PCommand.append(nodeB)	#rx
	self.last6PCommand.append('10')		#ts
        self.last6PCommand.append('10')		#ch
	self.parse(command,self.OUTPUT_SERIAL_PORT_ROOT)


	time.sleep( 5 )


#	print "Allocating RX cell between "+str(nB)+" and "+str(nA)	
#	#first we allocate a RX cell from b to a
#	command=[]
#	command.append('6p')
#	command.append('add')
##	if self.ipRoot=="1415:92cc:0:1":	#sim mode
##		command.append(str(int(str(nB))))
##		command.append(str(int(str(nA))))
##	else:
#	command.append(str(nB))
#	command.append(str(nA))
#	command.append('RX')
#	command.append('cell')
#	command.append('10')
#	command.append('10')
##	if self.ipRoot=="1415:92cc:0:1":	#sim mode
##		command.append(str(int(str(self.WHISPERNODE_MAC.split(':')[4])+""+str(self.WHISPERNODE_MAC.split(':')[5]))))	#whisper
##	else:
#	command.append(str(self.WHISPERNODE_MAC.split(':')[4])+""+str(self.WHISPERNODE_MAC.split(':')[5]))	#whisper
#	self.parse(command,self.OUTPUT_SERIAL_PORT_ROOT)

	time.sleep( 10 )


	print "Testing link. Pinging to "+str(nB)+" through "+str(nA)
	command=[]
	command.append('link')
#	if self.ipRoot=="1415:92cc:0:1":	#sim mode
#		command.append(str(int(str(nB))))
#		command.append(str(int(str(nA))))
#	else:
	command.append(str(nB))
	command.append(str(nA))	
	self.parse(command,self.OUTPUT_SERIAL_PORT_ROOT)

	return 0

    def _networkPrefix_notif_inWhisper(self,sender,signal,data):
        '''
        Record the network prefix.
        '''
        # store
        self.networkPrefix    = data[:]
	prefixString=""
	for val in self.networkPrefix:
		hexval=hex(val)
		sval=str(hexval.split("x")[1])	
		if sval=="0":
			sval="00"
		prefixString=prefixString+":"+sval

	#remove first colon
	prefixString=prefixString[1:]
	#merge two first bytes
	prefixString=prefixString[:2] + prefixString[3:]
	#in case 00 bytes are present, simplyfy them
	prefixString=prefixString.replace("00:00", "0")
		
	print "------------ Received network prefix: "+str(prefixString)
	self.networkPrefixFormatted = prefixString	
	self._setUpDagRoot(prefixString)
	self.algorithm=SwitchParentAlgorithm(self,self.ROOT_MAC,self.WHISPERNODE_MAC)


    def _fromMoteDataLocal_notif_whisper(self,sender,signal,data):
        '''
        Called when receiving 
        '''  
	#"received DAO"

	if data[1][0]!=0:
		return	#it is not a DAO	
	

	(prefix,src, parents, children)=self._indicateDAO_inWhisper(data)


	if prefix==None or len(parents)==0:
		return

	pdr=1
	macBytes=[00,00,00,00,00,00]

	i=0
	for s in src.split(':')[1:]:

		if len(s)==4:
			macBytes[i]=s[:2]
			macBytes[i+1]=s[2:]
		if len(s)==3:
			macBytes[i]="0"+s[:-2]
			macBytes[i+1]=s[-2:]
		if len(s)==2:
			macBytes[i]="00"
			macBytes[i+1]=s
		if len(s)==1:
			macBytes[i]="00"
			macBytes[i+1]="0"+s
		i=i+2
	
	mac=(':'.join(macBytes))

	j=0
	for s in parents[0][1].split(':')[1:]:
	
		if len(s)==4:
			macBytes[j]=s[:2]
			macBytes[j+1]=s[2:]
		if len(s)==3:
			macBytes[j]="0"+s[:-2]
			macBytes[j+1]=s[-2:]
		if len(s)==2:
			macBytes[j]="00"
			macBytes[j+1]=s
		if len(s)==1:
			macBytes[j]="00"
			macBytes[j+1]="0"+s
		j=j+2

	macparent=(':'.join(macBytes))

	if macparent not in self.nodes.keys():
		#"Parent is not ready"
		return

	if mac not in self.nodes.keys():
	
		

		data = {}

		lastByte=int(mac.split(':')[-1],16)
		secLastByte=int(mac.split(':')[-2],16)
		fakeIpv4="10.10.0"
		print "Adding new node "+str(src)+" with lastbyte "+str(lastByte)		

		data["type"]="networkUpdate"
		data["root"]=0
		data["mac"]=mac
		data["macParent"]=macparent
		data["ipv6"]='{0}:{1}'.format(prefix,src)
		data["ipv4"]='{0}.{1}'.format(fakeIpv4,str(lastByte))
		data["rank"]="256"
		data["neighbors"]=[]
		data["cells"]={}						#neigh type ts ch 
		data["timestamp"]=str(int(round(time.time() * 1000)))
		data["powered"]="false"
		data["latencyASNtoTheRoot"]=0					#TODO
		data["overallQuality"]=1					#TODO
		

		autonomousCell={}
		intVal=(secLastByte*256)+lastByte
		ts= self.ACTIVE_SLOTS + ( intVal % (self.SLOTS_PER_SLOTFRAME-self.ACTIVE_SLOTS))
		autonomousCell['ch']= int(intVal % (self.NUMCHANS))
		autonomousCell['tslot']=int(ts)
		autonomousCell['type']="RX"
		autonomousCell['rxNode']=mac
		autonomousCell['txNode']="FF:FF:FF:FF:FF:FF"

		data["cells"][ts]=autonomousCell

		#calculate expected Rank according to RFC 8180
		rankParent=int(self.nodes[macparent]["rank"])
								
		#only for testing porposes
		rf=1
		sr=0
		sp=(3/pdr)-2
		data["rank"] = rankParent + (rf*sp + sr) * self.MINHOPRANKINCREASE		#estimated aprox value 

		#walk through the tree until the root
		foundRoot=False
		nHops=0
		p=macparent
		while not foundRoot:
			if p==self.ROOT_MAC:
				foundRoot=True
				break
			else:
				p=self.nodes[p]["macParent"]
				nHops+=1

		data["hopsToRoot"]=nHops+1
		wMacLastByte=self.WHISPERNODE_MAC.split(":")[-1]
		if int(lastByte)==int(str(wMacLastByte),16):
			print "This node is a Whisper node "+str(int(lastByte))+" "+str(int(str(wMacLastByte),16))
			data["isWhisperNode"]="true"
		else:
			print "This node is not a Whisper node "+str(int(lastByte))+" "+str(int(str(wMacLastByte),16))
			data["isWhisperNode"]="false"


		self.nodes[mac]=data
		self.topology.addNode(mac,macparent,pdr)
	else:
		if macparent != self.nodes[mac]["macParent"]:
			print "Updating old link with oldparent "+str(self.nodes[mac]["macParent"])
			self.topology.addLink(mac,self.nodes[mac]["macParent"],pdr,0)
			self.nodes[mac]["macParent"]=macparent
			print "Updating new link with new parent"+str(self.nodes[mac]["macParent"])
			self.topology.addLink(mac,macparent,pdr,1)

		if macparent in self.nodes.keys():
		    if mac not in self.nodes[macparent]["neighbors"]:
			self.topology.addLink(macparent,mac,pdr,1)
		if mac in self.nodes.keys():
		    if macparent not in self.nodes[mac]["neighbors"]:
			self.topology.addLink(mac,macparent,pdr,1)

		#cells received from whisper commands
		for node in self.cellsToBeSent.keys():
			print "Checking new cells for node "+str(node)
			if node == mac:
				print "Node "+str(mac)+" has cell "+str(self.cellsToBeSent[mac])
				for ts in self.cellsToBeSent[mac].keys():
					self.nodes[mac]["cells"][ts]=self.cellsToBeSent[mac][ts]

		



	self.topology.writeTopo()
	self.queue.put(self.nodes[mac])

    def _indicateDAO_inWhisper(self,tup):
        '''
        Indicate a new DAO was received.
        
        This function parses the received packet, and if valid, updates the
        information needed to compute source routes.
        '''
        # retrieve source and destination
        try:
            source                = tup[0]
            if len(source)>8: 
                source=source[len(source)-8:]
            dao                   = tup[1]
        except IndexError:
            #log.info("DAO too short ({0} bytes), no space for destination and source".format(len(dao)))
            return
           
        # retrieve DAO header
        dao_header                = {}
        dao_transit_information   = {}
        dao_target_information    = {}
        
        try:
            # RPL header
            dao_header['RPL_InstanceID']    = dao[0]
            dao_header['RPL_flags']         = dao[1]
            dao_header['RPL_Reserved']      = dao[2]
            dao_header['RPL_DAO_Sequence']  = dao[3]
            # DODAGID
            dao_header['DODAGID']           = dao[4:20]
           
            dao                             = dao[20:]
            # retrieve transit information header and parents
            parents                         = []
            children                        = []
                          
            while len(dao)>0:
                if   dao[0]==self._TRANSIT_INFORMATION_TYPE: 
                    # transit information option
                    dao_transit_information['Transit_information_type']             = dao[0]
                    dao_transit_information['Transit_information_length']           = dao[1]
                    dao_transit_information['Transit_information_flags']            = dao[2]
                    dao_transit_information['Transit_information_path_control']     = dao[3]
                    dao_transit_information['Transit_information_path_sequence']    = dao[4]
                    dao_transit_information['Transit_information_path_lifetime']    = dao[5]
                    # address of the parent
                    prefix        =  dao[6:14]
                    parents      += [dao[14:22]]
                    dao           = dao[22:]
                elif dao[0]==self._TARGET_INFORMATION_TYPE:
                    dao_target_information['Target_information_type']               = dao[0]
                    dao_target_information['Target_information_length']             = dao[1]
                    dao_target_information['Target_information_flags']              = dao[2]
                    dao_target_information['Target_information_prefix_length']      = dao[3]
                    # address of the child
                    prefix        =  dao[4:12]
                    children     += [dao[12:20]]
                    dao           = dao[20:]
                else:
                    #log.info("DAO with wrong Option {0}. Neither Transit nor Target.".format(dao[0]))
                    return (None,None,None,None)
        except IndexError:
            #log.info("DAO too short ({0} bytes), no space for DAO header".format(len(dao)))
            return

	src='{0}:{1}'.format(u.formatIPv6Addr(self.networkPrefix),u.formatIPv6Addr(source))
	output_parents = []
	for p in parents:
        	output_parents.append([u.formatIPv6Addr(self.networkPrefix),u.formatIPv6Addr(p)])
	output_children = []
        for c in children:
            output_children.append([u.formatIPv6Addr(self.networkPrefix),u.formatIPv6Addr(p)])

	return (u.formatIPv6Addr(self.networkPrefix),u.formatIPv6Addr(source),output_parents,output_children)

    def _setUpDagRoot(self,prefix):      
	'''
	Normally should only be called once
	'''

        #TODO to be updated with address of the root node
	
	src=self.ipRoot
	parents="false"
	children=[]
  
	data = {}

	macBytes=[00,00,00,00,00,00]
	i=0
	for s in src.split(':')[1:]:
		if len(s)==4:
			macBytes[i]=s[:2]
			macBytes[i+1]=s[2:]
		if len(s)==3:
			macBytes[i]="0"+s[:-2]
			macBytes[i+1]=s[-2:]
		if len(s)==2:
			macBytes[i]="00"
			macBytes[i+1]=s
		if len(s)==1:
			macBytes[i]="00"
			macBytes[i+1]="0"+s
		i=i+2
	mac=(':'.join(macBytes))

	self.ROOT_MAC=mac

	lastByte=int(mac.split(':')[-1],16)
	secLastByte=int(mac.split(':')[-2],16)
	fakeIpv4="10.10.0"

	#this is a wired link
	pdr=1

	data["type"]="networkUpdate"
	data["root"]=1
	data["isWhisperNode"]="false"
	data["mac"]=mac
	data["macParent"]="false"
	data["ipv6"]='{0}:{1}'.format(prefix,src)
	data["ipv4"]='{0}.{1}'.format(fakeIpv4,str(lastByte))
	data["rank"]="256"
	data["neighbors"]=[]
	data["cells"]={}
	data["timestamp"]=str(int(round(time.time() * 1000)))
	data["powered"]="true"
	data["latencyASNtoTheRoot"]=0
	data["hopsToRoot"]=0
	data["overallQuality"]=1

	minimalCell={}
	minimalCell['ch']=0
	minimalCell['tslot']=0
	minimalCell['type']="SHARED"
	minimalCell['rxNode']="FF:FF:FF:FF:FF:FF"
	minimalCell['txNode']="FF:FF:FF:FF:FF:FF"

	data["cells"][0]=minimalCell


	autonomousCell={}
	intVal=(secLastByte*256)+lastByte
	ts= self.ACTIVE_SLOTS + ( intVal % (self.SLOTS_PER_SLOTFRAME-self.ACTIVE_SLOTS))
	autonomousCell['ch']= int(intVal % (self.NUMCHANS))
	autonomousCell['tslot']=int(ts)
	autonomousCell['type']="RX"
	autonomousCell['rxNode']=mac
	autonomousCell['txNode']="FF:FF:FF:FF:FF:FF"

	data["cells"][ts]=autonomousCell

	self.queue.put(data)
	self.topology.addNode(mac,False,False)
	self.nodes[mac]=data
