#! /usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from ina219 import INA219
from guizero import App, Combo, Text, TextBox, Slider, PushButton


class TEST():
    """ class description """
    cbModeText = ["Power-down", "Shunt_Trig.", "Bus_Trig", "Shunt+Bus_Trig",
                  "ADC off", "Shunt_Cont.", "Bus_Cont.", "Shunt+Bus_Cont."]
    cbBusVText = ["16V FSR", "32V FSR"]
    cbShuntVText = ["\u00b140mV", "\u00b180mV", "\u00b1160mV", "\u00b1320mV"]
    cbBusBText = ["9 | 1", "10 | 1", "11 | 1", "12 | 1", "12 | 1 ",
                  "12 | 2", "12 | 4", "12 | 8", "12 | 16", "12 | 32",
                  "12 | 64", "12 | 128"]
    cbShuntBText = cbBusBText

    def __init__(self):
        """ The slider can't be queried for value, set defaults. """
        self.address = 64
        self.i2cBuss = 0

    def _updateConfig(self):
        """ Function doc """
        R0 = self.device.getRegisters()[0]
        self.cbBusV.set(TEST.cbBusVText[(0x2000 & R0) >> 13])
        self.cbShuntV.set(TEST.cbShuntVText[(0x1800 & R0) >> 11])
        option = (0x0780 & R0) >> 7
        if option > 3:
            option -= 4
        self.cbBusB.set(TEST.cbBusBText[option])
        option = (0x0078 & R0) >> 3
        if option > 3:
            option -= 4
        self.cbShuntB.set(TEST.cbShuntBText[option])
        self.cbMode.set(TEST.cbModeText[7 & R0])

    def newDevice(self):
        """ Function doc """
        self.device = INA219(self.address, self.i2cBuss,
                             float(self.tbShuntOhms.get()))
        self._updateConfig()

    def addrChanged(self, newValue):
        """ Function doc """
        self.address = int(newValue)

    def i2cChanged(self, newValue):
        """ Function doc """
        self.i2cBuss = int(newValue)

    def setConfig(self):
        """ Function doc """
        value = TEST.cbBusVText.index(self.cbBusV.get())
        value <<= 13
        option = TEST.cbShuntVText.index(self.cbShuntV.get())
        value |= option << 11
        option = TEST.cbBusBText.index(self.cbBusB.get())
        if option > 3:
            option += 4
        value |= option << 7
        option = TEST.cbShuntBText.index(self.cbShuntB.get())
        if option > 3:
            option += 4
        value |= option << 3
        value |= TEST.cbModeText.index(self.cbMode.get())
        self.device.setConfiguration(value)

    def doReset(self):
        """ Function doc """
        self.device.setConfiguration(0x8000)
        self._updateConfig()

    def getLoadV(self):
        """ Function doc """
        self.tbLoadV.set(str(self.device.getLoadVoltage()))

    def getShuntV(self):
        """ Function doc """
        self.tbShuntV.set(str(self.device.getShuntVoltage()))

    def getLoadI(self):
        """ Function doc """
        self.tbLoadI.set(str(self.device.getLoadCurrent()))

    def getLoadP(self):
        """ Function doc """
        self.tbLoadP.set(str(self.device.getPowerUsed()))

    def getRegs(self):
        """ Function doc """
        regs = self.device.getRegisters()
        self.tbGetReg012.set(str(regs[:3]))
        self.tbGetReg345.set(str(regs[3:]))

    def setCalib(self):
        """ Function doc """
        try:
            value = int(self.tbSetCal.get())
            self.device.setCalibration(value)
        except ValueError:
            self.tbSetCal.set('')

    # Main body
    def window(self):
        """ Function doc """
        app = App(title="INA219 Testing", width=475, height=535, layout="grid")
        ROW = 0
        PushButton(app, command=self.newDevice,
                   text="connectTo(addr, i2c, rShunt)",
                   grid=[ROW, 0], align="left")
        Text(app, text="addr:", size=12, grid=[ROW, 1], align="right")
        Slider(app, start=64, end=79, command=self.addrChanged,
                       grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="i2c:", size=12, grid=[ROW, 1], align="right")
        Slider(app, start=0, end=15, command=self.i2cChanged,
                        grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="rShunt:", size=12, grid=[ROW, 1], align="right")
        self.tbShuntOhms = TextBox(app, text='0.1', width=20,
                                   grid=[ROW, 2], align="left")
        ROW += 1
        PushButton(app, command=self.getLoadV, text="getLoadVoltage()",
                   grid=[ROW, 0], align="left")
        Text(app, text="in Volts:", size=12, grid=[ROW, 1], align="right")
        self.tbLoadV = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        PushButton(app, command=self.getShuntV, text="getShuntVoltage()",
                   grid=[ROW, 0], align="left")
        Text(app, text="in Volts:", size=12, grid=[ROW, 1], align="right")
        self.tbShuntV = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        PushButton(app, command=self.getLoadI, text="getLoadCurrent()",
                   grid=[ROW, 0], align="left")
        Text(app, text="in Amps:", size=12, grid=[ROW, 1], align="right")
        self.tbLoadI = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        PushButton(app, command=self.getLoadP, text="getPowerUsed()",
                   grid=[ROW, 0], align="left")
        Text(app, text="in Watts:", size=12, grid=[ROW, 1], align="right")
        self.tbLoadP = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        PushButton(app, command=self.getRegs, text="getRegisters()",
                   grid=[ROW, 0], align="left")
        Text(app, text="[Cfg, SV, BV]:", size=12, grid=[ROW, 1], align="right")
        self.tbGetReg012 = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="[P, I, Calib]:", size=12, grid=[ROW, 1], align="right")
        self.tbGetReg345 = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="", size=12, grid=[4, 1], align="left")
        ROW += 1
        PushButton(app, command=self.setCalib, text="setCalibration(calValue)",
                   grid=[ROW, 0], align="left")
        Text(app, text="calValue:", size=12, grid=[ROW, 1], align="right")
        self.tbSetCal = TextBox(app, width=20, grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="", size=12, grid=[ROW, 1], align="left")
        ROW += 1
        Text(app, text="Configuration\nOptions :", size=14,
                               grid=[ROW, 0], align="left")
        PushButton(app, command=self.doReset, text="doReset()",
                   grid=[ROW, 1], align="left")
        PushButton(app, command=self.setConfig, text="setConfiguration(...)",
                   grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="Mode", size=12, grid=[ROW, 0], align="left")
        Text(app, text="Bus Voltage", size=12, grid=[ROW, 1], align="left")
        Text(app, text="Shunt Voltage", size=12, grid=[ROW, 2], align="left")
        ROW += 1
        self.cbMode = Combo(app, options=TEST.cbModeText,
                            grid=[ROW, 0], align="left")
        self.cbBusV = Combo(app, options=TEST.cbBusVText,
                            grid=[ROW, 1], align="left")
        self.cbShuntV = Combo(app, options=TEST.cbShuntVText,
                              grid=[ROW, 2], align="left")
        ROW += 1
        Text(app, text="Bus Bits|Avg", size=12, grid=[ROW, 1], align="left")
        Text(app, text="Shunt Bits|Avg", size=12, grid=[ROW, 2], align="left")
        ROW += 1
        self.cbBusB = Combo(app, options=TEST.cbBusBText,
                            grid=[ROW, 1], align="left")
        self.cbShuntB = Combo(app, options=TEST.cbShuntBText,
                              grid=[ROW, 2], align="left")
        app.display()
        sys.exit(0)


# Main body
if __name__ == '__main__':
    test = TEST()
    test.window()
