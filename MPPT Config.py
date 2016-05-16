#!/usr/bin/env python

"""Copyright (c) 2016, Dilithium Power Systems LLC All rights reserved.

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
from Tkinter import *
import ttk
import time
import sys

sys.path.append('./util')
sys.path.append('../util')

import can_ethernet
import can_msg_pb2
import eeprom
import mppt

from multiprocessing import freeze_support


class GUI(Frame):

  def writeEEPROM(self):
    # see if it's possible to configure
    #try:
    if True:
      self.configChannel = self.selectedChannel.get()
      ee = self.tracker[self.configChannel].ee
    #except:
    #  return
    nEEPROMValues = len(ee.data)

    for i in range(nEEPROMValues):
      eeName = ee.data[i][0]
      valueToWrite = self.eepromNewValueVar[i].get()
      print 'name= {0:s} val= {1:g}'.format(eeName, valueToWrite)
      ee.writeValue(eeName, valueToWrite)
    # reset the mppt
    self.tracker[self.configChannel].reset()
    self.discoverMPPTs()
    ee = self.tracker[self.configChannel].ee

    for i in range(len(ee.data)):
      eeType = ee.data[i][1] 
      eeValue = ee.data[i][2] 
      if(eeType == 'int32'):
        self.eepromValueVar[i].set('{:d}'.format(eeValue))
      else:
        self.eepromValueVar[i].set('{:g}'.format(eeValue))

  def loadConfigFromFile(self):
    # see if it's possible to configure
    if True:
    #try:
      self.configChannel = self.selectedChannel.get()
      ee = self.tracker[self.configChannel].ee
    #except:
    #  return
    filename = 'configuration.csv'
    sn = int(self.newSN.get())
    ee.loadConfigurationFromFile(filename, sn)

    # reset the mppt
    self.tracker[self.configChannel].reset()
    self.discoverMPPTs()

    # load the new values from the mppt
    ee = self.tracker[self.configChannel].ee

    # load the values into the gui
    for i in range(len(ee.data)):
      eeType = ee.data[i][1] 
      eeValue = ee.data[i][2] 
      if(eeType == 'int32'):
        self.eepromValueVar[i].set('{:d}'.format(eeValue))
      else:
        self.eepromValueVar[i].set('{:g}'.format(eeValue))

  def configureMPPT(self):
    # see if it's possible to configure
    if True:
    #try:
      self.configChannel = self.selectedChannel.get()
      ee = self.tracker[self.configChannel].ee
    #except:
    #  return

    # disable the button
    self.configureButton.configure(state=DISABLED)

    cw = Toplevel(self.w)
    self.cw = cw

    # intercept the destroy action to run the close function first
    cw.protocol('WM_DELETE_WINDOW', self.CloseConfigWindow)

    # title the window
    cw.wm_title(
      'MPPT Channel {0:d} Configuration'.format(
        self.configChannel))

    px = 2
    py = 2

    # set up column widths
    cw.columnconfigure(0, minsize=100, weight=10)
    cw.columnconfigure(1, minsize=100, weight=10)
    cw.columnconfigure(2, minsize=100, weight=10)
    cw.columnconfigure(3, minsize=100, weight=10)

    # column labels
    Label(cw, text='Parameter').grid(row=1, column=0, padx=px, pady=py)
    Label(cw, text='Type').grid(row=1, column=1, padx=px, pady=py)
    Label(cw, text='Current Value').grid(row=1, column=2, padx=px, pady=py)

    # initialize the individual channel objects
    nEEPROMValues = len(ee.data)

    self.eepromName = {}
    self.eepromType = {}
    self.eepromValue = {}
    self.eepromValueVar = {}

    self.loadConfigButton = Button(
      cw,
      text='Load New Config',
      command=self.loadConfigFromFile)
    self.loadConfigButton.grid(row=0, column=0, sticky=W, padx=px, pady=py)

    Label(cw, text='SN to Write').grid(row=0, column = 1, padx = px, pady = py)

    self.newSN = StringVar()
    self.newSN.set('{0:d}'.format(ee.data[0][2]))

    vcmd = cw.register(self.validateCANSNEntry)
    self.newSNEntry = Entry(cw, textvariable=self.newSN, validate='key',
                            validatecommand=(vcmd, '%P'))
    self.newSNEntry.grid(row=(0), column=2, sticky = W)

    for i in range(nEEPROMValues):
      rw = i + 2

      eeName = ee.data[i][0]
      eeType = ee.data[i][1]

      # eeprom parameter name
      self.eepromName[i] = Label(cw, text='{0:s}'.format(eeName))
      self.eepromName[i].grid(
        row=rw,
        column=0,
        sticky=W,
        padx=px,
        pady=py)

      # eeprom parameter type
      self.eepromType[i] = Label(cw, text='{0:s}'.format(eeType))
      self.eepromType[i].grid(
        row=rw,
        column=1,
        sticky=W,
        padx=px,
        pady=py)

      #try:
      if True:
        eeValue = ee.readValue(eeName)
      #except:
      #  eeValue = -1
      # eeprom parameter value
      self.eepromValueVar[i] = StringVar()
      if(eeType == 'int32'):
        self.eepromValueVar[i].set('{:d}'.format(eeValue))
      else:
        self.eepromValueVar[i].set('{:g}'.format(eeValue))
      self.eepromValue[i] = Label(
        cw,
        textvariable=self.eepromValueVar[i])
      self.eepromValue[i].grid(
        row=rw,
        column=2,
        sticky=W,
        padx=px,
        pady=py)

  def CloseConfigWindow(self):
    self.configureButton.configure(state=NORMAL)
    self.cw.destroy()

  def validateCANSNEntry(self, P):
    try:
      if P != '':
        v = int(P, 10)
        if v > 32000 or v < 0:
          raise ValueError
      return True
    except ValueError:
      return False

  def validateCANAddressEntry(self, P):
    try:
      v = int(P, 16)
      if v > 0x7ff:
        raise ValueError
      return True
    except ValueError:
      return False

  def configCAN(self):
    self.killThread()
    self.guiStatus.config(text='Status: Configuring CAN Bus')
    bitrate = int(self.bitrateStr.get())
    if True:
      if hasattr(self, 'can'):
        self.can.Close()
      self.can = can_ethernet.canEthernet()
      self.can.Connect(bitrate)
      self.guiStatus.config(text='Status: Configuring CAN Bus Succeeded')
      self.bridge.config(text='CAN Bridge: %x' % (self.can.bridgeIP))
      self.discoverButton.config(state=NORMAL)
    #except:
    #  self.guiStatus.config(text='Status: Configuring CAN Bus Failed')

  def setConfigState(self, index, state):
    assert state == 'NORMAL' or state == 'DISABLED'
    if(state == 'NORMAL'):
      self.inputVoltage[index].config(state=NORMAL)
      self.inputCurrent[index].config(state=NORMAL)
      self.inputPower[index].config(state=NORMAL)
      self.outputVoltage[index].config(state=NORMAL)
      self.temperature[index].config(state=NORMAL)
      self.channelSelected[index].config(state=NORMAL)
    else:
      self.inputVoltage[index].config(state=DISABLED)
      self.inputCurrent[index].config(state=DISABLED)
      self.inputPower[index].config(state=DISABLED)
      self.outputVoltage[index].config(state=DISABLED)
      self.temperature[index].config(state=DISABLED)
      self.channelSelected[index].config(state=DISABLED)
    return

  def setValues(self, index, error=False, errorString=''):
    assert error == True or error == False
    if error == False:
      # if theres no error, update the values
      self.inputVoltageStr[index].set(
        '{0:g}'.format(
          self.tracker[index].vin))
      self.inputCurrentStr[index].set(
        '{0:g}'.format(
          self.tracker[index].iin))
      self.inputPowerStr[index].set(
        '{0:g}'.format(
          self.tracker[index].vin *
          self.tracker[index].iin))
      self.outputVoltageStr[index].set(
        '{0:g}'.format(
          self.tracker[index].vout))
      self.temperatureStr[index].set(
        '{0:g}'.format(
          self.tracker[index].temp))
    else:
      # if theres an error, print the error string
      self.inputVoltageStr[index].set(errorString)
      self.inputCurrentStr[index].set(errorString)
      self.inputPowerStr[index].set(errorString)
      self.outputVoltageStr[index].set(errorString)
      self.temperatureStr[index].set(errorString)
    return

  def killThread(self):
    if self.updateJob is not None:
      self.w.after_cancel(self.updateJob)

  def discoverMPPTs(self):
    logging.info('Discovering MPPTs')
    first = True
    baseAddr = int(self.baseAddr.get(), 16)
    for i in range(16):
      try:
        self.tracker[i] = mppt.mppt(i, baseAddr, self.can)
        
        try:
          sn = self.tracker[i].ee.readValue('serialNumber')
          swRev = self.tracker[i].ee.readValue('SWVersion')
          self.mpptStatus[i].config(
            text='SN ' +
            str(sn) +
            ' SW ' +
            str(swRev))
        except eeprom.MpptEepromError:
          self.mpptStatus[i].config(text='Error Reading SN')
        self.setConfigState(i, 'NORMAL')
        self.trackerFound[i] = 1
      except mppt.MpptNotPresent:
        self.mpptStatus[i].config(text='Not Found')
        self.inputVoltage[i].config
        self.trackerFound[i] = 0
        self.setConfigState(i, 'DISABLED')
      # update the gui
      self.w.update_idletasks()
    self.guiStatus.config(
      text='Status: {0:g} MPPTs found'.format(sum(self.trackerFound)))

    firstChannel = -1
    for i in range(16):
      if self.trackerFound[i] == 1:
        firstChannel = i
        break

    # if trackers are present then start the update thread
    if sum(self.trackerFound) > 0:
      self.configureButton.config(state=NORMAL)
      self.selectedChannel.set(firstChannel)
      self.updateMPPTStatus()
    else:
      self.configureButton.config(state=DISABLED)
    return

  def updateMPPTStatus(self):
    # ensure theres only one thread running
    self.killThread()

    # this line make it call itself at the chosen rate
    self.updateJob = self.w.after(
      1000 /
      self.updateSpeed,
      self.updateMPPTStatus)

    # cycle through the mppts and if it showed up on the but get it's data
    # and display it
    for i in range(16):
      if(self.trackerFound[i] == 1):
        # try:
        self.tracker[i].getStateData()
        self.setValues(i)
        # except:
        #	self.setValues(i, True, 'error')
      else:
        self.setValues(i, True, '0')

    # print the update number
    self.updateRate = 1 / (time.time() - self.lastUpdateTime)
    self.lastUpdateTime = time.time()
    updateRateFail = self.updateRate < self.updateSpeed / 5
    if updateRateFail:
      logging.error('Rate too slow, Update Rate = %0.1fhz' %  self.updateRate)
    else:
      logging.info('New Update, Update Rate = %0.1fhz' %  self.updateRate)
    self.updateNumber += 1
    return

  def Close(self):
    if hasattr(self, 'can'):
      self.can.Close()
    self.w.quit()

  def __init__(self, w):

    logging.basicConfig(level=logging.INFO)

    # make a reference back to the top window
    self.w = w

    logging.info('Initialized GUI')

    # handle closing the window gracefully
    w.protocol('WM_DELETE_WINDOW', self.Close)

    # setting up tkinter environment
    color = '#%02x%02x%02x' % (158, 158, 158)
    w.title('Photon MPPT Status')

    # set up column widths
    w.columnconfigure(0, minsize=50, weight=10)
    w.columnconfigure(1, minsize=50, weight=10)
    w.columnconfigure(2, minsize=50, weight=6)
    w.columnconfigure(3, minsize=50, weight=6)
    w.columnconfigure(4, minsize=50, weight=6)
    w.columnconfigure(5, minsize=50, weight=6)
    w.columnconfigure(6, minsize=50, weight=6)

    # classvars
    self.lastUpdateTime = time.time()
    self.channelSelected = [None] * 16
    self.tracker = [None] * 16
    self.mpptStatus = [None] * 16
    self.inputVoltage = [None] * 16
    self.inputVoltageStr = [None] * 16
    self.inputCurrent = [None] * 16
    self.inputCurrentStr = [None] * 16
    self.inputPower = [None] * 16
    self.inputPowerStr = [None] * 16
    self.outputVoltage = [None] * 16
    self.trackerFound = [None] * 16
    self.outputVoltageStr = [None] * 16
    self.temperature = [None] * 16
    self.temperatureStr = [None] * 16
    self.updateNumber = 0
    self.updateJob = None
    self.updateSpeed = 2  # hzi
    self.configWindowOpen = 0
    px = 2
    py = 2

    # tkinter object vars
    self.heartbeat = IntVar()
    self.baseAddr = StringVar()
    self.baseAddr.set('0x600')
    self.bitrateStr = StringVar()
    self.bitrateStr.set('125000')
    self.selectedChannel = IntVar()
    self.selectedChannel.set(-1)

    # setting up menubar
    self.menubar = Menu(w)
    w.configure(menu=self.menubar)
    #self.fileMenu = Menu(self.menubar)
    #self.menubar.add_cascade(label="File", menu=self.fileMenu)

    # column labels
    Label(w, text='Channel').grid(row=0, column=0, padx=px, pady=py)
    Label(w, text='Status').grid(row=0, column=1, padx=px, pady=py)
    Label(w, text='Input Voltage').grid(row=0, column=2, padx=px, pady=py)
    Label(w, text='Input Current').grid(row=0, column=3, padx=px, pady=py)
    Label(w, text='Input Power').grid(row=0, column=4, padx=px, pady=py)
    Label(w, text='Output Voltage').grid(row=0, column=5, padx=px, pady=py)
    Label(w, text='MPPT Temp').grid(row=0, column=6, padx=px, pady=py)

    # initialize the individual channel objects
    for i in range(16):
      rw = i + 1
      # box for writing the channel number
      txt = '{0:g}'.format(i)
      self.channelSelected[i] = Radiobutton(w, text=txt, variable=self.selectedChannel,
                          value=i, state=DISABLED)
      self.channelSelected[i].grid(
        row=rw,
        column=0,
        sticky=W,
        padx=px,
        pady=py)

      # status box for writing the serial number and software revision
      self.mpptStatus[i] = Label(w, text='')
      self.mpptStatus[i].grid(
        row=rw,
        column=1,
        sticky=W,
        padx=px,
        pady=py)

      # make handles for the objects for writing to the value cells
      self.inputVoltageStr[i] = StringVar()
      self.inputCurrentStr[i] = StringVar()
      self.inputPowerStr[i] = StringVar()
      self.outputVoltageStr[i] = StringVar()
      self.temperatureStr[i] = StringVar()

      self.inputVoltage[i] = Entry(
        w,
        state=DISABLED,
        textvariable=self.inputVoltageStr[i])
      self.inputVoltage[i].grid(
        row=rw,
        column=2,
        sticky=W,
        padx=px,
        pady=py)

      self.inputCurrent[i] = Entry(
        w,
        state=DISABLED,
        textvariable=self.inputCurrentStr[i])
      self.inputCurrent[i].grid(
        row=rw,
        column=3,
        sticky=W,
        padx=px,
        pady=py)

      self.inputPower[i] = Entry(
        w,
        state=DISABLED,
        textvariable=self.inputPowerStr[i])
      self.inputPower[i].grid(
        row=rw,
        column=4,
        sticky=W,
        padx=px,
        pady=py)

      self.outputVoltage[i] = Entry(
        w,
        state=DISABLED,
        textvariable=self.outputVoltageStr[i])
      self.outputVoltage[i].grid(
        row=rw,
        column=5,
        sticky=W,
        padx=px,
        pady=py)

      self.temperature[i] = Entry(
        w,
        state=DISABLED,
        textvariable=self.temperatureStr[i])
      self.temperature[i].grid(
        row=rw,
        column=6,
        sticky=W,
        padx=px,
        pady=py)

    # footer status labels
    self.guiStatus = Label(w, text='Status: Init')
    self.guiStatus.grid(
      row=18,
      column=0,
      columnspan=2,
      sticky=W,
      padx=px,
      pady=py)

    # status for the can bridge
    self.bridge = Label(w, text='CAN Bridge:')
    self.bridge.grid(
      row=19,
      column=0,
      columnspan=2,
      sticky=W,
      padx=px,
      pady=py)

    # label for the can address
    self.canAddrLabel = Label(w, text='CAN Base Addr:')
    self.canAddrLabel.grid(row=20, column=0, sticky=W, padx=px, pady=py)

    # button to intialize the can bus
    self.canButton = ttk.Button(w, text='Init CAN', command=self.configCAN)
    self.canButton.grid(row=17, column=0)

    # button to discover the mppts
    self.discoverButton = ttk.Button(w, state=DISABLED, text='Discover MPPTs',
                     command=self.discoverMPPTs)
    self.discoverButton.grid(row=17, column=1)

    # button to configure the mpppt
    self.configureButton = ttk.Button(
      w,
      text='Config MPPT',
      command=self.configureMPPT)
    self.configureButton.grid(row=17, column=2)
    self.configureButton.configure(state=DISABLED)

    # entry for the can address - this uses a validator
    vcmd = w.register(self.validateCANAddressEntry)
    self.canAddrEntry = Entry(
      w,
      textvariable=self.baseAddr,
      validate='key',
      validatecommand=(
        vcmd,
        '%P'))
    self.canAddrEntry.grid(row=20, column=1, sticky=W)

    self.bitrateLabel = Label(w, text='CAN Bitrate:')
    self.bitrateLabel.grid(row=21, column=0, sticky=W, padx=px, pady=py)

    self.bitrateSelect = ttk.Combobox(
      w,
      textvariable=self.bitrateStr,
      state='readonly')
    self.bitrateSelect.grid(row=21, column=1, sticky=W, padx=px, pady=py)
    self.bitrateSelect['values'] = (
      '10000',
      '20000',
      '50000',
      '125000',
      '250000',
      '500000',
      '1000000')

    logging.info('All GUI Elements Initialized')

    #self.heartbeatIndicator = Checkbutton(w, variable=self.heartbeat, onvalue=1, offvalue=0, image=None, bitmap=None, indicatoron=FALSE, text="Heartbeat")
    #self.heartbeatIndicator.grid(row=17, column = 2)

    # self.configCAN()
    # time.sleep(1)
    # self.discoverMPPTs()

if __name__ == '__main__':
  freeze_support()
  # initialize Tk and run mainloop
  root = Tk()
  # root.geometry("800x600+100+100")
  # root.iconbitmap(r'c:\Python27\DLLs\py.ico')
  g = GUI(root)
  root.mainloop()
