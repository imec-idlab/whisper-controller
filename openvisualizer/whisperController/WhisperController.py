import logging
log = logging.getLogger('logger_whisper')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

import threading
import multiping
from pydispatch import dispatcher

from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus      import eventBusClient

from coap import coap


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

        # Open CoAP socket
        UDPPORT = 61618
        self.c = coap.coap(udpPort=UDPPORT)

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
                destination_eui = self.eui[:]
                destination_eui[6] = target_id[0]
                destination_eui[7] = target_id[1]

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

                print dataToSend

                if len(command) > 4:
                    coap_target = self.eui[:]
                    coap_target[6] = (int(command[4], 16) & 0xff00) >> 8
                    coap_target[7] = int(command[4], 16) & 0x00ff

                    mote_ip = "bbbb::"
                    count = 1
                    for byte in coap_target:
                        mote_ip += "%02x" % byte
                        if (count % 2) == 0:
                            mote_ip += ":"
                        count += 1

                    self.c.PUT('coap://[{0}]/w'.format(mote_ip[0:-1]), payload=dataToSend)
                else:
                    self._sendToMoteProbe(serialport, dataToSend)

            elif command[0] == "6p":
                # Initialize data to send
                dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, 0x02]

                command_parsed = False
                if command[1] == "add":
                    command_parsed = True
                    dataToSend.append(0x01)  # indicate whisper 6p add request

                    # add target
                    [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]

                    # add source
                    [dataToSend.append(i) for i in self.splitBytes(command[3], "hex")]

                    if command[4] == "TX": dataToSend.append(0x01)
                    elif command[4] == "RX": dataToSend.append(0x02)
                    elif command[4] == "TXRX": dataToSend.append(0x04)
                    else:
                        print("Not a valid cell type, aborted.")
                        return

                    if int(command[5]) <= 255:
                        dataToSend.append(int(command[5]))
                    else:
                        print "Invalid seqNum, command aborted."
                        return

                    if command[6] == "no_cell":
                        dataToSend.append(0x00) # indicate a specified cell is comming

                    elif command[6] == "cell":
                        dataToSend.append(0x01)

                        if 0 <= int(command[7]) <= 101:
                            [dataToSend.append(i) for i in self.splitBytes(command[7])]
                        else:
                            print "Not a valid slot offset, aborted."
                            return

                        if 0 <= int(command[8]) <= 15:
                            [dataToSend.append(i) for i in self.splitBytes(command[8])]
                        else:
                            print "Not a valid channel, aborted."
                            return
                    else:
                        dataToSend.append(0x02) # indicate random cell

                elif command[1] == "delete":
                    command_parsed = True
                    dataToSend.append(0x02)  # indicate whisper 6p add request

                    # add target
                    [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]

                    # add source
                    [dataToSend.append(i) for i in self.splitBytes(command[3], "hex")]

                    if command[4] == "TX":
                        dataToSend.append(0x01)
                    elif command[4] == "RX":
                        dataToSend.append(0x02)
                    elif command[4] == "TXRX":
                        dataToSend.append(0x04)
                    else:
                        print("Not a valid cell type, aborted.")
                        return

                    if int(command[5]) <= 255:
                        dataToSend.append(int(command[5]))
                    else:
                        print "Invalid seqNum, command aborted."
                        return

                    if command[6] == "no_cell":
                        dataToSend.append(0x00)  # indicate a specified cell is comming

                    elif command[6] == "cell":
                        dataToSend.append(0x01)

                        if 0 <= int(command[7]) <= 101:
                            [dataToSend.append(i) for i in self.splitBytes(command[7])]
                        else:
                            print "Not a valid slot offset, aborted."
                            return

                        if 0 <= int(command[8]) <= 15:
                            [dataToSend.append(i) for i in self.splitBytes(command[8])]
                        else:
                            print "Not a valid channel, aborted."
                            return
                    else:
                        dataToSend.append(0x02)  # indicate random cell

                elif command[1] == "list":
                    command_parsed = True
                    dataToSend.append(0x05)  # indicate whisper 6p list request
                    [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]
                    [dataToSend.append(i) for i in self.splitBytes(command[3], "hex")]

                    if command[4] == "TX":
                        dataToSend.append(0x01)
                    elif command[4] == "RX":
                        dataToSend.append(0x02)
                    elif command[4] == "TXRX":
                        dataToSend.append(0x04)
                    else:
                        print("Not a valid cell type, aborted.")
                        return

                    if int(command[5]) <= 255:
                        dataToSend.append(int(command[5]))
                    else:
                        print "Invalid seqNum, command aborted."
                        return

                    [dataToSend.append(i) for i in self.splitBytes(command[6])] # max nr of cells
                    [dataToSend.append(i) for i in self.splitBytes(command[7])] # listing offset

                elif command[1] == "clear":
                    command_parsed = True
                    dataToSend.append(0x07)  # indicate whisper 6p list request
                    [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]
                    [dataToSend.append(i) for i in self.splitBytes(command[3], "hex")]
                    dataToSend.append(0x01)  # send celloption 0x01 (TX) does not matter
                else:
                    print "Please specify a correct 6P command."

                if command_parsed:
                    coap_target = self.eui[:]
                    coap_target[6] = (int(command[-1], 16) & 0xff00) >> 8
                    coap_target[7] = int(command[-1], 16) & 0x00ff

                    mote_ip = "bbbb::"
                    count = 1
                    for byte in coap_target:
                        mote_ip += "%02x" % byte
                        if (count % 2) == 0:
                            mote_ip += ":"
                        count += 1

                    self.c.PUT('coap://[{0}]/w'.format(mote_ip[0:-1], confirmable=False), payload=dataToSend)

            elif command[0] == "link":
                first = self.eui[:]
                first[6] = (int(command[1], 16) & 0xff00) >> 8
                first[7] = int(command[1], 16) & 0x00ff

                first_mote_ip = "bbbb::"
                count = 1
                for byte in first:
                    first_mote_ip += "%02x" % byte
                    if (count % 2) == 0:
                        first_mote_ip += ":"
                    count += 1
                first_mote_ip = first_mote_ip[0:-1]
                first_id = [first[6], first[7]]

                second = self.eui[:]
                second[6] = (int(command[2], 16) & 0xff00) >> 8
                second[7] = int(command[2], 16) & 0x00ff

                second_mote_ip = "bbbb::"
                count = 1
                for byte in first:
                    second_mote_ip += "%02x" % byte
                    if (count % 2) == 0:
                        second_mote_ip += ":"
                    count += 1
                second_mote_ip = second_mote_ip[0:-1]
                second_id = [second[6], second[7]]

                self.linkTestVars['ping_destination'] = first_id
                self.linkTestVars['ping_route_stop'] = second_id
                self.linkTestVars['openLbrCatchPing'] = True
                request = multiping.MultiPing([first_mote_ip])
                request.send()

                res = request.receive(1) # 1 second timeout
                if res[0]: print "Ping success."
                else: print "Ping failed."

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

    def splitBytes(self, number, mode="dec"):
        bytes = [0x0, 0x0]
        if mode == "hex":
            bytes[0] = (int(number, 16) & 0xff00) >> 8
            bytes[1] = int(number, 16) & 0x00ff
        else:
            bytes[0] = (int(number) & 0xff00) >> 8
            bytes[1] = int(number) & 0x00ff
        return bytes


    def getOpenLbrCatchPing(self):
        return self.linkTestVars['openLbrCatchPing']

    def updatePingRequest(self, lowpan):
        self.eui[6] = self.linkTestVars['ping_route_stop'][0]
        self.eui[7] = self.linkTestVars['ping_route_stop'][1]

        # Get route to required stop
        route = self._dispatchAndGetResult(signal='getSourceRoute', data=self.eui)
        route.pop()

        dest_eui = self.eui[:]
        dest_eui[6] = self.linkTestVars['ping_destination'][0]
        dest_eui[7] = self.linkTestVars['ping_destination'][1]
        route.insert(0, dest_eui)

        lowpan['route'] = route
        lowpan['nextHop'] = route[-1]
        self.linkTestVars['openLbrCatchPing'] = False

        return lowpan

    def _sendToMoteProbe(self, serialport, dataToSend):
        dispatcher.send(
            sender=self.name,
            signal='fromMoteConnector@' + serialport,
            data=''.join([chr(c) for c in dataToSend])
        )

    def __del__(self):
        self.c.close()




