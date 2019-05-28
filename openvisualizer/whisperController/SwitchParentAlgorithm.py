import json


class SwitchParentAlgorithm():

    def __init__(self, whisperController,rootmac,whispermac):

        # log
        print "creating instance of Whisper Switch parent Algorithm, rootmac is "+str(rootmac)

	self.MINRANKHOPINCREASE=256
	self.THRESHOLD=512
	self.HIGHRANK=16*self.MINRANKHOPINCREASE

	self.wController=whisperController

	self.rootMAC=rootmac
	self.whisperMAC=whispermac			#TODO manage if there are more than 1 whisper node

	self.nodes={}
	self.data={}


    def parentSwitch(self, targetNode, currentParent, destinationParent):

	print "Starting parentSwitch algorithm"
	self.data = json.load(open("topo.json"))	#read the last instance of the topology

	#create node structure
	for n in self.data['nodes']:
	    self.nodes[n['id']]={
		'id':  n['id'],
		'rank':  256,
		'parent': -1,
		'neighbors': {},
		'children': [],
	    }

	#fill relationship
	for n in self.data['nodes']:

		    for e in self.data['connections']:
			
			if e['pdr'] > 0.5:	#consider only good links
				if n['id'] == e['fromMote']:
					
				    self.nodes[n['id']]['neighbors'][e['toMote']]={}
				    self.nodes[n['id']]['neighbors'][e['toMote']]['etx']=(1/e['pdr'])

				    self.nodes[e['toMote']]['neighbors'][n['id']]={}
				    self.nodes[e['toMote']]['neighbors'][n['id']]['etx']=(1/e['pdr'])

	failure=0
	totalCommands=[]
	totalType1=[]
	totalType2=[]
	w=0


	self._initRanksAndParents()
	self._initRanks()

	for n in self.nodes.items():
		lis2=[]
		lis=n[1]['neighbors'].keys()
		for l in lis:
			lis2.append(l)

	#paths of every node
	P=self._fillPs()

	#heads of the branches
	heads=set([P[b][0] for b in P.keys()])

	I={}
	for h in heads:
		I[h]=0
	neighboursProcessed=0
	needExtraDio=[]
	needWhisperNode=False

