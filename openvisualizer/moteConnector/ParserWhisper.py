import logging
log = logging.getLogger('ParserWhisper')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

import struct

from pydispatch import dispatcher
import StackDefines

from ParserException import ParserException
import Parser

class ParserWhisper(Parser.Parser):

    def __init__(self):
        log.info("Whisper parser started.")

    def parseInput(self,input):

        if input[0] == 0x01:
            print "Recieved whisper data frame"

            command = input[1]

            if command == 0x01:
                # Whisper fake dio from root command
                if input[2] == 0:
                    print "Fake DIO succeeded"
                else:
                    print "Fake DIO failed"
            else:
                data = input[1:-1]
                char_data = []
                [char_data.append(chr(data[i])) for i in range(0, len(data))]

                print ''.join(char_data)

        return ('error', input)
