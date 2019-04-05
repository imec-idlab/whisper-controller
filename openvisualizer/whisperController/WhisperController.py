import logging
log = logging.getLogger('logger_whisper')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

import threading
import multiping
from pydispatch import dispatcher

from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus      import eventBusClient


class WhisperController(eventBusClient.eventBusClient):

    def __init__(self):
        # log
        log.info("creating whisper controller instance")

        self.stateLock = threading.Lock()
        self.eui = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, 0x00, 0x00]

        self.linkTestVars = {
            'openLbrCatchPing': False,
            'ping_destination': 0x00,
            'ping_route_stop': 0x00,          # required route stop before going to dest
        }

        # give this thread a name
        self.name = 'whisper_controller'

    def parse(self, command, serialport):
        try:
            if command[0] == "dio":
                print "Fake dio command"

                # Initialize data to send + indicate fake dio command
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, 0x01]

                # target id (16b, so split in 2 bytes)
                target_id = [0x0, 0x0]
                target_id[0] = (int(command[1], 16) & 0xff00) >> 8
                target_id[1] = int(command[1], 16) & 0x00ff
                [dataToSend.append(i) for i in target_id]

                # parent id (16b, so split in 2 bytes)
                parent_id = [0x0, 0x0]
                parent_id[0] = (int(command[2], 16) & 0xff00) >> 8
                parent_id[1] = int(command[2], 16) & 0x00ff
                [dataToSend.append(i) for i in parent_id]

                # Get next hop from dagroot (using source route)
                destination_eui = [0x14, 0x15, 0x92, 0xcc, 0x00, 0x00, target_id[0], target_id[1]]
                # destination_eui = [0x00, 0x12, 0x4b, 0x00, 0x06, 0x13, target_id[0], target_id[1]]

                # Set next hop or target whisper node id
                if len(command) > 3:
                    # whisper node is specified
                    whisper_id = [0x0, 0x0]
                    whisper_id[0] = (int(command[4]) & 0xff00) >> 8
                    whisper_id[1] = int(command[4]) & 0x00ff
                    [dataToSend.append(i) for i in whisper_id]
                else:
                    route = self._dispatchAndGetResult(signal='getSourceRoute', data=destination_eui)
                    if len(route) == 0:
                        print "No next hop found. Abort."
                        return

                    # next hop id (16b, so split in 2 bytes)
                    next_hop = [0x0, 0x0]
                    next_hop[0] = int(route[-2][-2])
                    next_hop[1] = int(route[-2][-1])
                    [dataToSend.append(i) for i in next_hop]

                # Split rank in 2 bytes
                rank = [0x0, 0x0]
                rank[0] = (int(command[3]) & 0xff00) >> 8
                rank[1] = int(command[3]) & 0x00ff
                [dataToSend.append(i) for i in rank]




                self._sendToMoteProbe(serialport, dataToSend)
            elif command[0] == "link":
                self.linkTestVars['ping_destination'] = 0x04
                self.linkTestVars['ping_route_stop'] = 0x03
                self.linkTestVars['openLbrCatchPing'] = True
                request = multiping.MultiPing(["bbbb::1415:92cc:0:4"]) # dest addr doesnt matter here
                request.send()

                res = request.receive(1) # 1 second timeout
                if res[0]: print "Ping success."
                else: print "Ping failed."

                self.linkTestVars['ping_destination'] = 0x03
                self.linkTestVars['ping_route_stop'] = 0x04
                self.linkTestVars['openLbrCatchPing'] = True
                request = multiping.MultiPing(["bbbb::1415:92cc:0:3"])  # dest addr doesnt matter here
                request.send()

                res = request.receive(1)  # 1 second timeout
                if res[0]:
                    print "Ping success."
                else:
                    print "Ping failed."
                self.linkTestVars['openLbrCatchPing'] = False

            elif command[0] == "dis":
                print "Sending fake dis"

                # Initialize data to send + indicate fake dio command
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, 0x03]

                # target id (16b, so split in 2 bytes)
                target_id = [0x0, 0x0]
                target_id[0] = (int(command[1], 16) & 0xff00) >> 8
                target_id[1] = int(command[1], 16) & 0x00ff
                [dataToSend.append(i) for i in target_id]

                self._sendToMoteProbe(serialport, dataToSend)

            else:
                print "Not the correct parameters."
                return

        except Exception as e:
            print e.message

    def getOpenLbrCatchPing(self):
        return self.linkTestVars['openLbrCatchPing']

    def updatePingRequest(self, lowpan):
        self.eui[7] = self.linkTestVars['ping_route_stop']

        # Get route to required stop
        route = self._dispatchAndGetResult(signal='getSourceRoute', data=self.eui)
        print route
        route.pop()

        dest_eui = self.eui[:]
        dest_eui[7] = self.linkTestVars['ping_destination']
        route.insert(0, dest_eui)

        lowpan['route'] = route
        lowpan['nextHop'] = route[-1]
        print "New route: " + str(route)
        self.linkTestVars['openLbrCatchPing'] = False

        import json
        print json.dumps(lowpan)

        return lowpan

    def _sendToMoteProbe(self, serialport, dataToSend):
        dispatcher.send(
            sender=self.name,
            signal='fromMoteConnector@' + serialport,
            data=''.join([chr(c) for c in dataToSend])
        )



