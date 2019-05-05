
class WhisperParser():
    def __init__(self):
        # Whisper Parser
        self.subparsers = {} # list of keys, and parse callbacks

    def parse(self, command):
        """

        :param command: command to be parsed
        :return: dataToSend
        """
        key = command[0]

        for subparser_key in self.subparsers.keys():
            if subparser_key == key:
                try:
                    return self.subparsers[key](command[1:-1])
                except Exception as e:
                    print e.message
                    print "Error parsing command of type: " + key
                    return None

    def attachSubparser(self, key, callback):
        if not self.subparsers.has_key(key):
            self.subparsers[key] = callback
        else:
            print "A parser with key:" + key + " is already registered with this parser."

    def detachSubparser(self, key):
        del self.subparsers[key]
