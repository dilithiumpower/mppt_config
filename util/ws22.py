
"""This is mostly an example opf how to organize a class for the wavescupltor
motor controller None of this code is tested at all and will likely require
some good work."""

import struct
import canPacket


def parseWSPacket(pkt):
    # pack byte array into a string
    # this might be the rverse order
    lowerArray = struct.pack(
        'BBBB',
        pkt.data[3],
        pkt.data[2],
        pkt.data[1],
        pkt.data[0])
    upperArray = struct.pack(
        'BBBB',
        pkt.data[7],
        pkt.data[6],
        pkt.data[5],
        pkt.data[4])

    # unpack string into a float
    lowerFloat = struct.unpack('f', lowerArray)
    upperFloat = struct.unpack('f', upperArray)

    return [lowerFloat, upperFloat]


class wavesculptor22():
    # initialize the object

    def __init__(self, can, baseaddr, report):

        # handle to the can interface
        self.can = can

        # handle to the reporting interface
        self.rpt = report

        # baseaddress of ws22
        self.baseaddr = baseaddr

        self.rpt.report(
            'Initializing Wavesculptor',
            False,
            False,
            '0x{:x}'.format(baseaddr),
            '',
            True)

    def getStateData(self):

        # set the timeout to slightly longer then interval
        to = 0.25

        # grab some packets from the bus
        StatusPkt, _ = self.can.getPacket(self.baseaddr + 1, to)
        BusMeasPkt, _ = self.can.getPacket(self.baseaddr + 2, to)
        VelocityPkt, _ = self.can.getPacket(self.baseaddr + 3, to)
        PhaseCurrentPkt, _ = self.can.getPacket(self.baseaddr + 4, to)
        MotorVoltagePkt, _ = self.can.getPacket(self.baseaddr + 4, to)

        # print packets for debug
        StatusPkt.printPacket()
        BusMeasPkt.printPacket()
        VelocityPkt.printPacket()
        PhaseCurrentPkt.printPacket()
        MotorVoltagePkt.printPacket()

        # parse them
        [self.busVoltage, self.busCurrent] = parseWSPacket(BusMeasPkt)
        [self.motorVelocity, self.vehicleVelocity] = parseWSPacket(VelocityPkt)
        [self.iC, self.iB] = parseWSPacket(PhaseCurrentPkt)
        [self.vD, self.vQ] = parseWSPacket(MotorVoltagePkt)