#	t='92:cc:00:00:00:03'
#	ct='92:cc:00:00:00:02'
#	dt='92:cc:00:00:00:01'
#	(t,ct,dt)=getRandomTestingNodes(P)
	t=targetNode
	ct=currentParent
	dt=destinationParent

	#constraint nodes
	CN=[]
	#cadidates as parent
	CP={}

	target=[val for val in self.nodes.values() if val['id'] == t][0] 
	new=[val for val in self.nodes.values() if val['id'] == dt][0] 
	old=[val for val in self.nodes.values() if val['id'] == ct][0] 

	print "Change parent of "+str(t)+" from "+str(ct)+" to "+str(dt)

	#parent cadidates
	CP[target['id']]=self._getCPs(target)

	tentativeRankWithDt= target['neighbors'][dt]['tentativeRank']
	tentativeRankWithCt= target['neighbors'][ct]['tentativeRank']
	minRankOfCPdt=self._getCandidatesWithMinRank(self._getCPs(self.nodes[t]))

	#message types
	numType1=0	#remote DIO
	numType2=0	#propagating DIO

	#other than the desired parent
	potentialParents=[n for n in CP[target['id']] if n[1]['tentativeRank'] <= tentativeRankWithDt and n[0] != dt]

	for pp in potentialParents:
		if pp[0] == self.rootMAC:			#skip root node as parent candidate
			potentialParents.remove(pp)
			numType1+=1
			continue
		if t in P[pp[0]]:	#we can remove this potential parent because is a child of t. if we increase te rank in t, his rank will also eventually be increased
			potentialParents.remove(pp)
		if pp[0] == self.whisperMAC:			#skip whisper node as parent candidate
			potentialParents.remove(pp)

	print "Calculating output..."

	#only if there is one or more potential parents (besides the desired parent)
	for n in potentialParents:
			assert n[0]!=self.rootMAC
					
			neighboursProcessed+=1

			#same branch as dt
			if P[n[0]][0]==P[dt][0]:

				if n[1]['tentativeRank'] == tentativeRankWithDt:
						#this node is in the same branch as t and dt. Impossible
						needWhisperNode=True
						break

				else:
					assert n[1]['tentativeRank'] < tentativeRankWithDt
					if P[n[0]][0]==P[t][0]:
						needWhisperNode=True
						break
					else:	
						#this node is in the same branch as dt. could be done in two steps
						#the head of n is unique in CN without counting dt
						if len([ i for i in potentialParents if i[0]!=n[0] and i[0]!=1 and P[i[0]][0]==P[n[0]][0] ])>0:
							needWhisperNode=True
							break
						else:
							#This switch can be done in two steps
							#if comes here is because it has the same rank as dt, it is enough to increase it a bit	
							rankdiff = abs( tentativeRankWithDt - n[1]['tentativeRank']) + 1
		
							#Calculating CN in branch
							impossibleIncreaseRankInBranchConfirmed=False
							stack=[]
							stack.append(ct)
							
							#if it is the root, it wont have any CN
							if ct==self.rootMAC:
								vertex = stack.pop()
							i=0
							while len(stack)!=0:
								i=i+1
								vertex = stack.pop()
								if P[vertex][0] == P[dt][0]:
									impossibleIncreaseRankInBranchConfirmed=True
									for i in heads:
										I[P[i][0]]=0
									needWhisperNode=True
									break
								
								CNsOfTheBranchOfThisNode=[]
								#get all nodes in the bramch of P[vertex][0]
								for nodeInBranch,branch in P.items():
									if branch[0]==P[vertex][0]:
										(cnodes,r) = self._getCandidatesWithMinRank(self._getCPs(self.nodes[nodeInBranch]))
										for (c) in cnodes:
											if abs(self.nodes[nodeInBranch]['rank'] - r + rankdiff) >= self.THRESHOLD:
												if c not in P[n[0]]:
													if nodeInBranch!=t:
														CNsOfTheBranchOfThisNode.append(nodeInBranch)
								currentDiff=0
								#CNS in the branch of this node
								for cn in CNsOfTheBranchOfThisNode:
									(cnodes,r) = self._getCandidatesWithMinRank(self._getCPs(self.nodes[cn]))

									for (c) in cnodes:
										if c!=self.rootMAC:
											if c not in P[vertex]:
											    if I[P[c][0]]==0:
												if c not in stack:
												    stack.append(c)
												    currentDiff=abs(self.nodes[cn]['rank']-self.nodes[c]['rank']-self.MINRANKHOPINCREASE+rankdiff-self.THRESHOLD)

								if I[P[vertex][0]] <= rankdiff:
									I[P[vertex][0]]=rankdiff
								rankdiff=currentDiff

							if not impossibleIncreaseRankInBranchConfirmed:
								needExtraDio.append(n[0])

		

			else:
				assert n[1]['tentativeRank'] <= tentativeRankWithDt
				#if comes here is because it has the same rank as dt, it is enough to increase it a bit	

				impossibleIncreaseRankInBranchConfirmed=False
				stack=[]
				stack.append(n[0])
				rankdiff = abs( tentativeRankWithDt - n[1]['tentativeRank']) + 1

				#check if we can increase this "a bit"
				i=0
				while len(stack)!=0:
					i=i+1
					vertex = stack.pop()

					if P[vertex][0] == P[dt][0]:
						impossibleIncreaseRankInBranchConfirmed=True
						needWhisperNode=True
						for i in heads:
							I[P[i][0]]=0
						break
					CNsOfTheBranchOfThisNode=[]

					for nodeInBranch,branch in P.items():
						if branch[0]==P[vertex][0]:
							(cnodes,r) = self._getCandidatesWithMinRank(self._getCPs(self.nodes[nodeInBranch]))
							for (c) in cnodes:
								if abs(self.nodes[nodeInBranch]['rank'] - r + rankdiff) >= self.THRESHOLD:
									if c not in P[n[0]]:
										if nodeInBranch!=t:
											CNsOfTheBranchOfThisNode.append(nodeInBranch)

					currentDiff=0
					for cn in CNsOfTheBranchOfThisNode:
						(cnodes,r) = self._getCandidatesWithMinRank(self._getCPs(self.nodes[cn]))
						for (c) in cnodes:
							if c!=self.rootMAC:
								if c not in P[vertex]:
									if I[P[c][0]]==0:
										if c not in stack:
											stack.append(c)
											#rank to be added in the next branch
											currentDiff=abs(self.nodes[cn]['rank']-self.nodes[c]['rank']-self.MINRANKHOPINCREASE+rankdiff-self.THRESHOLD)
					if I[P[vertex][0]] <= 0:
						I[P[vertex][0]]=rankdiff

					rankdiff=currentDiff			
			if needWhisperNode:
				break	
	command_list=[]
	message={}

	if not needWhisperNode:
		fail=False
		print "RESULT:"
		if neighboursProcessed==0:
			numType1+=1
			print "Primitive: Send REMOTE DIO from the ROOT to target t="+str(t)+" with rank "+str(self.HIGHRANK)
			message['type']="remoteDio"
			message['rank']=self.HIGHRANK
			message['t']=t
			message['ct']=ct
			message['dt']=dt
			command_list.append(message)
		else:
			if len(needExtraDio)>0:
				numType1+=1
				print "Primitive: Send REMOTE DIO from the ROOT to target t="+str(t)+" with rank "+str(self.HIGHRANK)
		
				for i in heads:
					if I[i]!=0:
						numType2+=1
						print "Primitive: Send PROPAGATING DIO from the ROOT towards branch t="+str(i)+" with rank "+str(I[i])

				for extraDios in needExtraDio:
					numType1+=1
					print "Primitive: Send REMOTE EXTRA DIO from the ROOT to target t="+str(t)+" with rank "+str(self.HIGHRANK)+" this time will pas through "+str(extraDios)
			else:
				numType1+=1
				print "Primitive: Send REMOTE DIO from the ROOT to target t="+str(t)+" with rank "+str(self.HIGHRANK)
				for i in heads:
					if I[i]!=0:
						numType2+=1
						print "Primitive: Send PROPAGATING DIO from the ROOT towards branch t="+str(i)+" with rank "+str(I[i])
	else:
		print "WHISPER NODES ARE NEEDED"
		failure+=1
		fail=True

	#reset nodes dict
	self.nodes={}
	self.data={}

	return (fail,command_list)


    def _initRanks(self):
	for n in self.nodes.values():
		for (neigh, val) in n['neighbors'].items():
		    	self.nodes[n['id']]['neighbors'][neigh]['tentativeRank']=self.nodes[neigh]['rank']+self.nodes[n['id']]['neighbors'][neigh]['etx']*self.MINRANKHOPINCREASE
			#to check stability
			assert n['rank'] <= (self.THRESHOLD + self.nodes[n['id']]['neighbors'][neigh]['tentativeRank'])

	print "Ranks loaded"


    def _initRanksAndParents(self):
	print "Init parentships by rank"
	stack=[]

	stack.append(self.nodes[self.rootMAC])
	i=0

	visited=[]
	visited.append(self.nodes[self.rootMAC]['id'])

	while len(stack) !=0:		
		ver=stack.pop()
		for neigh in ver['neighbors']:
			if neigh in visited:
				continue
			for e in self.data['connections']:
				if( (ver['id'] == e['fromMote'] and neigh == e['toMote']) or ((ver['id'] == e['toMote'] and neigh == e['fromMote'])) ) and e['rpl']==1:
					stack.append(self.nodes[neigh])
					self.nodes[neigh]['parent']=ver['id']
					self.nodes[neigh]['rank']=(1/e['pdr'])*self.MINRANKHOPINCREASE+self.nodes[ver['id']]['rank']
					self.nodes[self.nodes[neigh]['parent']]['children'].append(neigh)	
					visited.append(self.nodes[neigh]['id'])

    #fill the paths from a node to the root
    def _fillPs(self):

	P={}
	for n in self.nodes.values():
		if n['id']==self.rootMAC:
			continue
		i = n
		l=[]
		l.append(i['id'])
		while i['parent'] != self.rootMAC:
			if i['parent']==self.rootMAC:
				break
			p=i['parent']
			i=[val for val in self.nodes.values() if val['id'] == p][0]
		
			l.append(i['id'])
		P[n['id']]=list(reversed(l))
	return P

    #get candidate parents
    def _getCPs(self,node):
	l=[]
	for neigh in node['neighbors'].items():
		if neigh[0] != node['parent']:
			l.append(neigh)
	return l

    #get candidate parents with min rank
    def _getCandidatesWithMinRank(self,candidates):
	minval=999999
	minCands=[]
	
	for c,val in candidates:
		#print (c, val)
		if val['tentativeRank'] < minval:
			minCands=[]
			minval=val['tentativeRank']
			minCands.append(c)
		else:
			if val['tentativeRank'] == minval:
				minCands.append(c)
	return (minCands,minval)

    #Not used for now
    def _getRandomTestingNodes(self,P):
	a=0	#t
	b=0	#ct
	c=0	#dt
	dtNotFound=True
	it=0	
	while dtNotFound:
		a=int(random.uniform(2, len(self.nodes)))
		b=0
		c=0

		if self.nodes[a]['parent']!=0:
			if len(self.nodes[a]['neighbors'])>1:			
				b=self.nodes[a]['parent']
				neighs= [n for n in self.nodes[a]['neighbors'] if (n!=self.nodes[a]['parent'] and self.nodes[n]['parent']!=a)]
				if len(neighs)>0:
					c= neighs[int(random.randint(0, len(neighs)-1))]
				if a!=0 and b!=0 and c!=0:
					if c!=self.rootMAC:
						if a not in P[c]:	#avoiding loops
							dtNotFound=False	
					else:# when ct is the root, can't be loops
						dtNotFound=False
		it+=1
		if it>500:
			assert False
	return (a,b,c)

