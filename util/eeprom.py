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

import logging
import struct
import csv
import sys

sys.path.append('../util')

import can_msg_pb2


class MpptEepromError(Exception):
  pass


def approxEqual(a, b, tol):
  return abs(float(a) - float(b)) < tol


class eeprom():
  # function to initialize class - this is called on initialization of the
  # eeprom() object

  def __init__(self, channel, baseid, can, mppt):
    self.canAddress = baseid + channel
    self.can = can
    self.mppt = mppt
    self.data = [['serialNumber', 'int32', 0],
           ['hardOutputVoltage', 'float', 0],
           ['minOutputVoltage', 'float', 0],
           ['maxOutputVoltage', 'float', 0],
           ['constOutputVoltage', 'float', 0],
           ['maxTemperature', 'float', 0],
           ['hardCurrent', 'float', 0],
           ['maxCurrent', 'float', 0],
           ['scaleAmpsIn', 'float', 0],
           ['offsetAmpsIn', 'float', 0],
           ['scaleAmpsOut', 'float', 0],
           ['offsetAmpsOut', 'float', 0],
           ['scaleVoltsIn', 'float', 0],
           ['offsetVoltsIn', 'float', 0],
           ['scaleVoltsOut', 'float', 0],
           ['offsetVoltsOut', 'float', 0],
           ['constVoltageHyst', 'float', 0],
           ['safetyVoltageHyst', 'float', 0],
           ['safetyCurrentHyst', 'float', 0],
           ['safetyTemperatureHyst', 'float', 0],
           ['thermistorBeta', 'float', 0],
           ['thermistorRo', 'float', 0],
           ['thermistorRbias', 'float', 0],
           ['thermistorTo', 'float', 0],
           ['canBitrate', 'int32', 0],
           ['canBaseAddress', 'int32', 0],
           ['testMode', 'int32', 0],
           ['POseconds', 'float', 0],
           ['INCseconds', 'float', 0],
           ['TRACKseconds', 'float', 0],
           ['SWVersion', 'int32', 0],
           ['syncCurrentHi', 'float', 0],
           ['syncCurrentLow', 'float', 0],
           ['autoSendRate', 'float', 0],
           ]
    if True:
      self.readData()
      logging.info('Successfully read EEPROM Data from MPPT: 0x%03X' %
                   self.canAddress)
    else:
      logging.error('Failed to read EEPROM Data from MPPT: 0x%03x' %
                    self.canAddress)
      raise MpptEepromError('Failed to read MPPT EEPROM')

  # this function will return the variable iindex of a named eeprom variable
  def getIndex(self, key):
    for i in range(len(self.data)):
      if(self.data[i][0] == key):
        keyfound = 1
        break
    if(keyfound == 0):
      raise AssertionError('failed to find key')
    return i

  # this function will return the value of a named variable
  def getValue(self, key):
    i = self.getIndex(key)
    return self.data[i][2]

  # this function will return the type of a named eeprom variable
  def getType(self, key):
    i = self.getIndex(key)
    return self.data[i][1]

  # this will print the full contants of the eeprom to the terminal
  def printContents(self):
    for i in range(len(self.data)):
      print(
        '{0:s} {1:s} = {2:g}'.format(
          self.data[i][1],
          self.data[i][0],
          self.data[i][2]))

  # this function will read the contents of the eeprom on the device
  # and put it into the data structures
  def readData(self):

    for i in range(len(self.data)):
      if(self.data[i][1] == 'int32'):
        value = self.pktToInt32(self.getPacket(i))
      elif(self.data[i][1] == 'float'):
        value = self.pktToFloat(self.getPacket(i))
      else:
        raise Exception('no type match')
      self.data[i][2] = value

  # this function will send a packet on the canbus to retrieve a single
  # variable value out of eeprom
  def getPacket(self, idx):
    tx = can_msg_pb2.CanMessage()
    tx.id = self.canAddress + 0x20
    tx.data.extend([0, 0, 0, 0, 0, 0, 0, idx])
    self.can.SendPkt(tx)
    rx = self.can.WaitForPacket(tx, 2)
    return rx

  # this function will read a single value from eeprom and return it as a
  # number
  def readValue(self, key):
    i = self.getIndex(key)
    rawValue = self.getPacket(i)
    if(self.data[i][1] == 'int32'):
      value = self.pktToInt32(rawValue)
    elif(self.data[i][1] == 'float'):
      value = self.pktToFloat(rawValue)
    else:
      raise Exception('no type match')
    self.data[i][2] = value
    return value

  # this function will write a single named value to eeprom
  def writeValue(self, key, value):
    i = self.getIndex(key)
    if(self.data[i][1] == 'int32'):
      bytes = self.int32ToPkt(value)
    elif(self.data[i][1] == 'float'):
      bytes = self.floatToPkt(value)
    else:
      raise Exception('no type match')
    # create the packet structure
    tx = can_msg_pb2.CanMessage()
    tx.id = self.canAddress + 0x30
    
    # build the can packet payload with the magic number
    tx.data.extend([bytes[3], bytes[2], bytes[1], bytes[0], 45, 78, 69, i])
    
    # send the packet on the bus
    self.can.SendPkt(tx)

  # this function will write the contents of the eeprom to a configuration
  # file
  def writeConfigurationToFile(self, file_name, overwrite):
    assert file_name is not None
    assert overwrite is not None
    # read the file into memory
    serial_number = self.readValue('serialNumber')
    if(overwrite == True):
      #update data to reflect the current values on the device
      self.readData()

      # open the config file and read it's contents into memory
      f = open(file_name, 'r')
      assert f is not None
      lines = f.readlines()
      f.close()

      # open the config file for wiritng
      f = open(file_name, 'w')
      assert f is not None
      csvReader = csv.reader(lines)
      i = 0

      # loop through the unit configurations and write the correct one
      for row in csvReader:
        l = ','.join(row)
        if(i > 0):
          # if the line corresopnds to the correct serial number
          if(int(row[0]) == serial_number):
            l = ''
            #print 'config found - writing line'
            configExists = True
            for i in range(len(self.data)):
              l += '{0:g},'.format(self.data[i][2])
            l = l[:-1]
        f.write(l + '\n')
        #print l
        i += 1
      f.close()
    else:
      # if the config already exists - dont overwrite
      logging.info('Config File already contains entry - not overwriting')
    if not configExists:
      logging.info('%s written' % (file_name))
    return

  # read the configuration file and write to the device
  def loadConfigurationFromFile(self, file_name, serial_number):
    assert file_name is not None
    assert serial_number is not None
    # load the config file into memory
    f = open(file_name, 'r')
    r = csv.reader(f)
    header = r.next()

    # loop through file to see if this serial number is in the file and
    # find it's line index
    confExists = False

    i = 1
    while True:
      try:
        row = r.next()
        sn = int(row[header.index('serialNumber')])
        if(serial_number == sn):
          confExists = True
          dataToWrite = row
        i += 1
      except StopIteration:
        break

    # if the config exists dataToWrite now contains the row where 
    # the data exists
    if not confExists:
      raise AssertionError('Configuration does not exist.')
    else:
      logging.info('Writing Configuration to Unit')

      # write all the values to the eeprom on the device
      for i in range(len(dataToWrite)):
        # don't write the swversion variable - thats handled by the
        # device only
        if(header[i] != 'SWVersion'):
          self.writeNewEEPROMValue(header[i], float(dataToWrite[i]))

  # confirm that the values were correctly written
  def confirmConfiguration(self, file_name, serial_number):
    if not isinstance(file_name, str):
      raise TypeError('Filename must be a string: %s', type(file_name))
    if not isinstance(serial_number, int):
      raise TypeError('Serial number must be an int: %s', type(serial_number))
    
    # load the config file into memory
    f = open(file_name, 'r')
    r = csv.reader(f)
    header = r.next()

    # loop through file to see if this serial number is in the file and
    # find it's line index
    confExists = False

    i = 1
    while True:
      if True:
        row = r.next()
        sn = int(row[header.index('serialNumber')])
        if serial_number == sn :
          confExists = True
          dataToWrite = row
        i += 1
      #except:
       # break

    # if the config exists dataToWrite now contains the row where
    # the data exists
    assert confExists

    if confExists:
      for i in range(len(dataToWrite)):
        if(header[i] != 'SWVersion'):
          self.confirmNewEEPROMValue(
            header[i],
            float(
              dataToWrite[i]))
    return

  def floatToPkt(self, num):
    assert num is not None
    # convert a floating point number to its raw byte array
    s = struct.pack('>f', num)
    output = struct.unpack('BBBB', s)
    return output

  def int32ToPkt(self, num):
    assert num is not None
    # convert a 32 bit int to its array of bytes
    s = struct.pack('>i', num)
    output = struct.unpack('BBBB', s)
    return output

  def pktToFloat(self, pkt):
    assert pkt is not None
    # convert an array of bytes to a floating point number
    s = struct.pack(
      'BBBB',
      pkt.data[3],
      pkt.data[2],
      pkt.data[1],
      pkt.data[0])
    output = struct.unpack('>f', s)[0]
    return output

  def pktToInt32(self, pkt):
    assert pkt is not None
    # convert an array of bytes to a 32bit int
    temp = struct.pack(
      'BBBB',
      pkt.data[3],
      pkt.data[2],
      pkt.data[1],
      pkt.data[0])
    output = struct.unpack('>L', temp)[0]
    return output

  def writeNewEEPROMValue(self, key, newValue):
    # write a new value to the eeprom
    # this function confirms that the new value is different then 
    # the one currently in the eeprom
    currentValue = self.readValue(key)
    #print('Current {0:s} : {1:g}'.format(key, currentValue))
    if(approxEqual(currentValue, newValue, 0.00001)):
      logging.info('%s already set' % (key))
    else:
      self.writeValue(key, newValue)
      currentValue = self.readValue(key)
      cond = not approxEqual(currentValue, newValue, 0.001)
      logging.info('%s - writing %s' % (key, repr(newValue)))
      logging.info('%s - reading %s' % (key, self.readValue(key)))

  def confirmNewEEPROMValue(self, key, new_value):
    # confirm that the eeprom contains the specified value
    current_value = self.readValue(key)
    if approxEqual(current_value, new_value, 0.001):
      logging.info('%s confirmed: %s' % (key, repr(new_value)))
    else:
      logging.error('%s not confirmed: %s' % (key, repr(new_value)))
