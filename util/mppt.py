"""Copyright (c) 2014, Dilithium Power Systems LLC All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of Dilithium Power Systems LLC.

"""

import eeprom
import logging
import struct
import time

import can_ethernet
import can_msg_pb2

class MpptNotPresent(Exception):
  pass

class BadPacket(Exception):
  pass


class mppt():
  # initialize tracker structure also initialize the eeprom

  def __init__(self, channel, baseid, can):
    self.canAddress = baseid + channel
    self.can = can
    self.temp = 0
    self.vin = 0
    self.vout = 0
    self.iin = 0
    self.iout = 0
    
    # debug level
    self.debug = 0

    self.found = self.detectMPPT()
    if self.found:
      self.ee = eeprom.eeprom(channel, baseid, can, self)
    else:
      raise MpptNotPresent('MPPT 0x%03x not detected' % self.canAddress)

  def RTRPacket(self, canAddress, retries, timeout):
    for _ in xrange(retries):
      # form the rtr packet to send
      tx = can_msg_pb2.CanMessage()
      tx.id = canAddress
      tx.type = can_msg_pb2.STD_RTR
      tx.data.extend([0] * 8)

      # send the packet
      self.can.SendPkt(tx)
      try:
        rx = self.can.WaitForPacket(tx, timeout)
      except can_ethernet.TimeoutError:
        return None
    return rx

  # detect if mppt is on the bus
  def detectMPPT(self):
    
    # try to detect mppt through RTR packet
    rx = self.RTRPacket(self.canAddress, 3, 0.1)

    # report what happened
    if rx:
      logging.info('MPPT Detected at address: 0x%03X' % (self.canAddress))
      return True
    else:
      logging.info('Failed to Discover MPPT: 0x%03X' % (self.canAddress))
      return False

  def getStateData(self):
    # get the state of the mppt - voltage in, volatge out, current and
    # temperature
    rx = self.RTRPacket(self.canAddress, 3, 0.1)
    self.parseStatePacket(rx)

  def setEnable(self, enable, leds='on'):
    # this function will send the packet to enable or disable the mppt
    param = 0
    if(enable == 'on'):
      param = param | 0x01
      try_report(self.rpt,
             'Enabled MPPT',
             False,
             False,
             '0x{0:X}'.format(self.canAddress),
             '')
    elif(enable == 'off'):
      param = param & 0xfe
      try_report(self.rpt,
             'Disabled MPPT',
             False,
             False,
             '0x{0:X}'.format(self.canAddress),
             '')
    else:
      param = param & 0xfe

    if(leds == 'on'):
      param = param & 0xfd
      try_report(self.rpt,
             'Enabled LEDs',
             False,
             False,
             '0x{0:X}'.format(self.canAddress),
             '')
    elif(leds == 'off'):
      param = param | 0x02
      try_report(self.rpt,
             'Disabled LEDs',
             False,
             False,
             '0x{0:X}'.format(self.canAddress),
             '')
    else:
      param = param & 0xfd

    tx = canPacket('t', self.canAddress + 0x10, 1, [param], False, False)
    self.can.sendPkt(tx)

  # this function will force the mppt duty cycle to a fixed value
  # eeprom testMode must be set to 1 for this command to function
  def setDutyCycle(self, dutyCycle):
    s = struct.pack('>H', dutyCycle)
    output = struct.unpack('>BB', s)

    # make packet with magic sequence
    tx = canPacket('t', self.canAddress + 0x70, 8, [output[0],
                            output[1],
                            0, 0, 45, 78, 69, 0])
    # send the packet
    self.can.sendPkt(tx)

  # this function will take the returned state packet and parses it out to
  # usable state variables
  def parseStatePacket(self, pkt):

    if not pkt.dlc == 8:
      raise BadPacket('DLC must = 8: %d' % pkt.dlc)
    if not pkt.id == self.canAddress:
      raise BadPacket('Address must = self.canAddress: %d' % pkt.id)

    self.vin = float(pkt.data[1] * 0x100 + pkt.data[0]) / 100.0
    self.vout = float(pkt.data[5] * 0x100 + pkt.data[4]) / 100.0
    self.iin = float(pkt.data[3] * 0x100 + pkt.data[2]) / 1000.0
    self.temp = float(pkt.data[7] * 0x100 + pkt.data[6]) / 100.0

  def reset(self):
    logging.info('Resetting MPPT...')
    
    # create the packet structure
    tx = can_msg_pb2.CanMessage()
    tx.id = self.canAddress + 0x30
    
    # build the can packet payload with the magic number
    tx.data.extend([0, 0, 0, 0, 45, 78, 69, 0xfe])
    # send the packet on the bus

    self.can.SendPkt(tx)
    logging.info('Waiting for MPPT to initialize...')
    time.sleep(6)
    logging.info('Done.')
    
