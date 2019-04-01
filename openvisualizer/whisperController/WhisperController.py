import logging
log = logging.getLogger('logger_whisper')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

import threading
from pydispatch import dispatcher

from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus      import eventBusClient


class WhisperController(eventBusClient.eventBusClient):

    def __init__(self, openLbr):
        # log
        log.info("creating whisper controller instance")

        self.stateLock = threading.Lock()
        self.networkPrefix = None
        self.openLbr = openLbr

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
                self.test_link()

            else:
                print "Not the correct parameters."
                return

        except Exception as e:
            print e.message

    def test_link(self):
        print "Testing link between 2 nodes"

        packet = {
            'tf': [],
            'nh': [0x3A], # next header
            'cid': [],
            'hlim': [],
            'src_addr': [0x00, 0x00, 0x00, 0x00, 0, 0, 0, 0x01],
            'dst_addr': [0x14, 0x15, 0x92, 0xCC, 0, 0, 0, 0x04],
            'payload': [0x80, 0x00, 0x40, 0x6c, 0x31, 0x90, 0x00, 0x00, 0xa0, 0x8c, 0xeb, 0x63, 0x8c, 0x28, 0xd7, 0x41]
        }

        route = self._dispatchAndGetResult(signal='getSourceRoute', data=packet['dst_addr'])
        route.pop() # last is root
        packet['route'] = route
        packet['nextHop'] = packet['route'][len(packet['route']) - 1]

        self.dispatch(
            signal='bytesToMesh',
            data=(packet['nextHop'], self.openLbr.reassemble_lowpan(packet)),
        )

    def _sendToMoteProbe(self, serialport, dataToSend):
        dispatcher.send(
            sender=self.name,
            signal='fromMoteConnector@' + serialport,
            data=''.join([chr(c) for c in dataToSend])
        )



