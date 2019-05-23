
import json

class WhisperTopology():
    def __init__(self,wc):

	self.wcontroller=wc
	self.topology={}
	self.topology['connections']=[]
	self.topology['nodes']=[]

    #will only be call together with its parent, isParent is always true
    def addNode(self, nodeId, parentId, pdr):   
        """
        :param nodeId: node to be added
        :param parentId: parent of the node to be added
        :return: boolean
        """
	print "Adding new node "+str(nodeId)
	simpleId=str(nodeId.split(':')[4])+":"+str(nodeId.split(':')[5])
	newNode={"id": nodeId,"simpleID": simpleId}
	if newNode not in self.topology['nodes']:
		#print "Adding new node"		
		self.topology['nodes'].append(newNode)
		if parentId == False:
			print "It is the root node"	
		else:
			self.addLink(nodeId,parentId,pdr, 1)

	else:
		#print "This node already exist. Checking if link with his parent exist"
		self.addLink(nodeId,parentId,pdr, 1)


    def addLink(self, nodeA, nodeB, pdr, isParent):
        """
        :param nodeA: vertex A
        :param nodeB: vertex B
        :return: boolean
        """
	assert len(nodeA.split(':')) == len(nodeB.split(':'))	

	

	if len(nodeA.split(':')) == 2:
		for node in self.topology['nodes']:
			if node['simpleID']==nodeA:
				print "Replacing short ids for long ids "+str((nodeA,node['id']))
				nodeA=node['id']
			if node['simpleID']==nodeB:
				print "Replacing short ids for long ids "+str((nodeB,node['id']))
				nodeB=node['id']
	#print "Tring to adding or update link between "+str(nodeA)+" and "+str(nodeB)			
	found=False
	for l in self.topology['connections']:
		if (l['fromMote'] == str(nodeA) and l['toMote'] == str(nodeB)) or (l['fromMote'] == str(nodeB) and l['toMote'] == str(nodeA)):
			#print "PDR "+str(pdr)+" RPL "+str(isParent)
			#print "PDRl "+str(l['pdr'])+" RPLl "+str(l['rpl'])
			if pdr == int(l['pdr']) and isParent == int(l['rpl']):
				found=True
				break
			if pdr != int(l['pdr']):
				print "PDR will be updated"
				self.topology['connections'].remove(l)
			if isParent != int(l['rpl']):
				print "Parentship between will be updated. Removing old link"				
				self.topology['connections'].remove(l)
			
	
	if not found:	
		link={}
		print "Adding Link between "+str(nodeA)+" and "+str(nodeB)
		link['toMote']=nodeA
		link['fromMote']=nodeB
		link['pdr']=pdr
		link['rpl']=isParent
		self.topology['connections'].append(link)
		print "updating node tables"
#	else:	
#		print "This link already exists with the same properties"
		

	if nodeA in self.wcontroller.nodes.keys():
		#print str(nodeA)+" is already in the keys"
		if not any(d['mac'] == nodeB for d in self.wcontroller.nodes[nodeA]['neighbors']):
			print str(nodeB)+" is not in the neighbor list yet"
			newNeigh={}
			newNeigh['mac']=nodeB
			newNeigh['rank']="65535"								#will be updated later by the controller
			newNeigh['ipv6']='{0}:{1}'.format(self.wcontroller.networkPrefixFormatted,nodeB)
			newNeigh['aveLinkQuality']="1"								#will be updated later by the controller
			self.wcontroller.nodes[nodeA]['neighbors'].append(newNeigh)
			print self.wcontroller.nodes[nodeA]['neighbors']
		
	if nodeB in self.wcontroller.nodes.keys():
		#print str(nodeB)+" is already in the keys"
		if not any(d['mac'] == nodeA for d in self.wcontroller.nodes[nodeB]['neighbors']):
			print str(nodeA)+" is not in the neighbor list yet"
			newNeigh={}
			newNeigh['mac']=nodeA
			newNeigh['rank']="65535"								#will be updated later by the controller
			newNeigh['ipv6']='{0}:{1}'.format(self.wcontroller.networkPrefixFormatted,nodeA)
			newNeigh['aveLinkQuality']="1"								#will be updated later by the controller
			self.wcontroller.nodes[nodeB]['neighbors'].append(newNeigh)
			print self.wcontroller.nodes[nodeB]['neighbors']



    def getLinks(self):
	return self.topology['connections']


    def getNodes(self):
	return self.topology['nodes']


    def printTopo(self):
	print str(self.topology)

    



    def writeTopo(self):
	with open('topo.json', 'w') as fp:
    		json.dump(self.topology, fp)
