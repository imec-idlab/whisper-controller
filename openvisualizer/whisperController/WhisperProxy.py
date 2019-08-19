# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import threading

import requests
from requests.auth import HTTPBasicAuth

import time
from flask import Flask, request, json

app = Flask(__name__)

class WhisperProxy():

    def __init__(self, whisperController):

        # log
        print "creating instance of Whisper PROXY"

	self.wController=whisperController

        self.threads = [threading.Thread(target=self._sendReq,args=[self.wController]),threading.Thread(target=self._server_south_band,args=[self.wController])]

        for thread in self.threads:
            thread.setDaemon(True)
            thread.start()


    def _sendReq(self,controller):

	print "Starting _sendReq server "

	url = 'http://localhost:8181/onos/whisper/whisper/setNode'
	
	headers = {'Content-type': 'application/json'}

	while True:
	    time.sleep(0.01)
	    event = controller.queue.get(block=True)
		
	    data_json = json.dumps(event)

	    #print "Sending "+str(data_json)
	    response = requests.post(url, data=data_json, headers=headers,auth=HTTPBasicAuth('onos', 'rocks'))
	    # Get the reply if needed...

	    

    @app.route("/test", methods=['POST'])
    def processMessageFromONOS():
	    print "Received something from REST!"
	    wcontroller=app.config['arg']

	    if request.headers['Content-Type'] == 'text/plain':
		print (request.data)
		return 'OK', 200
	    elif request.headers['Content-Type'] == 'application/json':

		print "Received protocol "+str(request.json['protocol'])+" message type "+str(request.json['message'])
		data_parsed = request.json['data'].replace("\\", "")
		print "Received data "+str(data_parsed)
		if request.json['protocol'] == "onos-whisper-sb":
			if request.json['message'] == "change-parent":	
			
				data_parsed= ""+str(data_parsed)
				newjson = json.loads(data_parsed)
				print "Content is "+str(newjson['target'])+" and "+str(newjson['newparent'])
			
				target=str(newjson['target'])[8:]
				if target not in wcontroller.nodes.keys():
					print "Target node "+str(target)+" does not exist yet"
					return "OK", 200

				newParent=str(newjson['newparent'])[8:]
				oldParent=wcontroller.nodes[target]["macParent"]
				print "Changing parent of node "+str(target)+" from old parent "+str(oldParent)+" to new parent "+str(newParent)

				if oldParent == newParent:
					return "The new parent is already the old parent", 202

				(fail,commandList) = wcontroller.algorithm.parentSwitch(target, oldParent,newParent)		
				print "clist "+str(commandList)
				print "fail "+str(fail)
				if fail==True:
					return "A whisper node is needed", 201

				for c in commandList:

					targetShort=str(c['t'].split(':')[4])+""+str(c['t'].split(':')[5])
					parentShort=str(c['ct'].split(':')[4])+""+str(c['ct'].split(':')[5])

					command=[]
					command.append('dio')
					command.append(targetShort)
					command.append(parentShort)
					command.append(c['rank'])
					if c['type']=='remoteDio':
						command.append('root')	
						print command
						wcontroller.parse(command,wcontroller.OUTPUT_SERIAL_PORT_ROOT)	
						print "Command delivered"				
					else:
						print "DIO mode not supported yet"
					
				print "REST message processed OK"

			if request.json['message'] == "schedule-cell":	
				data_parsed= ""+str(data_parsed)
				newjson = json.loads(data_parsed)
				print "Content is 6P "+str(newjson['operation'])+" "+str(newjson['srcNode'])+" "+str(newjson['dstNode'])+" "+str(newjson['type'])+" "+str(newjson['ts'])+" "+str(newjson['ch'])
			print " Message processed"

		else:
			print str(request.json['protocol'])+" protocol not recognized"
		

		return "OK", 200
	    else:
		return "Unsupported Media Type", 415


    def _server_south_band(self,controller):
	
	print "Starting REST server "
	app.config['arg'] = controller
	app.run(port=9999, debug = False)

