#!/usr/bin/python
# -*- coding: utf-8 -*-

from mkblib   import hexField
from mkblib   import hexDump16
from mkblib   import Lock
from datetime import datetime
from datetime import timedelta
from datetime import tzinfo
import time
import smbus

foo = bytearray(28)

def     bin2BCD( bin ):
    return ((bin//10)<<4)+bin%10
    
def     BCD2bin( bcd ):
    return (10*(bcd>>4))+(bcd&0xF)
                    
            
class   RTC:
    DEBUG=False
    I2C1=smbus.SMBus(1)	    #RTC module is on the #1 i2c bus
    ADDR=0x68           #RTC device address, DS3231

    #RTC Device Registers   # range of values in BCD
    SEC=0                   # 0-59
    MIN=1                   # 0-59
    HRS=2                   # 0-23
    DAY=3                   # 1- 7  Where Monday==1
    DATE=4                  # 1-31
    MONTH=5                 # 1-12 + Century bit
    YEAR=6                  # 0-99
    A1_SEC=7                # 0-59          Alarm1
    A1_MIN=8                # 0-59
    A1_HRS=9                # 0-23
    A1_DAY_DATE=10          # 1- 7 | 1-31
    A2_MIN=11               # 0-59          Alarm2
    A2_HRS=12               # 0-23
    A2_DAY_DATE=13          # 1- 7 | 1-31
    CTRL=14
    STATUS=15
    OFFSET=16
    TEMP_MSB=17
    TEMP_LSB=18

    #RTC Bit Usage
    BUSY=0x4
    ALARM_SEC_MASK=0x7F
    ALARM_MIN_MASK=0x7F
    ALARM_HRS_MASK=0x3F
    ALARM_DAY_MASK=0x0F
    ALARM_DATE_MASK=0x3F
    ALARM_MONTH_MASK=0x1F
    ALARM_RATE_BIT=0x80
    ALARM_DYDT_BIT=0x40
    ALARM_USE_DATE=True
    
    def     __init__(self, checkOscStopped=True):
        if checkOscStopped and self.hasOscStopped():
            raise EnvironmentError(     \
                'The RTC oscillator has stopped, the time is untrusted.')            

#   def     __repr__(self):
#        return "RTC()"

    def     __str__(self):
        return "instance of class RTC"

    def     read(self, start, length):
        return RTC.I2C1.read_i2c_block_data(RTC.ADDR,start,length)

        #data=i2c.read_byte_data(RTC,SEC)           #OK, byte read

        #data=i2c.read_block_data(RTC,0)            #caused hang

        #data=i2c.read_word_data(RTC,TEMP_MSB)      #wrong endian

    def     write(self, start, array):
        return RTC.I2C1.write_i2c_block_data(RTC.ADDR,start,array)

    def     isBusy(self):                   #status:2
        status=self.read(RTC.STATUS,1)
        if status[0]&RTC.BUSY:
            return True
        else:
            return False

    def     isAlarmed(self,alarmNum):       #status:alarmNum
        status=self.read(RTC.STATUS,1)
        if alarmNum < 1 or alarmNum > 2:
            return None
        elif status[0]&alarmNum:
            return True
        else:
            return False

    def     resetAlarm(self,alarmNum):
        status=self.read(RTC.STATUS,1)
        if alarmNum < 1 or alarmNum > 2:
            return None
        elif status[0]&alarmNum:
            result=True
        else:
            result=False
        aray=[status[0]&~alarmNum]
        self.write(RTC.STATUS,aray)
        return result

    def     hasOscStopped(self):            #status:7
        status=self.read(RTC.STATUS,1)
        if status[0]&0x80:
            return True
        else:
            return False

    def     resetOscStopped(self):
        status=self.read(RTC.STATUS,1)
        aray=[status[0]&0x7F]
        self.write(RTC.STATUS,aray)
        if status[0]&0x80:
            return True
        else:
            return False

    def     setInterrupt(self,alarmNum,bool):   #ctrl:alarmNum + bit 2
        ctrl=self.read(RTC.CTRL,1)
        if alarmNum < 1 or alarmNum > 2:
            return None
        elif bool:
            ctrl[0] |= alarmNum
        else:
            ctrl[0] & ~alarmNum
        aray=[ctrl[0]]
        self.write(RTC.CTRL,aray)
        return True

    def     set32kHzOut(self,bool):             #status:3
        status=self.read(RTC.STATUS,1)
        if bool:
            status[0] |= 8
        else:
            status[0] &= 0xF7
        aray=[status[0]]
        self.write(RTC.STATUS,aray)
        return True
    
    def     dumpRegs(self):
        aray=self.read(0,19)
        raw=[]
        for i in range(14,len(aray)): raw.append(hex(aray[i]));
        print("REGS[ctrl,status,Age,temp+,temp-]=",raw)
        del raw[:]
        for i in range(7): raw.append(hex(aray[i]));
        print("clock[ss,mm,hh,dy,dt,mm,yr]=",raw)
        del raw[:]
        for i in range(7,11): raw.append(hex(aray[i]));
        print("Alarm1[ss,mm,hh,dy/dt]=",raw)
        del raw[:]
        for i in range(11,14): raw.append(hex(aray[i]));
        print("Alarm2[mm,hh,dy/dt]=",raw)

    def  dayAsString(self, dn ):    #python datetime has Monday as 0!
        if dn==1:
            result="Monday"
        elif dn==2:
            result="Tuesday"
        elif dn==3:
            result="Wednesday"
        elif dn==4:
            result="Thursday"
        elif dn==5:
            result="Friday"
        elif dn==6:
            result="Saturday"
        elif dn==7:
            result="Sunday"
        else:
            result="BadDayValue=="+str(dn)      
        return result

    def     getAlarm1AsString(self):
        #Report Alarm1 settings
        a1=self.read(RTC.A1_SEC,4)    #Alarm1 data
        raw=[]
        for i in range(0, len(a1)): raw.append(hex(a1[i]));
        print("Alarm1 raw ss:mm:hh:DY/DT==", raw)       #raw data, ss:mm:hh:DY/DT
        mask=0
        if a1[0]&0x80: mask+=1;
        if a1[1]&0x80: mask+=2;
        if a1[2]&0x80: mask+=4;
        if a1[3]&0x80: mask+=8;
        if  mask==0x0F:
            t1="Alarm1 once per second (when seconds==0)."
        elif mask==0x0E:
            t1="Alarm1 when seconds==" + hex(a1[0]&0x7F)[2:] + " match."
        elif mask==0x0C:
            t1="Alarm1 when mm:ss==" + hex(a1[1]&0x7F)[2:] + ':' + \
                hex(a1[0]&0x7F)[2:] + " match."
        elif mask==0x08:
            t1="Alarm1 when hh:mm:ss==" + hex(a1[2]&0x3F)[2:] + ':' +  \
                hex(a1[1]&0x7F)[2:] + ':' + hex(a1[0]&0x7F)[2:] + " match."
        elif mask==0:
            if a1[3]&0x40:
                dn=al[3]&0x0F
                t1="Alarm1 when Day:hh:mm:ss==" + dayAsString(dn) + ':' + \
                  hex(a1[2]&0x3F)[2:] + ':' + hex(a1[1]&0x7F)[2:] + ':' + \
                  hex(a1[0]&0x7F)[2:] +" match."   
            else:
                t1="Alarm1 when Date:hh:mm:ss==" + hex(a1[3]&0x3F)[2:] + ':' + \
                  hex(a1[2]&0x3F)[2:] + ':' + hex(a1[1]&0x7F)[2:] + ':' +   \
                  hex(a1[0]&0x7F)[2:] + " match."
        else:
            t1="Alarm1 invalid mask=="+hex(mask)
        return t1   #report Alarm1 settings

    def     getAlarm2AsString(self):
        #Report Alarm2 settings
        a2=self.read(RTC.A2_MIN,3)    #Alarm2 data
        raw=[]
        for i in range(0, len(a2)): raw.append(hex(a2[i]));
        print("Alarm2 raw mm:hh:DY/DT==", raw)       #raw data, mm:hh:DY/DT
        mask=0
        if a2[0]&0x80: mask+=1;
        if a2[1]&0x80: mask+=2;
        if a2[2]&0x80: mask+=4;
        if  mask==7:
            t1="Alarm2 once per minute (at seconds==00).";
        elif mask==3:
            t1="Alarm2 when minutes==" + hex(a2[0]&0x7F)[2:] + " match."
        elif mask==1:
            t1="Alarm2 when hh:mm==" + hex(a2[1]&0x3F)[2:] + ':' + \
                hex(a2[0]&0x7F)[2:] + " match."
        elif mask==0:
            if a2[2]&0x40:
                dn=a2[2]&0x0F
                t1="Alarm2 when Day:hh:mm==" + dayAsString(dn) + ':' + \
                   hex(a2[1]&0x3F)[2:] + ':' + hex(a2[0]&0x7F)[2:] + " match."   
            else:
                t1="Alarm2 when Date:hh:mm==" + hex(a2[2]&0x3F)[2:] + ':' + \
                   hex(a2[1]&0x3F)[2:] + ':' + hex(a2[0]&0x7F)[2:] + " match."
        else:
            t1="Alarm2 invalid mask=="+hex(mask)
        return t1       #print Alarm2 setting

    def     setClock(self, dateTime):
        regs = self.read(RTC.CTRL, 2)       #get CTRL and STATUS
        noInterrupts = [regs[0] & 0xFC]     #clear interrupt enable
        self.write(RTC.CTRL, noInterrupts)
        now=[ bin2BCD(dateTime.second)       \
            , bin2BCD(dateTime.minute)       \
            , bin2BCD(dateTime.hour)         \
            , bin2BCD(dateTime.weekday()+1)  \
            , bin2BCD(dateTime.day)          \
            , bin2BCD(dateTime.month)        \
            , bin2BCD(dateTime.year%100) ]
        #bcd=[]
        #for i in range(len(now)):
        #    bcd.append(hexField(now[i]))
        #print('setClock[ss,mm,hh,dy,dt,mm,yy]=', bcd)
        self.write(RTC.SEC, now)
        regs[1] &= 0xFC             
        self.write(RTC.STATUS, regs[1:])  #clear alarms
        self.write(RTC.CTRL, regs[:1])    #restore interrupts

    def     setAlarm1(self, dateTime, alarm_mask):
        ##  alarm_mask== LSB to MSB { A1M1, A1M2, A1M3, A1M4, DY/DT }
        regs = self.read(RTC.CTRL, 2)       #get CTRL and STATUS
        noInterrupts = [regs[0] & 0xFE]     #clear interrupt enable
        self.write(RTC.CTRL, noInterrupts)
        mask = alarm_mask & 0xF
        if mask==0xF or mask==0xE or mask==0xC or mask==8 or mask==0:
            if alarm_mask & 0x10:
                dayDate=dateTime.weekday()+1    #the weekday option
            else:
                dayDate=bin2BCD(dateTime.day)   #the date option
        else:
            return None
        now=[ ((mask&1)<<7)+bin2BCD(dateTime.second)     \
            , ((mask&2)<<6)+bin2BCD(dateTime.minute)     \
            , ((mask&4)<<5)+bin2BCD(dateTime.hour)       \
            , ((mask&8)<<4)+((alarm_mask&0x10)<<2)+dayDate ]
        print('alarm1 data=', now)
        self.write(RTC.A1_SEC,now)
        regs[1] &= 0xFE             
        self.write(RTC.STATUS, regs[1:])    #clear alarm
        self.write(RTC.CTRL, regs[:1])      #restore interrupts

    def     setAlarm2(self, dateTime, alarm_mask):
        ##  alarm_mask== LSB to MSB { A2M2, A2M3, A2M4, DY/DT }
        regs = self.read(RTC.CTRL, 2)       #get CTRL and STATUS
        noInterrupts = [regs[0] & 0xFD]     #clear interrupt enable
        self.write(RTC.CTRL, noInterrupts)
        mask=alarm_mask&7      #is the alarm_mask legal?
        if mask==7 or mask==6 or mask==4 or mask==0:
            if alarm_mask & 8:
                dayDate=dateTime.weekday()+1    #the weekday option
            else:
                dayDate=bin2BCD(dateTime.day)   #the date option
        else:
            return None
        now=[ ((mask&1)<<7)+bin2BCD(dateTime.minute)     \
            , ((mask&2)<<6)+bin2BCD(dateTime.hour)       \
            , ((mask&4)<<5)+((alarm_mask&8)<<3)+dayDate ]
        print('alarm2 data=', now)
        self.write(RTC.A2_MIN,now)      
        regs[1] &= 0xFD 
        self.write(RTC.STATUS, regs[1:])    #clear alarm
        self.write(RTC.CTRL, regs[:1])      #restore interrupts

    def     getRTCtemp(self, inCelsius=True):    #if inCelsius is false then fahrenheit
        atemp=self.read(RTC.TEMP_MSB,2)
        temp=((atemp[0]*256+atemp[1])>>6)*0.25
        if inCelsius:
            return temp
        else:
            return temp*9/5+32       

    def     getDatetime(self):     
        atime=self.read(RTC.SEC,7)
        #atime[sec,min,hr,day,date,mon,year]    Convert BCD to binary
        if RTC.DEBUG==True:
            bcd=[]
            for i in range(len(atime)):
                bcd.append(hexField(atime[i]))
            print('getDatetime[ss,mm,hh,dy,dt,MM,YY]=', bcd)        
        dt=datetime( 2000+BCD2bin(atime[6])                     \
                   , BCD2bin(atime[5]&RTC.ALARM_MONTH_MASK)     \
                   , BCD2bin(atime[4]&RTC.ALARM_DATE_MASK)      \
                   , BCD2bin(atime[2]&RTC.ALARM_HRS_MASK)       \
                   , BCD2bin(atime[1]&RTC.ALARM_MIN_MASK)       \
                   , BCD2bin(atime[0]&RTC.ALARM_SEC_MASK) )
        return dt
        
        
'''
class SMBus(__builtin__.object)
     |  SMBus([bus]) -> SMBus
     |  
     |  
     |  read_byte(...)
     |      read_byte(addr) -> result
     |      
     |      Perform SMBus Read Byte transaction.
     |  
     |  read_byte_data(...)
     |      read_byte_data(addr, cmd) -> result
     |      
     |      Perform SMBus Read Byte Data transaction.
     |  
     |  read_i2c_block_data(...)
     |      read_i2c_block_data(addr, cmd, len=32) -> results
     |      
     |      Perform I2C Block Read transaction.
     |  
     |  write_byte(...)
     |      write_byte(addr, val)
     |      
     |      Perform SMBus Write Byte transaction.
     |  
     |  write_byte_data(...)
     |      write_byte_data(addr, cmd, val)
     |      
     |      Perform SMBus Write Byte Data transaction.
     |  
     |  write_i2c_block_data(...)
     |      write_i2c_block_data(addr, cmd, [vals])
     |      
     |      Perform I2C Block Write transaction.
     |  
     
i2c.write_i2c_block_data(MEM,0x0F,[0xF8,    \
   35,84,104,101,32,69,110,100,83,116,97,114,116,76,97,115,116,80,97,103,101,46] )
   #  T  h   e      E  n   d   S  t   a  r   t   L  a  s   t   P  a  g   e   .  

tick=tock=time.time()
while( tick-tock < .005 ):
    tick = time.time()

# Hex Dump 32K EEPROM
i2c.write_byte_data(MEM,0,0) #start address=0
for i in range(0,256):       #lines
    data=[]
    for j in range(0,16):
        data.append(i2c.read_byte(MEM))
    print( hexDump16( 16*i, data ))    

interval=1
tick=tock=time.time()
for i in range(1,3600):
    while( tick-tock < interval ):     #delay 
        tick=time.time()
    while( i2c.read_byte_data(RTC,STATUS) & BUSY_BIT ):
        tick=time.time()
    aray=i2c.read_i2c_block_data(RTC,0,7)
    for j in range(0,len(aray)):
        aray[j] = hex(aray[j])[2:]
    print( 'Tick['+str(i)+ ']', aray )
    tock=tick
    
'''



if __name__ == '__main__':

    def getInt( prompt, min, max ):
        #print 'min='+hex(min)+', max='+hex(max)
        result = min - 1
        while result < min or result > max:
            reply = raw_input( prompt )
            result = int( reply )
        return result

    def getDT( ):
        reply = ''
        while reply == '':
            reply = raw_input( 'What time, in the form YYYY-MM-DD hh:mm:ss?  ' )
            print '('+reply+')'
            try:
                dt = datetime.strptime( reply, '%Y-%m-%d %H:%M:%S' )
            except ValueError as ve:
                reply = ''
        return dt

    def getAlarmMask( alarm ):
        reply = -1
        if alarm == 1:
            opt = [15, 14, 12, 8, 0, 16]
            prompt = 'every sec or sec match or min+sec or hr+min+sec or date+HMS or day+HMS match.  '
        else:
            opt = [7, 6, 4, 0, 8 ]
            prompt = 'every min or min match or hr+min or date+HM or day+HM match.'
        while reply not in opt:
            print 'Choose from ' + str(opt) + ', description follows in order...'
            reply = int(raw_input( prompt ))
        return reply


    print 'Welcome to the testing controller.'
    selection = 'r'
    test = 0
    if selection == 'r':
        rtc = RTC()
        while not (test == 'q' or test == 'Q'):
            test = 0
            while test <= 0 or test > 16:
                print "test  1 = getDatetime(),       test  2 = getRTCtemp()"
                print "test  3 = getAlarm1AsString(), test  4 = getAlarm2AsString()"
                print "test  5 = dumpRegs(),          test  6 = isBusy()"
                print "test  7 = hasOscStopped(),     test  8 = resetOscStopped()"
                print "test  9 = isAlarmed(?),        test 10 = resetAlarm(?)"
                print "test 11 = dayAsString(?),      test 12 = set32KhzOut(?)"
                print "test 13 = setClock(?),         test 14 = setInterrupt(?)"
                print "test 15 = setAlarm1(?),        test 16 = setAlarm2(?)"
                test = raw_input( 'Reply with desired test # or Q to quit ' )
                if test == 'q' or test == 'Q':
                    break
                test = int(test)
            if test == 1:
                print "RealTimeClock time is " + str(rtc.getDatetime())            
            elif test == 2:
                print "RealTimeClock temperature is (in C) " + str(rtc.getRTCtemp())
            elif test == 3:
                print rtc.getAlarm1AsString()
            elif test == 4:
                print rtc.getAlarm2AsString()
            elif test == 5:
                rtc.dumpRegs()
            elif test == 6:
                if rtc.isBusy() is True:
                    print 'RealTimeClock IS busy.'
                else:
                    print 'RealTimeClock is NOT busy.' 
            elif test == 7:
                if rtc.hasOscStopped() is True:
                    print 'RealTimeClock oscillator has stopped.'
                else:
                    print 'RealTimeClock oscillator has NOT stopped.' 
            elif test == 8:
                rtc.resetOscStopped()
                print 'RealTimeClock oscillator stopped flag was cleared.'
            elif test == 9:
                alarm = getInt( "Which alarm? reply with 1 or 2.  ", 1, 2 )
                if rtc.isAlarmed( alarm ) is True:
                    print 'Alarm ' + str(alarm) + ' is alarmed.'
                else:
                    print 'Alarm ' + str(alarm) + ' is NOT alarmed.' 
            elif test == 10:
                alarm = getInt( "Which alarm? reply with 1 or 2.  ", 1, 2 )
                rtc.resetAlarm( alarm )
            elif test == 11:
                day = getInt( "What day #?  1 to 7 are defined.  ", 0, 99 )
                print 'Day ' + str(day) + ' is ' + rtc.dayAsString(day) +'.'
            elif test == 12:
                tf = getInt( 'Enable(1)/Disable(0) 32kHz out, reply 1 or 0.  ', 0, 1 )
                if tf == 0:
                    rtc.set32kHzOut( False )
                else:
                    rtc.set32kHzOut( True )
            elif test == 13:
                dt = getDT()             
                rtc.setClock( dt )
                print 'RealTimeClock time set to ' + str(dt)
            elif test == 14:
                alarm = getInt( "Which alarm? reply with 1 or 2.  ", 1, 2 )
                tf = getInt( 'Enable(1)/Disable(0) interrupt, reply 1 or 0.  ', 0, 1 )
                if tf == 0:
                    rtc.setInterrupt( alarm, False )
                    print 'Alarm ' + str(alarm) + ' will NOT trigger interrupts.'
                else:
                    rtc.setInterrupt( alarm, True )
                    print 'Alarm ' + str(alarm) + ' will trigger interrupts.'
            elif test == 15:
                dt = getDT()
                mask = getAlarmMask( 1 )                             
                rtc.setAlarm1( dt, mask)
                print 'Alarm1 set, use test #3 to see detail.'
            elif test == 16:
                dt = getDT()
                mask = getAlarmMask( 2 )    
                rtc.setAlarm2( dt, mask )
                print 'Alarm2 set, use test #4 to see detail.'
    
#THE End               
