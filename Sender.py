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
        self.ack_received_table = {}
        self.window_size = 7
        self.window = []
        self.last_packet_seqno = -1



    # Function to read data in from the file.
    def get_data(self):
        data = self.infile.read(1400)
        return data

    def send_packet(self):
        if self.sequence_number == 0:
            msg = "syn"
            pack = self.make_packet(msg, self.sequence_number, "")
            self.send(pack)
        else:
            # Else if you get data and it's empty - that means the file has been fully sent. Send a fin message to end transmission.
            #while len(self.window) <= self.window_size:
            for seqno in range(self.sequence_number, self.sequence_number+7):
                data = self.get_data()
                if data == "":
                    msg = "fin"
                   # self.complete = True
                    self.last_packet_seqno = seqno
                    pack = self.make_packet(msg, seqno, "")
                    self.window.append(pack)
                    self.send(pack)
                    break
                else:
                    msg = "dat"
                    pack = self.make_packet(msg, seqno, data)
                    self.send(pack)
                    #self.window.append(pack)

            # for pack in self.window:
            #     print pack

            #     self.send(pack)
            #     self.window.remove(pack)

    def process_response(self, response):
        msg_type, seqno, reponse_data, checksum = self.split_packet(response)

        # Add the ACK to ack_received_table
        if msg_type == "ack":
            if seqno in self.ack_received_table:
                self.ack_received_table[seqno] += 1
            else:
                self.ack_received_table[seqno] = 1

        # If the checksum is valid
        if Checksum.validate_checksum(response):
            
            # Fast retransmit
            if self.ack_received_table[seqno] == 4:
                self.sequence_number = int(seqno)

            # If the ack is expecting the next seq number, send it
            elif int(seqno) == self.sequence_number + 1:
                self.sequence_number += 1

            else:
                # A packet was dropped, set our sequence number to the one the receiver expects.
                self.sequence_number = int(seqno)

            self.send_packet()



    # Main sending loop.
    def start(self):

        # While the whole file has not been sent.
        while not self.complete: 
            if self.last_packet_seqno != -1:
                self.complete = True           
            # Wait for ACK from receiver
            response = self.receive(.5)
            if response is not None:
                self.process_response(response)
            elif self.sequence_number == 0:
                self.send_packet()



            




        


        
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
