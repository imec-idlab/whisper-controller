from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus      import eventBusClient

import WhisperDefines

class WhisperDioParser(eventBusClient.eventBusClient):

    def __init__(self, eui):
        super(WhisperDioParser, self).__init__("WhisperDioParser", [])
        self.eui = eui

    def parse(self, command):
        """
        Parses dio commands: whisper dio <target> <source> <rank>
        :param command: the command
        :return: dataToSend: command parsed to send to whisper nodes
        """
        # Initialize data to send + indicate fake dio command

        if command[0] == "toggle":
            # Toggle propagating dios
            dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, WhisperDefines.WHISPER_COMMNAD_TOGGLE_DIO]
            return dataToSend

        if command[0] == "set_rank":
            dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, WhisperDefines.WHISPER_COMMNAD_SET_RANKTOSEND]

            # target id (16b, so split in 2 bytes)
            [dataToSend.append(i) for i in self.splitBytes(command[1], "hex")]

            # Split rank in 2 bytes
            [dataToSend.append(i) for i in self.splitBytes(command[2])]

            return dataToSend

        dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, WhisperDefines.WHISPER_COMMAND_DIO]

        # target id (16b, so split in 2 bytes)
        [dataToSend.append(i) for i in self.splitBytes(command[0], "hex")]

        # parent id (16b, so split in 2 bytes)
        [dataToSend.append(i) for i in self.splitBytes(command[1], "hex")]

        # Add next hop
        next_hop = self.getNextHop(command[0])
        if next_hop: [dataToSend.append(i) for i in next_hop]
        else: return None

        # Split rank in 2 bytes
        [dataToSend.append(i) for i in self.splitBytes(command[2])]

        print dataToSend
        return dataToSend

    def splitBytes(self, number, mode="dec"):
        bytes = [0x0, 0x0]
        if mode == "hex":
            bytes[0] = (int(number, 16) & 0xff00) >> 8
            bytes[1] = int(number, 16) & 0x00ff
        else:
            bytes[0] = (int(number) & 0xff00) >> 8
            bytes[1] = int(number) & 0x00ff
        return bytes

    def getNextHop(self, targetID):
        # Get next hop from dagroot (using source route)
        target_id = self.splitBytes(targetID, "hex")
        destination_eui = self.eui[:]
        destination_eui[6] = target_id[0]
        destination_eui[7] = target_id[1]

        route = self._dispatchAndGetResult(signal='getSourceRoute', data=destination_eui)
        if len(route) == 0:
            print "No next hop found. Abort."
            return False

        # next hop id (16b, so split in 2 bytes)
        next_hop = [0x0, 0x0]
        next_hop[0] = int(route[-2][-2])
        next_hop[1] = int(route[-2][-1])
        return next_hop