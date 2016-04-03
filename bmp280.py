#!/usr/bin/python

import time
import smbus

class  BMP280:
    ADDR=0x76	      #Pressure/Temp device address
    BMP280_ID=0x58    #chip ID
    #BMP280 Calibration Registers, rd_only
    T1_LSB=0x88         #Calibration coefficient
    T1_MSB=0x89         #Calibration coefficient
    T2_LSB=0x8A         #Calibration coefficient
    T2_MSB=0x8B         #Calibration coefficient
    T3_LSB=0x8C         #Calibration coefficient
    T3_MSB=0x8D         #Calibration coefficient
    P1_LSB=0x8E         #Calibration coefficient
    P1_MSB=0x8F         #Calibration coefficient
    P2_LSB=0x90         #Calibration coefficient
    P2_MSB=0x91         #Calibration coefficient
    P3_LSB=0x92         #Calibration coefficient
    P3_MSB=0x93         #Calibration coefficient
    P4_LSB=0x94         #Calibration coefficient
    P4_MSB=0x95         #Calibration coefficient
    P5_LSB=0x96         #Calibration coefficient
    P5_MSB=0x97         #Calibration coefficient
    P6_LSB=0x98         #Calibration coefficient
    P6_MSB=0x99         #Calibration coefficient
    P7_LSB=0x9A         #Calibration coefficient
    P7_MSB=0x9B         #Calibration coefficient
    P8_LSB=0x9C         #Calibration coefficient
    P8_MSB=0x9D         #Calibration coefficient
    P9_LSB=0x9E         #Calibration coefficient
    P9_MSB=0x9F         #Calibration coefficient
    RESERVED_LSB=0xA0   #Calibration coefficient
    RESERVED_MSB=0xA1   #Calibration coefficient
    #BMP280 Device Registers
    ID_REG=0xD0         #rd_only
    RESET_REG=0xE0      #wr_only  forced POW on writing 0xB6
    STATUS_REG=0xF3     #rd_only, measuring[3],im_update[0] 
    CONTROL_REG=0xF4    #rd/wr,   osrs_t<7:5>,osrs_p<4:2>,mode<1:0>
    CONFIG_REG=0xF5     #rd/wr,   t_sb<7:5>,filter<4:2>,spi3w_en[0]
    PRESS_MSB=0xF7      #rd_only
    PRESS_LSB=0xF8      #rd_only
    PRESS_XLSB=0xF9     #rd_only, bits 7:4
    TEMP_MSB=0xFA       #rd_only
    TEMP_LSB=0xFB       #rd_only
    TEMP_XLSB=0xFC      #only bits 7:4

    MODE_SLEEP=0x0
    MODE_FORCE=0x1
    MODE_NORMAL=0x3
    OSRS_SKIP=0x0
    OSRS_X1=0x1
    OSRS_X2=0x2
    OSRS_X4=0x3
    OSRS_X8=0x4
    OSRS_X16=0x5
    

    def __init__(self, temp_osrs = 1, press_osrs = 1, mode = 1):
        self.osrs_t=temp_osrs
        self.osrs_p=press_osrs
        self.mode=mode
        
        self.i2c=smbus.SMBus(1)	    #BMP280 is on the #1 i2c bus
        self.T1=self.i2c.read_word_data(BMP280.ADDR, BMP280.T1_LSB)
        self.T2=self.i2c.read_word_data(BMP280.ADDR, BMP280.T2_LSB)
        self.T3=self.i2c.read_word_data(BMP280.ADDR, BMP280.T3_LSB)
        self.P1=self.i2c.read_word_data(BMP280.ADDR, BMP280.P1_LSB)
        self.P2=self.i2c.read_word_data(BMP280.ADDR, BMP280.P2_LSB)
        self.P3=self.i2c.read_word_data(BMP280.ADDR, BMP280.P3_LSB)
        self.P4=self.i2c.read_word_data(BMP280.ADDR, BMP280.P4_LSB)
        self.P5=self.i2c.read_word_data(BMP280.ADDR, BMP280.P5_LSB)
        self.P6=self.i2c.read_word_data(BMP280.ADDR, BMP280.P6_LSB)
        self.P7=self.i2c.read_word_data(BMP280.ADDR, BMP280.P7_LSB)
        self.P8=self.i2c.read_word_data(BMP280.ADDR, BMP280.P8_LSB)
        self.P9=self.i2c.read_word_data(BMP280.ADDR, BMP280.P9_LSB)
        '''
        self.T1=27504
        self.T2=26435
        self.T3=-1000
        self.P1=36477
        self.P2=-10685
        self.P3=3024
        self.P4=2855
        self.P5=140
        self.P6=-7
        self.P7=15500
        self.P8=-14600
        self.P9=6000
        '''

    def debugp(self,text):
        print(text)         #or pass

    def reserved(self):
        VERSION_REG=0xD1  #ML(mask=0x0F), AL(mask=0xF0)
        RESET_REG=0xE0    #Reset register, write_byte_data CMD_RESET
        CONFIG_REG=0xF4   #OSS(0|1|2|3<<6)+STARTBIT<<5+MEAU_CTRL
        ADC_MSB=0xF6      #Raw ADC output
        ADC_LSB=0xF7      #Raw ADC output
        ADC_XLSB=0xF8     #Raw ADC output

        #BMP180 CONFIG Commands, (command, delay in seconds)
        CMD_TEMP=(0x2E, 0.0045)       #Temperature: 
        CMD_PRES_ULP=(0x34, 0.0045)   #Pressure: Ultra Low Power
        CMD_PRES_STD=(0x74, 0.0075)   #Pressure: Standard
        CMD_PRES_HIR=(0xB4, 0.0135)   #Pressure: High Resolution
        CMD_PRES_UHR=(0xF4, 0.0255)   #Pressure: Ultra High Resolution
        CMD_RESET=0xB6                #write to RESET_REG for "power on reset" behavior
        CMD_OSS_MASK=0xC0             #Command field (oversampling ratio)
        CMD_START_MASK=0x20           #Command field (Start a conversion)
        CMD_MEAU_MASK=0x1F            #Command field (Measurement control)
        CMD_OSS_RSHIFT=6              #Normalize the OSS field (right shift)

    def getChipID(self):        #should always be self.BMP280_ID (0x58)
        result = self.i2c.read_byte_data(BMP280.ADDR, BMP280.ID_REG)
        #result=0x58
        #self.debugp("Chip_ID=" + hex(result))
        return result

    def beginMeasurement(self, osrs_t=1, osrs_p=1):
        self.i2c.write_byte_data(BMP280.ADDR, BMP280.CONFIG_REG, 0)
        self.i2c.write_byte_data(BMP280.ADDR, BMP280.CONTROL_REG, \
                                ((osrs_t & 7)<<5) + ((osrs_p & 7)<<2) + 1)
        tick = tock = time.time()
        status = self.i2c.read_byte_data(BMP280.ADDR, BMP280.STATUS_REG)
        while (status & 0x09) != 0:
            #print 'delaying for sample, status=' + hex(status)
            status = self.i2c.read_byte_data(BMP280.ADDR, BMP280.CONTROL_REG)
        tick = time.time()            
        #print 'beginMeasurement complete, delay=' + str(tick-tock)                                 

    def getTemp(self):
        result=self.i2c.read_i2c_block_data(BMP280.ADDR, BMP280.TEMP_MSB, 3)
        adc_T = (result[0]<<12) + (result[1]<<4) + (result[2]>>4)
        #adc_T = 519888
        self.debugp("RAW Temperature=" + str(adc_T))

        #solution from datasheet section 8.1 (floating point)
        var1=((adc_T/16384.0)-(self.T1/1024.0))*self.T2
        var2=((  ((adc_T/131072.0)-(self.T1/8192.0))  \
               * ((adc_T/131072.0)-(self.T1/8192.0))  \
              )     \
             ) * self.T3
        self.t_fine=(int)(var1+var2)
        T=(var1+var2)/5120.0
        
        #solution from datasheet section 8.2 (32-bit integer)
        var1=(((adc_T>>3) - (self.T1<<1)) * self.T2)>>11
        var2=(( (((adc_T>>4) - self.T1) * ((adc_T>>4) - self.T1) ) >> 12) \
              * self.T3) >> 14
        self.t_fine=var1+var2
        T=(self.t_fine * 5 + 128) >> 8
        #self.debugp("var1="+str(var1)+", var2="+str(var2)+", t_fine="+str(self.t_fine)) 
        #self.debugp("Computed Temperature (1/100 of C)=" + str(T) + \
        #            ",  " + str(((T * 9 / 5) + 3200)/100.0) + ' degrees fahrenheit.' )
        return T

    def getPressure(self):
        result=self.i2c.read_i2c_block_data(BMP280.ADDR, BMP280.PRESS_MSB, 3)
        adc_P = (result[0]<<12) + (result[1]<<4) + (result[2]>>4)
        #adc_P = 415148
        self.debugp("RAW Pressure=" + str(adc_P))

        #solution from datasheet section 8.1 (floating point)
        var1=(self.t_fine/2.0)-64000.0
        var2=var1 * var1 * self.P6 / 32768.0
        var2=var2 + var1 * self.P5 * 2.0
        var2=(var2/4.0) + self.P4 * 65536.0
        var1=(self.P3 * var1 * var1 / 524288.0 + (self.P2 * var1)) / 524288.0
        var1=(1.0 + var1 / 32768.0) * self.P1
        if var1 < 0.02 and var1 > -0.02:     #probably division by 0
            return 0
        p=1048576.0 - adc_P
        p=(p - (var2 / 4096.0)) * 6250.0 / var1
        var1= self.P9 * p * p /2147483648.0
        var2= p * self.P8 / 32768.0
        p= p + (var1 + var2 + self.P7) / 16.0

        #solution from datasheet section 8.2 (32-bit integer)
        var1=(self.t_fine>>1) - 64000
        var2=(((var1>>2) * (var1>>2))>>11) * self.P6
        var2=var2 + ((var1 * self.P6)<<1)
        var2=(var2>>2) + (self.P4 << 16)
        var1=( ( (self.P3 * (((var1>>2)*(var1>>2))>>13)>>3)     \
                 + ((self.P2 * var1)>>1) ) )>>18
        var1=((32768+var1) * self.P1) >>15
        if var1==0:
            return 0        #avoid divide by zero error
        p=((1048576 - adc_P) - (var2>>12)) * 3125
        if p < 0x80000000:
            p=(p<<1)/var1
        else:
            p=(p/var1) * 2
        var1=(self.P9 * (((p>>3) * (p>>3))>>13))>>12
        var2=((p>>2) * self.P8)>>13
        p=p+((var1+var2+self.P7)>>4)
 
        #self.debugp("Computed Pressure (in Pa)=" + str(p) +     \
        #            ', in millibar=' + str(p/100))
        return p


