#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
The INA219 device is a Bidirectional Current/Power Monitor with i2c I/F.

INA219 datasheet: www.ti.com/lit/ds/symlink/ina219.pdf

Author:  Saint James Devices, MK Beavers
Changes: Initial release, 11June2017
Developed & Tested on Raspberry Pi.
"""

# Imports
import sys
import smbus

# Class declarations


class INA219():
    """
    Monitor voltage, current, & power to a load using ina219 device.

    The device has a fixed address, in range 0x40-4F, on an I2C bus.

    Script Usage: ./ina219.py [device_address [i2c_bus [shuntOhms]]]
        Defaults:  device_address=64, i2c_bus=1, shuntOhms=0.1
    Prints the device registers and basic data to the console.
    """
    CONFIG = 0
    SHUNTV = 1
    BUSV = 2
    POWER = 3
    CURRENT = 4
    CALIB = 5
    BUSV_CNVR_BIT = 2   # BUSV.CNVR (conversion ready) bit mask
    BUSV_CNV_MASK = 3   # BUSV.CNVR & BUSV.OVF (overflow) bit mask
    BUSV_CNV_OK = 2     # BUSV.CNVR = 1 & BUSV.OVF = 0 if conversion OK

    def _readWordReg(self, register):
        """ Return the register value. """
        value = self.bus.read_word_data(self.addr, register)
        return (value & 0xFF) * 256 + (value // 256)

    def _writeWordReg(self, reg, value):
        """ Write the value to the register. """
        swapped = (value & 0xFF) * 256 + (value // 256)
        self.bus.write_word_data(self.addr, reg, swapped)

    def _isConversionOK(self):
        """ Return True if conversion is OK else False. """
        status = INA219.BUSV_CNV_MASK & self._readWordReg(INA219.BUSV)
        return INA219.BUSV_CNV_OK == status

    def _setCurrentLSB(self, calValue):
        self.currentLSB = 0.04096 / (calValue * self.rShunt)

    def __init__(self, address=0x40, bus=1, rShunt=0.1):
        """ Save the connection parameters and init currentLSB. """
        self.bus = smbus.SMBus(bus)
        self.addr = address
        self.rShunt = rShunt
        calValue = self._readWordReg(INA219.CALIB)
        if calValue != 0:
            self._setCurrentLSB(calValue)

    def getLoadVoltage(self):
        """ Return the load voltage in Volts or -1. """
        B = self._readWordReg(INA219.BUSV)
        if INA219.BUSV_CNVR_BIT == (B & INA219.BUSV_CNVR_BIT):
            B >>= 3     # normalize the ADC count
            B *= 0.004  # 4mv = LSB
            B = round(B, 5)
        else:
            B = -1.0
        return B

    def getShuntVoltage(self):
        """ Return the shunt voltage in Volts or -1. """
        S = self._readWordReg(INA219.BUSV)
        if INA219.BUSV_CNVR_BIT == (S & INA219.BUSV_CNVR_BIT):
            S = self._readWordReg(INA219.SHUNTV)
            S *= 0.000010   # 10uv = LSB
            S = round(S, 5)
        else:
            S = -1.0
        return S

    def getLoadCurrent(self):
        """
        Return the load current, in Amps, or -1 when no conversion is
        ready or an overflow condition occured.

        The calibration register (R5) must be > 0 for a non-zero return.
        """
        I = -1.0
        if self._isConversionOK():
            I = self._readWordReg(INA219.CURRENT)
            I *= self.currentLSB
            I = round(I, 5)
        return I

    def getPowerUsed(self):
        """
        Return the load power usage, in Watts, or -1 when no conversion
        is ready or an overflow condition occured.

        The calibration register (R5) must be > 0 for a non-zero return.
        """
        P = -1.0
        if self._isConversionOK():
            P = self._readWordReg(INA219.POWER)
            P *= 20 * self.currentLSB
            P = round(P, 5)
        return P

    def getRegisters(self):
        """ Return a list of the all device register values.

        RegisterName[index] Rd/Wr   On Reset
        --------------------------------------
        Configuration[0]    R/W      14751 (0x399F)
        Shunt voltage[1]    R/O     variable
        Bus voltage[2]      R/O     variable
        Power[3]            R/O        0
        Current[4]          R/O        0
        Calibration[5]      R/W        0
        """
        regs = []
        regs.append(self._readWordReg(INA219.CONFIG))
        regs.append(self._readWordReg(INA219.SHUNTV))
        regs.append(self._readWordReg(INA219.BUSV))
        regs.append(self._readWordReg(INA219.POWER))
        regs.append(self._readWordReg(INA219.CURRENT))
        regs.append(self._readWordReg(INA219.CALIB))
        return regs

    def setConfiguration(self, configuration):
        """ Update the device configuration.

            See INA219 datasheet for details on configuration options.
        """
        self._writeWordReg(INA219.CONFIG, configuration)

    def setCalibration(self, calibrate):
        """ Update the device calibration.

        The calibration controls the translation between the shunt
        voltage to current and power register.

        Example of calibrate value selection:
            rShunt = 0.1 ohms
            Minimum Imax desired = 0.5 amps

        Determine the minimum current step for the ADC?
            Imax / 2**15 = 0.5 / 32768 = 15.2587890625 e-06
        Select the ADC_LSB current step by rounding up to an integer?
            15.2587890625 e-06 rounded to 16 e-06
        Solve for calibrate?
            0.04096 / (ADC_LSB * rShunt) =
            0.04096 / (16 e-06 * 0.1) = 25600 = 0x6400

        Actual Imax using the selected ADC_LSB is?
            ADC_LSB * 2**15 = 655.36 milliAmps
        """
        self._writeWordReg(INA219.CALIB, calibrate)
        if calibrate != 0:
            self._setCurrentLSB(calibrate)

# Function declarations


def main():
    argLen = len(sys.argv)
    if argLen == 1:
        ina = INA219()
    elif argLen == 2:
        ina = INA219(int(sys.argv[1]))
    elif argLen == 3:
        ina = INA219(int(sys.argv[1]), int(sys.argv[2]))
    elif argLen == 4:
        ina = INA219(int(sys.argv[1]), int(sys.argv[2]),
                     float(sys.argv[3]))
    else:
        print('usage: %s [addr [smbus [rShunt]]]' % (sys.argv[0]))
        sys.exit(1)
    try:
        regs = ina.getRegisters()
        print('Registers[0-5] =', regs)
        print('BusVoltage (in Volts) =', ina.getLoadVoltage())
        print('ShuntVoltage (in Volts) =', ina.getShuntVoltage())
        if regs[5] != 0:
            print('LoadCurrent (in Amps) =', ina.getLoadCurrent())
            print('LoadPower (in Watts) =', ina.getPowerUsed())
    except OSError:
        print('Connection to INA219 failed.')
        sys.exit(121)
    sys.exit(0)

# Main body
if __name__ == '__main__':
    main()
