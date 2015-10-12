import sys
import getopt

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.sackMode = sackMode
        self.debug = debug

        # My code
        self.sequence_number = 0
        self.complete = False
        self.next_seq = 0


    # Main sending loop.
    def start(self):
        while not self.complete:
            if self.sequence_number == 0:
                msg = "syn"
                pack = self.make_packet(msg, self.sequence_number, "")
                self.send(pack)
            else:
                data = self.get_data()
                if data == "":
                    msg = "fin"
                    self.complete = True
                else:
                    msg = "dat"

                pack = self.make_packet(msg, self.sequence_number, data)
                self.send(pack)

            response = self.receive(.5)

            msg_type, seqno, reponse_data, checksum = self.split_packet(response)

            if Checksum.validate_checksum(response):
                if int(seqno) == self.sequence_number + 1:
                    self.sequence_number += 1
                else:
                    self.sequence_number = int(seqno)
            


    def get_data(self):
        data = self.infile.read(1400)
        return data


        


        
'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest,port,filename,debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
