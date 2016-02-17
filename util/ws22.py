
"""This is mostly an example opf how to organize a class for the wavescupltor
motor controller None of this code is tested at all and will likely require
some good work."""

import logging
import struct


def parseWSPacket(rx):
    # pack byte array into a string
    # this might be the rverse order
    lowerArray = struct.pack('BBBB', rx.data[3], rx.data[2], rx.data[1], rx.data[0])
    upperArray = struct.pack('BBBB', rx.data[7], rx.data[6], rx.data[5], rx.data[4])

    # unpack string into a float
    lowerFloat = struct.unpack('f', lowerArray)
    upperFloat = struct.unpack('f', upperArray)

    return [lowerFloat, upperFloat]


class wavesculptor22():
    # initialize the object

    def __init__(self, can, baseaddr):

        # handle to the can interface
        self.can = can

        # baseaddress of ws22
        self.baseaddr = baseaddr

        logging.info('Initializing Wavesculptor 0x03X' % baseaddr)

    def getStateData(self):

        # set the timeout to slightly longer then interval
        to = 0.25

        # grab some packets from the bus
        StatusPkt = self.can.WaitForPacket(self.baseaddr + 1, to)
        BusMeasPkt = self.can.WaitForPacket(self.baseaddr + 2, to)
        VelocityPkt = self.can.WaitForPacket(self.baseaddr + 3, to)
        PhaseCurrentPkt = self.can.WaitForPacket(self.baseaddr + 4, to)
        MotorVoltagePkt = self.can.WaitForPacket(self.baseaddr + 4, to)

        # parse them
        [self.busVoltage, self.busCurrent] = parseWSPacket(BusMeasPkt)
        [self.motorVelocity, self.vehicleVelocity] = parseWSPacket(VelocityPkt)
        [self.iC, self.iB] = parseWSPacket(PhaseCurrentPkt)
        [self.vD, self.vQ] = parseWSPacket(MotorVoltagePkt)
