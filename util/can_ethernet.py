"""Copyright (c) 2015, Dilithium Power Systems LLC All rights reserved.

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

import can_msg_pb2
import copy
import logging
import multiprocessing
import Queue
import socket
import struct
import time
import uuid


# Network constants
MCAST_GRP = '239.255.60.60'
MCAST_ADDR = '224.0.0.22'
MCAST_PORT = 4876
TCP_PORT = MCAST_PORT
BUFFER_SIZE = 1500
TIMEOUT = 2.0

UDP_MODE = 1
TCP_MODE = 2


class PacketFormatError(Exception):
  pass


class TimeoutError(Exception):
  pass


class CanInterface():

  def __init__(self, tx_q, rx_q, kill):
    self.tx_q = tx_q
    self.rx_q = rx_q
    self.kill = kill
    self.n_pkts_rx = 0
    self.n_pkts_tx = 0
    self.can_log = can_msg_pb2.CanLogMessage()
    logging.basicConfig(level=logging.DEBUG)
    self.bus_number = None
    self.Connect()
    self.udp_rx_sock.setblocking(0)
    self.run()

  def run(self):
    while not self.kill.value:
      self.Receive()
      if self.bus_number:
        self.Send()
    self.Close()

  def Receive(self):
    try:
      rx, srv_sock = self.udp_rx_sock.recvfrom(BUFFER_SIZE)
      msg = bytearray(rx)
      [client_id, idx, mac] = self.ParsePacketHeader(msg)
      if mac != self.mac:
        self.ParsePackets(msg, idx)
    except socket.error:
      pass

  def ParsePackets(self, msg, idx):
    while (idx + 14) <= len(msg):
      rawpkt = msg[idx:idx + 14]
      pkt = self.ParsePacket(rawpkt)
      self.n_pkts_rx += 1
      self.can_log.log.extend([pkt])
      try:
        self.rx_q.put(pkt.SerializeToString())
        logging.debug('RECV:\n %s', unicode(pkt))
      except:
        logging.warning('DROPPED PACKET')
      idx += 14

  def ParsePacketHeader(self, msg):
    if len(msg) == 30 or ((len(msg) - 30) % 14) == 0:
      self.bus_id = msg[1:8]
      self.bus_number = msg[7] & 0x0F
      client_id = ''.join('{:02x}'.format(x) for x in msg[10:16])
      mac = int(
          ''.join('{:02x}'.format(x) for x in copy.copy(msg[10:16])[::-1]), 16)
      idx = 16
      logging.debug('rx client_id: %s', client_id)
      logging.debug('rx mac:       %x', mac)
      logging.debug('my mac:       %x', self.mac)
    elif len(msg) % 14 == 0:
      # Packets this length are likely valid
      idx = 0
    else:
      dbg_msg = ''.join('{:02x}'.format(x) for x in msg)
      logging.debug(dbg_msg)
      logging.debug('msg len: %d', len(msg)) 
      raise PacketFormatError()
    return [client_id, idx, mac]
  
  def ParsePacket(self, msg):
    pkt = can_msg_pb2.CanMessage()
    pkt.timestamp = int(time.time() * 1000)
    pkt.id = int(''.join('{:02x}'.format(x) for x in msg[0:4]), 16)
    pkt.dlc = int('{:02x}'.format(msg[5]), 16)

    # Seperate the flags.
    flags = msg[4]
    heartbeat_f = bool((msg[4] & 0x80) >> 7)
    settings_f = bool((msg[4] & 0x40) >> 6)
    rtr_f = bool((msg[4] & 0x02) >> 1)
    extended_f = bool(msg[4] & 0x01)
   
    if not (settings_f or heartbeat_f):
      if not rtr_f and not extended_f:
        pkt.type = can_msg_pb2.STD
      elif not rtr_f and extended_f:
        pkt.type = can_msg_pb2.EXT
      elif rtr_f and not extended_f:
        pkt.type = can_msg_pb2.STD_RTR
      elif rtr_f and extended_f:
        pkt.type = can_msg_pb2.EXT_RTR
    elif settings_f:
      pkt.type = can_msg_pb2.TRITIUM_SETTINGS
    elif heartbeat_f:
      pkt.type = can_msg_pb2.TRITIUM_HEARTBEAT

    # Append the data
    data_str = ''.join('{:02x}'.format(x) for x in msg[6:14])
    for i in xrange(pkt.dlc):
      pkt.data.append(int(data_str[2 * i:2 * i + 2], 16))
    
    if not heartbeat_f:
      logging.debug('RECV:\n' + unicode(pkt))
    else:
      logging.debug('TRITIUM_HEARTBEAT')
    return pkt
  
  def Send(self):
    # Try to deque a packet
    try:
      pkt = can_msg_pb2.CanMessage()
      pkt.ParseFromString(self.tx_q.get_nowait())
      logging.debug('Send Deenqueued')
      self.SendPkt(pkt)
    except Queue.Empty:
      return

  def SendPkt(self, pkt):
    # Check if the type is ok and calculate the max id number
    if pkt.type in [can_msg_pb2.STD, can_msg_pb2.STD_RTR,
                    can_msg_pb2.TRITIUM_HEARTBEAT,
                    can_msg_pb2.TRITIUM_SETTINGS]:
      max_id = 2 ** 11
    elif pkt.type in [can_msg_pb2.EXT, can_msg_pb2.EXT_RTR]:
      max_id = 2 ** 29
    else:
      raise Exception('unknown packet type')

    # Check if the identifier is in range
    if not 0 <= pkt.id <= max_id:
      raise Exception('bad id\n%s', unicode(pkt))

    # Enforce DLC == length(data)
    if pkt.dlc:
      if pkt.dlc != len(pkt.data):
        raise Exception('bad dlc\n%s', unicode(pkt))
    else:
      pkt.dlc = len(pkt.data)

    # Check if the data section is good
    if pkt.type in [can_msg_pb2.STD, can_msg_pb2.EXT]:
      for i in xrange(pkt.dlc):
        if not 0 <= pkt.data[i] <= 0xff:
          raise Exception('bad data\n%s', unicode(pkt))

    # Magic number
    client_id = 0x0054726974697560 | self.bus_number

    # write the packet type
    if(self.socket_mode == UDP_MODE):
      msg = bytearray(30)
      msgoffset = 16
      struct.pack_into('>Q', msg, 0, client_id)
      struct.pack_into('<Q', msg, 10, int(self.mac))
    elif(self.socket_mode == TCP_MODE and self.first_msg == True):
      msg = bytearray(38)
      msgoffset = 38 - 14
      # Check if the forwarding range is ok
      if(self.fwd_start < 0 | self.fwd_start + self.fwd_range > 2 ** 29):
          raise Exception('Bad Forwarding Range')

      # Fwd identifier
      struct.pack_into('>I', msg, 0, self.fwd_start)

      # Fwd range
      struct.pack_into('>I', msg, 4, self.fwd_range)

      struct.pack_into('>Q', msg, 8, client_id)
      struct.pack_into('<Q', msg, 18, int(self.mac))
      self.first_msg = False

    elif(self.socket_mode == TCP_MODE and not self.first_msg):
      msg = bytearray(14)
      msgoffset = 0
    else:
      raise Exception('Unrecognized socket mode')

    # Add the identifier
    struct.pack_into('>I', msg, msgoffset, pkt.id)

    # Add the flags
    heartbeat_f = pkt.type == can_msg_pb2.TRITIUM_HEARTBEAT
    settings_f = pkt.type == can_msg_pb2.TRITIUM_SETTINGS
    rtr_f = pkt.type in [can_msg_pb2.STD_RTR, can_msg_pb2.EXT_RTR]
    extended_f = pkt.type in [can_msg_pb2.EXT, can_msg_pb2.EXT_RTR]

    # Form the flags byte
    E = extended_f
    R = rtr_f << 1
    S = settings_f << 6
    H = heartbeat_f << 7
    flags = E | R | S | H

    struct.pack_into('>B', msg, 4 + msgoffset, flags)

    # Add the data length code
    struct.pack_into('>B', msg, 5 + msgoffset, pkt.dlc)

    # Add the data if appropriate
    if pkt.type in [can_msg_pb2.STD, can_msg_pb2.EXT,
                    can_msg_pb2.TRITIUM_SETTINGS,
                    can_msg_pb2.TRITIUM_HEARTBEAT]:
        for i in xrange(pkt.dlc):
            struct.pack_into('>B', msg, 6 + i + msgoffset, pkt.data[i])

    # Send it
    logging.debug('SEND:\n' + unicode(pkt))
    if(self.socket_mode == UDP_MODE):
      self.udp_tx_sock.sendto(msg, (MCAST_GRP, MCAST_PORT))
      dbg_msg = 'UDP :' + ''.join('{:02x}'.format(x) for x in msg)
      logging.debug(dbg_msg)
    elif(self.socket_mode == TCP_MODE):
      self.tcp_sock.send(msg)
      dbg_msg = 'TCP :' + ''.join('{:02x}'.format(x) for x in msg)
      logging.debug(dbg_msg)
    self.n_pkts_tx += 1

  def Connect(self):
    self.socket_mode = UDP_MODE
    self.mac = uuid.getnode()

    # Set up UDP receiver.
    self.udp_rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.udp_rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Pack multicast group structure correctly.
    mreq = struct.pack('=4sl', socket.inet_aton(MCAST_GRP),socket.INADDR_ANY) 
    
    # Request access to multicast group.
    self.udp_rx_sock.setsockopt(socket.IPPROTO_IP,
                                socket.IP_ADD_MEMBERSHIP, mreq)  
    
    # Bind to all intfs.
    self.udp_rx_sock.bind(('', MCAST_PORT))
    self.udp_rx_sock.settimeout(TIMEOUT)

    # Set up UDP transmitter.
    self.udp_tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.udp_tx_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
  
    # Get the MAC address of the local adapter.
    msg = bytearray(8)
    struct.pack_into('<Q', msg, 0, int(self.mac))
    self.local_mac = ''.join('{:02x}'.format(x) for x in msg[0:6])
    logging.debug('MAC Addr: %s', self.local_mac)

  def Close(self):
    logging.info('Closing Sockets')
    self.udp_tx_sock.close()
    self.udp_rx_sock.close()
    logging.info('Writing Log')
    f = open('can_log.bin', 'w')
    f.write(self.can_log.SerializeToString())
    f.close()
    logging.info('Packets Received: %d', self.n_pkts_rx)
    logging.info('Packets Sent: %d', self.n_pkts_tx)

class canEthernet():

  def __init__(self, logger=None):

    self.bridgeIP = 0

    # initialize variables
    self.txPackets = 0
    self.rxPackets = 0
    self.txConfirmed = 0
    self.socket_mode = UDP_MODE
    self.fwd_start = 0
    self.fwd_range = 0
    self.first_msg = True

    # initialize packet queue dict
    self.pkt_queue_dict = dict()

    # the queue dict allows grabbing packets in the order they were received,
    # indexed by their id

    if logger:
      self.logger = logger
    else:
      self.logger = logging


  def Connect(self, bitrate):
    # New Threaded Can Interface
    self.Cleanup()
    self.manager = multiprocessing.Manager()
    self.kill = self.manager.Value('b', False)
    self.tx_q = self.manager.Queue(1000)
    self.rx_q = self.manager.Queue(1000)
    self.iface = multiprocessing.Process(target=CanInterface,
        args=(self.tx_q, self.rx_q, self.kill))
    self.iface.start()
    self.SetBitrate(bitrate)

  def SetBitrate(self, bitrate):
    
    self.logger.info('Set bitrate %g bps', bitrate)
    # Calculate the parameters
    bitrate /= 1000
    lower_byte = bitrate & 0x00ff
    upper_byte = (bitrate & 0xff00) >> 8

    # Form the packet
    pkt = can_msg_pb2.CanMessage()
    pkt.type = can_msg_pb2.TRITIUM_SETTINGS
    pkt.id = 0x01
    pkt.data.extend([0x85, upper_byte, lower_byte])

    #Enqueue the packet
    self.tx_q.put(pkt.SerializeToString())

    # Wait for a return heartbeat packet
    match_pkt = can_msg_pb2.CanMessage()
    match_pkt.id = 0x00
    match_pkt.type = can_msg_pb2.TRITIUM_HEARTBEAT
    pkt = self.WaitForPacket(match_pkt, 2)
    bitrate = (pkt.data[0] * 0x100 + pkt.data[1]) * 1000
 
  def FlushQueueType(self, match_pkt):
    self.GrabAllPackets()
    while True:
      if self.GetPacketFromQueueDict(match_pkt.id) is None:
        return
      else:
        self.GrabAllPackets()

  def WaitForPacket(self, match_pkt, timeout=1):
    ''' Waits for a specified packet to come across the bus.

    Args:
      pkt: Type can_msg_pb2.CanMessage. Will try to match the id and type.
      timeout: How long to wait for the packet.
    Returns:
      pkt: Type can_msg_pb2.CanMessage.
    Raises:
      TimeoutError if timeout is exceeded.
    '''

    overtime = time.time() + timeout
    while True:
      pkt = self.GetPacketFromQueueDict(match_pkt.id)
      if pkt:
        return pkt
      else:
        self.GrabAllPackets()
      if time.time() > overtime:
        raise TimeoutError()

  def AddPacketToQueueDict(self, pkt):
    if pkt.id in self.pkt_queue_dict.keys():
      self.pkt_queue_dict[pkt.id].put(pkt)
      logging.debug('Recv Added to Queue Dict')
    else:
      # The queue doesnt exist
      self.pkt_queue_dict[pkt.id] = Queue.Queue()
      # Recursive call
      self.AddPacketToQueueDict(pkt)

  def GetPacketFromQueueDict(self, pkt_id):
    if pkt_id in self.pkt_queue_dict.keys():
      try:
        pkt = self.pkt_queue_dict[pkt_id].get_nowait()
        logging.debug('Recv Pulled from Queue Dict')
        return pkt
      except Queue.Empty:
        pass  
    return None

  def GrabAllPackets(self, timeout=1):
    '''Pull all of the outstanding packets from the rx queue and push to dict'''
    overtime = time.time() + timeout
    while True:
      try:
        # pull the next packet
        pkt_str = self.rx_q.get_nowait()
        pkt = can_msg_pb2.CanMessage()
        pkt.ParseFromString(pkt_str)
        logging.debug('Recv Deenqueued')

        # push to queue dict structure
        self.AddPacketToQueueDict(pkt)
      except Queue.Empty:
        break
      if time.time() > overtime:
        raise TimeoutError()

  def SendPkt(self, pkt):
    self.tx_q.put(pkt.SerializeToString())
    logging.debug('Send Enqueued')

  def Cleanup(self):
    # Housecleaning before Connnect or during Close
    if hasattr(self, 'kill'):
      self.kill.value = True
    if hasattr(self, 'tx_q'):
      self.GrabAllPackets()
      del self.tx_q
    if hasattr(self, 'tx_q'):
      del self.rx_q
    if hasattr(self, 'iface'):
      self.iface.join()
      self.iface.terminate()

  def Close(self):
    self.logger.info('Closing Sockets')
    self.Cleanup()

    return
