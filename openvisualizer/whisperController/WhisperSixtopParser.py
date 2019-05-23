from openvisualizer.moteConnector import OpenParser
from openvisualizer.eventBus      import eventBusClient

import WhisperDefines

class WhisperSixtopParser(eventBusClient.eventBusClient):

    def __init__(self, eui):
        super(WhisperSixtopParser, self).__init__("WhisperSixtopParser", [])
        self.eui = eui

    def parse(self, command):
        """
        Parses 6p commands: whisper 6p <command> <target> <source> <params>
        :param command: the command
        :return: dataToSend: command parsed to send to whisper nodes
        """

        # Initialize data to send
        dataToSend = [OpenParser.OpenParser.SERFRAME_PC2MOTE_WHISPER, WhisperDefines.WHISPER_COMMAND_SIXTOP]

        if command[0] == "add":
            dataToSend.append(0x01)  # indicate whisper 6p add request

            # add target
            [dataToSend.append(i) for i in self.splitBytes(command[1], "hex")]

            # add source
            [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]

            cellOptions = self.processCellOptions(command[3])
            if cellOptions: dataToSend.append(cellOptions)
            else: return None

            cellInfo = self.processCellInfo(command[4:])
            if cellInfo: [dataToSend.append(i) for i in cellInfo]

        elif command[0] == "delete":
            dataToSend.append(0x02)  # indicate whisper 6p delete request

            # add target
            [dataToSend.append(i) for i in self.splitBytes(command[1], "hex")]

            # add source
            [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]

            cellOptions = self.processCellOptions(command[3])
            if cellOptions:
                dataToSend.append(cellOptions)
            else:
                return None

            cellInfo = self.processCellInfo(command[4:])
            if cellInfo: [dataToSend.append(i) for i in cellInfo]

        elif command[0] == "list":
            dataToSend.append(0x05)  # indicate whisper 6p add request

            # add target
            [dataToSend.append(i) for i in self.splitBytes(command[1], "hex")]

            # add source
            [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]

            cellOptions = self.processCellOptions(command[3])
            if cellOptions:
                dataToSend.append(cellOptions)
            else:
                return None

            [dataToSend.append(i) for i in self.splitBytes(command[4])]  # max nr of cells
            [dataToSend.append(i) for i in self.splitBytes(command[5])]  # listing offset

        elif command[0] == "clear":
            dataToSend.append(0x07)  # indicate whisper 6p clear request
            # add target
            [dataToSend.append(i) for i in self.splitBytes(command[1], "hex")]
            # add source
            [dataToSend.append(i) for i in self.splitBytes(command[2], "hex")]

        else:
            print "Please specify a correct 6P command."
            return None

        return dataToSend

    def processCellInfo(self, cellInfo):
        result = []
        if cellInfo[0] == "cell":
            result.append(0x01)

            if 0 <= int(cellInfo[1]) <= 101:
                [result.append(i) for i in self.splitBytes(cellInfo[1])]
            else:
                print "Not a valid slot offset, aborted."
                return False

            if 0 <= int(cellInfo[2]) <= 15:
                [result.append(i) for i in self.splitBytes(cellInfo[2])]
            else:
                print "Not a valid channel, aborted."
                return False
        elif cellInfo[0] == "random":
            result.append(0x02)  # indicate random cell
        else:
            print "Not a valid cell definition, abort."
            return False
        return result

    def processCellOptions(self, cellType):
        if cellType == "RX":
            return 0x01
        elif cellType == "TX":
            return 0x02
        elif cellType == "TXRX":
            return 0x04
        else:
            print("Not a valid cell type, aborted.")
            return False

    def splitBytes(self, number, mode="dec"):
        bytes = [0x0, 0x0]
        if mode == "hex":
            bytes[0] = (int(number, 16) & 0xff00) >> 8
            bytes[1] = int(number, 16) & 0x00ff
        else:
            bytes[0] = (int(number) & 0xff00) >> 8
            bytes[1] = int(number) & 0x00ff
        return bytes