'''
MSB=i2c.read_byte_data(BMP180,AC1_MSB); LSB=i2c.read_byte_data(BMP180,AC1_LSB)
AC1=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,AC2_MSB); LSB=i2c.read_byte_data(BMP180,AC2_LSB)
AC2=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,AC3_MSB); LSB=i2c.read_byte_data(BMP180,AC3_LSB)
AC3=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,AC4_MSB); LSB=i2c.read_byte_data(BMP180,AC4_LSB)
AC4=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,AC5_MSB); LSB=i2c.read_byte_data(BMP180,AC5_LSB)
AC5=MSB*256+LSB
MSB=i2c.read_byte_d ata(BMP180,AC6_MSB); LSB=i2c.read_byte_data(BMP180,AC6_LSB)
AC6=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,B1_MSB); LSB=i2c.read_byte_data(BMP180,B1_LSB)
B1=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,B2_MSB); LSB=i2c.read_byte_data(BMP180,B2_LSB)
B2=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,MB_MSB); LSB=i2c.read_byte_data(BMP180,MB_LSB)
MB=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,MC_MSB); LSB=i2c.read_byte_data(BMP180,MC_LSB)
MC=MSB*256+LSB
MSB=i2c.read_byte_data(BMP180,MD_MSB); LSB=i2c.read_byte_data(BMP180,MD_LSB)
MD=MSB*256+LSB

tick=tock=time.time()
while( tick-tock < DELAY ):
    tick=time.time()
'''


if __name__ == '__main__':

    bmp = BMP280(BMP280.OSRS_X1, BMP280.OSRS_X1, BMP280.MODE_FORCE)
    print('ChipID=' + hex(bmp.getChipID()))
    bmp.beginMeasurement()
    print str(bmp.getTemp()) + ' (in 1/100 C)'
    print str(bmp.getPressure()) + ' (in Pa or 1/100 millibar)'


#THE End               

