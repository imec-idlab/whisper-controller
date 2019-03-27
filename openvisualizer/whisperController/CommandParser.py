import logging
log = logging.getLogger('whisper')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

import threading

from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus      import eventBusClient


class CommandParser(eventBusClient.eventBusClient):

    def __init__(self):
        # log
        log.info("creating instance")

        self.stateLock = threading.Lock()
        self.networkPrefix = None

        # give this thread a name
        self.name = 'whispercontoller_parser'

    def parse(self, data, moteProbeCallback):
        command = data['action'][1:]

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

            moteProbeCallback(dataToSend=dataToSend)

        elif command[0] == "link":
            self.test_link()

        else:
            print "Not the correct parameters."
            return

    def test_link(self):
        print "Testing link between 2 nodes"

        from multiping import MultiPing

        # Create a MultiPing object
        mp = MultiPing(["bbbb::1415:92cc:0:4"])

        # Send the pings to those addresses
        mp.send()

        # With a 1 second timout, wait for responses (may return sooner if all
        # results are received).
        responses, no_responses = mp.receive(1)

        if responses:
            print("reachable: %s" % responses)

        if no_responses:
            print("unreachable: %s" % no_responses)



