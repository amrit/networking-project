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
        self.window = []
        self.fin_seqno = None
        self.confirmed_packets = {}
        self.sent_packets = {}
        self.packets = {}




    def make_packets(self):
        seqno = 1
        while True:
            try:
                data = self.infile.read(1400)
                if data == "":
                    break
                self.packets[seqno] = data
                seqno += 1
            except EOFError:
                break
        self.total_packets = len(self.packets.keys())

    def send_packet(self, retransmit=False):
        if self.sequence_number == 0:
            msg = "syn"
            pack = self.make_packet(msg, self.sequence_number, "")
            self.packets[0] = pack
            print "SENDING PACKET " + str(self.sequence_number)
            self.send(pack)
        else:
            for seqno in range(self.sequence_number, self.sequence_number+7):

                if seqno < self.total_packets+2:

                    if (seqno == self.total_packets+1) and (seqno not in self.sent_packets or retransmit):
                        msg = "fin"
                        pack = self.make_packet(msg, seqno, "")
                        print "SENDING FIN PACKET " + str(seqno)
                        self.fin_seqno = seqno
                        self.sent_packets[seqno] = pack
                        self.send(pack)
                        break
                    else:
                        if seqno not in self.sent_packets or retransmit:
                            msg = "dat"
                            pack = self.make_packet(msg, seqno, self.packets[seqno])
                            print "SENDING PACKET " + str(seqno)
                            self.sent_packets[seqno] = pack
                            self.send(pack)



    def process_response(self, response):
        #print response
        msg_type, seqno, reponse_data, checksum = self.split_packet(response)


        # If the checksum is valid
        if Checksum.validate_checksum(response):

            if seqno in self.ack_received_table:
                self.ack_received_table[seqno] += 1
                print self.packets.keys()
                self.send(self.packets[int(seqno)])
            else:
                self.ack_received_table[seqno] = 1
            
            # Fast retransmit
            if self.ack_received_table[seqno] == 4:
                #self.sequence_number = int(seqno)
                self.send(self.packets[int(seqno)])

            # Add this sequence number to acks received
            print "RECEIVED ACK " + str(seqno)

            if int(seqno) == (self.total_packets + 2):
                print "COMPLETE"
                self.complete = True

            # If the ack is expecting the next seq number, send it
            elif int(seqno) == self.sequence_number + 1:
                self.confirmed_packets[self.sequence_number]  = self.packets[self.sequence_number]
                self.sequence_number += 1
                self.send_packet()

            else:
                # A packet was dropped, set our sequence number to the one the receiver expects.
                self.sequence_number = int(seqno)
                self.send_packet(retransmit=True)

            


    def timeout(self):
        #print self.sent_packets.keys()
        print self.sequence_number
        for seqno in range(self.sequence_number, self.sequence_number+7):
            if seqno < self.total_packets+2:
                if (seqno == self.total_packets+1):
                    msg = "fin"
                    pack = self.make_packet(msg, seqno, "")
                    print "SENDING FIN PACKET " + str(seqno)
                    self.fin_seqno = seqno
                    self.sent_packets[seqno] = pack
                    self.send(pack)
                else:
                    msg = "dat"
                    pack = self.make_packet(msg, seqno, self.packets[seqno])
                    print "SENDING PACKET " + str(seqno)
                    self.sent_packets[seqno] = pack
                    self.send(pack)



    # Main sending loop.
    def start(self):

        # While the whole file has not been sent.
        self.make_packets()

        while not self.complete:      
            # Wait for ACK from receiver
            response = self.receive(.5)
            print response
            if response is not None:
                self.process_response(response)
            elif self.sequence_number == 0:
                self.send_packet()
            else:
                self.timeout()

        
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
