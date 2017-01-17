import sys
import getopt

import Checksum
import BasicSender
from itertools import groupby
import os
import math

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
        self.ack_received_list = []
        self.window = []
        self.fin_seqno = None
        self.confirmed_packets = {}
        self.sent_packets = {}
        self.packets = {}
        self.cum_ack = None
        self.sack_list = []
        self.time_elapsed = 0
        self.single_packet = False

    def check_filesize(self):
        info = os.stat(filename)
        self.size = info.st_size
        self.total_packets = math.ceil(self.size/1400.0)
        



    def get_data(self, seq_no):
        if seq_no != 0:
            data = self.infile.read(1400)
            self.packets[seq_no] = data
            return data


    def send_packet(self, retransmit=False, fast_packet=None):
        if self.sequence_number == 0:
            msg = "syn"
            pack = self.make_packet(msg, self.sequence_number, "")
            self.packets[0] = pack
            self.sent_packets[0] = pack
            self.send(pack)
        else:

            if self.sackMode:
                for seqno in range(self.sequence_number, self.sequence_number+7):
                    if seqno < self.total_packets+1 and str(seqno) not in self.sack_list and seqno not in self.sent_packets:
                        if (seqno == self.total_packets):
                            msg = "fin"

                            if seqno in self.packets:
                                data = self.packets[seqno]
                            else:
                                data = self.get_data(seqno)

                            pack = self.make_packet(msg, seqno, data)

                            self.fin_seqno = seqno
                            self.sent_packets[seqno] = pack
                            self.send(pack)
                        else:
                            msg = "dat"

                            if seqno in self.packets:
                                data = self.packets[seqno]
                            else:
                                data = self.get_data(seqno)

                            pack = self.make_packet(msg, seqno, data)
                            self.sent_packets[seqno] = pack
                            self.send(pack)
            else:
                for seqno in range(self.sequence_number, self.sequence_number+7):

                    if seqno < self.total_packets+1:

                        if (seqno == self.total_packets) and (seqno not in self.sent_packets or retransmit):
                            msg = "fin"
                            if seqno in self.packets:
                                data = self.packets[seqno]
                            else:
                                data = self.get_data(seqno)
                            pack = self.make_packet(msg, seqno, data)
                            self.fin_seqno = seqno
                            self.sent_packets[seqno] = pack

                            self.send(pack)
                            break
                        else:
                            if seqno not in self.sent_packets or retransmit:
                                msg = "dat"
                                if seqno in self.packets:
                                    data = self.packets[seqno]
                                else:
                                    data = self.get_data(seqno)
                                pack = self.make_packet(msg, seqno, data)
                                self.sent_packets[seqno] = pack
                                self.send(pack)



    def process_response(self, response):


        if Checksum.validate_checksum(response):


            if (self.sackMode):
                msg_type, seqno, response_data, checksum = self.split_packet(response)

                self.cum_ack, self.sack_list = seqno.split(';')

                self.sack_list = self.sack_list.split(',')
                for elem in self.sack_list:
                    if elem != '':
                        elem = int(elem)

                seqno = int(self.cum_ack)

            else:
                msg_type, seqno, response_data, checksum = self.split_packet(response)
                seqno = int(seqno)


            #self.sent_packets.pop(seqno, None)


            if seqno < self.sequence_number:
                return


            fast_retrans = None

            self.ack_received_list.append(seqno)

            # Fast retransmit
            # Counting consecutive repeats code taken from stackoverflow
            grouped_acks = [[k, sum(1 for i in g)] for k,g in groupby(self.ack_received_list)]

            for elem in grouped_acks:
                if elem[1] == 4:
                    fast_retrans = int(elem[0])
                    elem[1] = 0


            if fast_retrans:
                #self.sequence_number = int(seqno)
                
                if self.sackMode:
                    self.timeout()
                    self.ack_received_list = []
                    return

                else:
                    if fast_retrans not in self.confirmed_packets:
                        self.ack_received_list = []

                        if (fast_retrans == self.total_packets+1):
                            msg = "fin"
                        else:
                            msg = "dat"

                        pack = self.make_packet(msg, fast_retrans, self.packets[fast_retrans])
                        self.sent_packets[fast_retrans] = pack

                        self.send(pack)

                    return

            if seqno == (self.total_packets + 1):
                self.complete = True

            # If the ack is expecting the next seq number, send it
            elif seqno > self.sequence_number:
                for i in range(0, seqno):
                    self.confirmed_packets[i] = self.packets[i]



                self.sequence_number = seqno
                if self.sequence_number == 1:
                    self.send_packet()
                else:     
                    for i in range(self.sequence_number, self.sequence_number+7):
                        if (not i >= self.total_packets+1 and i not in self.sent_packets):
                            if (i == self.total_packets):
                                msg = "fin"
                            else:
                                msg = "dat"

                            if i in self.packets:
                                data = self.packets[i]
                            else:
                                data = self.get_data(i)

                            pack = self.make_packet(msg, i, data)
                            self.sent_packets[i] = pack
                            self.send(pack)
            else:
                # A packet was dropped, set our sequence number to the one the receiver expects.
                self.sequence_number = int(seqno)
                for i in range(1, self.sequence_number):
                    self.confirmed_packets[i] = self.packets[i]
                    self.send_packet()


    def timeout(self):
        if self.sackMode:
            for seqno in range(self.sequence_number, self.sequence_number+7):
                if seqno < self.total_packets+1 and str(seqno) not in self.sack_list:
                    if (seqno == self.total_packets):
                        msg = "fin"
                        if seqno in self.packets:
                            data = self.packets[seqno]
                        else:
                            data = self.get_data(seqno)
                        pack = self.make_packet(msg, seqno, data)
                        self.fin_seqno = seqno
                        self.sent_packets[seqno] = pack

                        self.send(pack)
                    else:
                        msg = "dat"
                        if seqno in self.packets:
                            data = self.packets[seqno]
                        else:
                            data = self.get_data(seqno)
                        pack = self.make_packet(msg, seqno, data)
                        self.sent_packets[seqno] = pack

                        self.send(pack)

        else:
            for seqno in range(self.sequence_number, self.sequence_number+7):
                if seqno < self.total_packets+1:
                    if (seqno == self.total_packets):
                        msg = "fin"
                        if seqno in self.packets:
                            data = self.packets[seqno]
                        else:
                            data = self.get_data(seqno)
                        pack = self.make_packet(msg, seqno, data)
                        self.fin_seqno = seqno
                        self.sent_packets[seqno] = pack
                        self.send(pack)

                    else:
                        msg = "dat"
                        if seqno in self.packets:
                            data = self.packets[seqno]
                        else:
                            data = self.get_data(seqno)
                        pack = self.make_packet(msg, seqno, data)
                        self.sent_packets[seqno] = pack
                        self.send(pack)



    # Main sending loop.
    def start(self):

        # While the whole file has not been sent.
        self.check_filesize()

        while not self.complete:

            # Wait for ACK from receiver
            response = self.receive(.5)
            if response is not None:
                self.process_response(response)
            elif self.sequence_number == 0:
                self.send_packet()
            else:
                self.ack_received_list = []
                self.sent_packets = {}
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
