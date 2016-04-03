#!/usr/bin/python
# -*- coding: utf-8 -*-

from mkblib   import hexField
from mkblib   import hexDump16
from mkblib   import Lock
from datetime import datetime
from datetime import timedelta
from datetime import tzinfo
import os
import time
import smbus

foo = bytearray(28)     


class   Buffer:
    MEM = 0
    I2C = 1
    FILE = 2
    I2C1=smbus.SMBus(1)         #DS3231 EEPROM on Rpi #1 i2c bus
    def     __init__(self, pgSz, addr, allocSize):
        self.pgSz = pgSz
        self.buf = [0] * (pgSz+1)   #needs to be a int list
        self.store = None
        self.devAddr = None
        self.filename = None
        self.handle = None
        if type(addr) == bytearray:
            self.store = addr
            self.choice = Buffer.MEM
            self.storeSize = len(addr)
        elif type(addr) == int:
            self.devAddr = addr
            self.choice = Buffer.I2C
            self.storeSize = allocSize
        else:
            self.filename = addr
            self.choice = Buffer.FILE
            self.storeSize = os.path.getsize( self.filename )
            self.handle = open( self.filename, 'rb+' )
        self.startAddr = -1
        self.next = 0
        self.lastWrTime = 0
        self.dirty = False
        self.lock = Lock( 'intlog.lock' )

    def     __del__(self):
        if self.choice == Buffer.FILE:
            self.handle.close()

    def     prnObjState(self):
        print "BUF.startAddr=" + hex(self.startAddr)  \
               + ", next=" + hex(self.next)          \
               + ", pgSz=" + str(self.pgSz)         \
               + ", dirty=" + str(self.dirty)
        for i in range( 0, self.pgSz, 16 ): 
            print hexDump16( i, self.buf[i:i+16])
        if self.choice == Buffer.MEM:
            print "BUF.store contains..."
            for i in range(0, len(self.store), 16):
                tail = len(self.store) - i
                if tail > 16:
                    print hexDump16( i, self.store[i:16+i])
                else:
                    print hexDump16( i, self.store[i:tail+i])
                           
    def     write(self, startAddr, abytes, flush=False):
        print "WRT$ " + hexDump16(startAddr,abytes)
        if self.dirty:
            pgmask = ~(self.pgSz-1)
            if (startAddr & self.pgSz - 1 != self.next) or  \
                   (self.startAddr & pgmask != startAddr & pgmask):
                self.flush()
                self.startAddr = startAddr
                self.next = startAddr & self.pgSz - 1     
        else:
            self.startAddr = startAddr
            self.next = startAddr & self.pgSz - 1   
        self.put( abytes, flush )
        
    def     put(self, abytes, flush=False):
        for i in range( len(abytes)):
            self.buf[self.next+1] = abytes[i]
            self.dirty = True
            self.next += 1
            if self.next == self.pgSz:
                self.flush()
                self.next = self.startAddr & self.pgSz - 1 
        if flush:
            self.flush()


    def     flush(self):
        if self.next == (self.startAddr & self.pgSz - 1):
            print 'aborted flush'
            return
        tick=time.time()
        while( tick-self.lastWrTime < .010 ):
            tick = time.time()
        self.prnObjState()  #for debug
        self.lock.acquire()
        if self.choice == Buffer.MEM:    
            for i in range((self.startAddr & self.pgSz - 1),self.next):
                self.store[self.startAddr] = self.buf[i+1]
                self.startAddr += 1
        elif self.choice == Buffer.I2C:
            self.buf[self.startAddr&self.pgSz-1] = self.startAddr & 0xFF
            bytes = self.buf[self.startAddr & self.pgSz - 1:self.next+1]
            print 'OUT$ ' + hexDump16( self.startAddr, bytes )
            Buffer.I2C1.write_i2c_block_data(       \
                    self.devAddr,                   \
                    self.startAddr >> 8 & 0xFF,     \
                    bytes )
        elif self.choice == Buffer.FILE:
            #where = self.fh.tell()
            #if where != self.startAddr:
            self.handle.seek( self.startAddr, os.SEEK_SET )
            bytearay = bytearray( self.buf[1+(self.startAddr & self.pgSz - 1):self.next+1] )
            self.handle.write( bytearay )
            self.handle.flush()
        self.lock.release()
        self.lastWrTime = time.time()
        self.dirty = False
        print "flush complete"
                
    def     read( self, startAddr, count):
        results = []
        self.lock.acquire()
        if self.choice == Buffer.MEM:
            for i in range(startAddr, startAddr+count):
                results.append(self.store[i])
        elif self.choice == Buffer.I2C:
            Buffer.I2C1.write_byte_data(self.devAddr,startAddr>>8,startAddr&0xFF)
            for j in range(count):
                results.append(Buffer.I2C1.read_byte(self.devAddr))
        elif self.choice == Buffer.FILE:
            self.handle.seek( startAddr, os.SEEK_SET )
            asStr = self.handle.read( count )
            for i in range( len(asStr)):
                results.append( ord(asStr[i]) )
        self.lock.release()
        return results
        
        
EMPTY_BYTE = 0xC0        
HEADERSIZE   = 8
DIRFLAGMASK = 0x80
DIRFLAGADDR = 0
MSBINTERVALADDR = 0
LSBINTERVALADDR = 1
BUCKETSIZEADDR = 1
BUCKETSIZEMASK = 0x0F
BUCKET0ADDR = 8

""" Storage layout:
        header[0] : Most significant 8 bits of bucket interval (in seconds)
        header[1] : Least significant 4 bits of bucket interval (upper nibble) 
        header[1] : bucket size (lower nibble)
        header[2] : bucket 0 time member - year 0-99 
        header[3] : bucket 0 time member - month 1-12
        header[4] : bucket 0 time member - day  1-max day
        header[5] : bucket 0 time member - hour 0-23
        header[6] : bucket 0 time member - minute 0-59
        header[7] : bucket 0 time member - second 0-59
        stor[8]   : MSB of bucket 0 - bit 7 is direction flag
        stor[x]   :    part of bucket
        stor[last]: LSB of last bucket
"""

class   PeriodicLog:     
    """ A circular log of buckets, datetime determines storage bucket.  

        Expected to be used to persist real time data (data logging).
        The self.format method sets the period and data size for
        the buckets. An empty bucket is indicated by [0xC0, 0xC000, 
        0xC00000, ...] for bucketSize of 1, 2, 3, ...
        A bucket holds a single signed integer of [0xC0+1 to 0x3F, 
        0xC000+1 to 0x3f00, 0xC00000+1 to 0x3F0000, ...] for bucketSize
        of 1, 2, 3, ...        
                        
    """
    
    def     __init__(self, addr=0x57, pgSz=32, alloc=4096, readOnly=False):
        """ A circular log of buckets, timestamp determines storage bucket.
        
            Args:
                addr:  if bytearray[] then use as backing store
                       if 0-0x7F then use I2C/EEPROM for backing store
                       if filename then use named file for backing store
                pgSz:  size limit/alignment of writes to backing store.
                alloc: size of data store in bytes
                readOnly: disable self.buf.write from writing to backing store
                
            Return:
                Initialized instance of class
                
            Exceptions:
                None.
        """
        if type(addr) == bytearray:
            self.alloc = len(addr)
        else:
            self.alloc = alloc
            
        self.buf = Buffer(pgSz, addr, self.alloc)
        self.readOnly = readOnly
        self.cache = bytearray(10)
        
        # read the full header + bucket0 byte 0 to get the fwdFlag
        header = self.buf.read( 0, HEADERSIZE +1 )  
        print 'CTOR.header ' + hexDump16( 0, header )
        self.bcktSize = (header[BUCKETSIZEADDR] & BUCKETSIZEMASK)
        if self.bcktSize == 0: self.bcktSize = 1
        self.interval = timedelta( seconds=(header[MSBINTERVALADDR] << 4) +
                (header[LSBINTERVALADDR]>>4))
        self.lastRingBckt = ((self.alloc - HEADERSIZE) // self.bcktSize) - 1
        try:
            if header[2] == 0xFF:       #test left by format
                raise ValueError()
            self.lastWrDttm = datetime( 2000 + header[2], header[3],   #\
                header[4], header[5], header[6], header[7] )
        except ValueError:
            print 'PeriodicLog:__init__ no history.'
            self.lastWrBckt = self.lastRingBckt
            self.availBckts = 0
            self.lastWrDttm = None
            self.fwdFlag = 0x80
            return
        self.fwdFlag = header[BUCKET0ADDR] & DIRFLAGMASK
        self.lastWrBckt = 0
        self.availBckts = 1
        while self.lastWrBckt < self.lastRingBckt:     #scan forward
            dirAddr = (self.lastWrBckt + 1) * self.bcktSize + HEADERSIZE
            dirFlag = self.buf.read( dirAddr, 1 )
            if dirFlag[DIRFLAGADDR] & DIRFLAGMASK == self.fwdFlag:
                self.lastWrDttm += self.interval
                self.lastWrBckt += 1        
                self.availBckts += 1
            else:
                break
        print "scan FWd self.lastWrBckt=" + hex(self.lastWrBckt) 
        revFlag = self.fwdFlag ^ DIRFLAGMASK
        revBckt = self.lastRingBckt     #scan backward for availability
        while True:
            dirAddr = revBckt * self.bcktSize + HEADERSIZE
            dirFlag = self.buf.read( dirAddr, 1 )
            if dirFlag[DIRFLAGADDR] & DIRFLAGMASK == revFlag:
                self.availBckts += 1
                revBckt -= 1
            else:
                break
        print "avail buckets=" + hex(self.lastWrBckt) 
                
    def     prnObjState(self):
        print "ROM.bcktSize="+str(self.bcktSize)    \
            + ", interval="+str(self.interval)      \
            + ", alloc="+str(self.alloc)            \
            + ", extra="+str("does not apply")
        print "ROM.lastWrBkt="+str(self.lastWrBckt) \
            + ", availBckts="+str(self.availBckts)  \
            + ", fwdFlag=" + hex(self.fwdFlag)      \
            + ", lastRingBckt=" + str(self.lastRingBckt)
        print "ROM.lastWrDttm="+str(self.lastWrDttm)
        print "ROM.cache=" + hexDump16( 0, self.cache)
        self.buf.prnObjState()
                
    def     format(self, timeDelta, bcktSize):
        assert bcktSize > 0 and bcktSize <= 8, 'Invalid bcktSize arg'
        spec = (int(timeDelta.total_seconds())<<4) + bcktSize
        self.cache[0] = (spec >> 8 )& 0xFF #store things big endian
        self.cache[1] = spec & 0xFF
        self.cache[2] = 0xFF               # add signal for no data written
        self.buf.write(0, self.cache[0:3], True)
        
    def     bucketDelta(self, dateTime):
        td = dateTime - self.lastWrDttm
        seconds = int(td.total_seconds()) 
        result = seconds / int(self.interval.total_seconds())
        print "bucketDelta td="+str(td)+", seconds="+str(seconds)+ \
               ", delta="+str(result)
        return result

    def     getBucket(self, bcktDelta):
        if bcktDelta > 0 or abs(bcktDelta) <= self.lastWrBckt:
            bucket = self.lastWrBckt + bcktDelta
        else:
            bucket = self.lastRingBckt + bcktDelta + self.lastWrBckt + 1
        if bucket > self.lastRingBckt:
            bucket %= (self.lastRingBckt+1)
        return bucket
            
    def     fetch( self, dateTime, count=1):      #count > 1 return older
        bcktDelta = self.bucketDelta( dateTime )
        result = []
        if bcktDelta > 0:
            return result           #no elements available from the future
        elif abs(bcktDelta-1) > self.availBckts:
            return result           #asking for to old a bucket
        while ( count > 0 ):
            bucket = self.getBucket(bcktDelta)
            addr = bucket * self.bcktSize + HEADERSIZE
            eray = self.buf.read( addr, self.bcktSize )
            if (eray[DIRFLAGADDR] & 0x40) == 0:     #copy bit 6 to bit 7
                eray[0] &= 0x7F
            else:
                eray[0] |= 0x80
            value = 0
            for i in range( self.bcktSize ):
                value += eray[i] << 8 * (self.bcktSize - i - 1)
            result.append( value )
            count -= 1
            bcktDelta -= 1         #next older bucket
            #print 'count='+str(count)+', bcktDelta='+str(bcktDelta)
            if abs(bcktDelta-1) > self.availBckts:
                return result
        return result

    def     setAnchor(self, dateTime, aray):
        self.cache[0] = dateTime.year - 2000
        self.cache[1] = dateTime.month
        self.cache[2] = dateTime.day
        self.cache[3] = dateTime.hour
        self.cache[4] = dateTime.minute
        self.cache[5] = dateTime.second
        self.fwdFlag ^= 0x80
        for i in range( self.bcktSize ):
            self.cache[6+i] = ((aray[0] >> (8 * (self.bcktSize -i -1)))) & 0xFF
        if self.fwdFlag & 0x80 == 0x80:
            self.cache[6] |= 0x80
        else:
            self.cache[6] &= 0x7F
        self.buf.write( 2, self.cache[0:(6+self.bcktSize)], True )
        if self.availBckts <= self.lastRingBckt: self.availBckts += 1
        self.lastWrBckt = 0
        self.lastWrDttm = dateTime
        
            
    def     store(self, dateTime, aray):
        if self.availBckts == 0:
            td = timedelta( seconds = int(self.interval.total_seconds()) / 2 )
            self.setAnchor( dateTime-td, aray )
            return
        bcktDelta = self.bucketDelta(dateTime)
        if bcktDelta < 0:       #can't store to the past
            return
        elif bcktDelta == 0:
            for i in range( self.bcktSize ):
                self.cache[i] = (aray[0] >> 8 * (self.bcktSize -i -1)) & 0xFF
            if self.fwdFlag & 0x80 == 0x80:
                self.cache[0] |= 0x80
            else:
                self.cache[0] &= 0x7F
            self.buf.write( self.lastWrBckt*self.bcktSize+8, self.cache[:3], True )
            return
        elif bcktDelta == 1 and self.lastWrBckt == self.lastRingBckt:
            self.setAnchor( self.lastWrDttm+self.interval, aray )
            return
        elif bcktDelta > self.lastRingBckt: 
            td = timedelta( seconds = int(self.interval.total_seconds()) / 2 )
            self.setAnchor( dateTime-td, aray )
            return
        while bcktDelta > 1:
            if self.lastWrBckt == self.lastRingBckt:
                empty = EMPTY_BYTE << 8 * (self.bcktSize -1)
                self.setAnchor( self.lastWrDttm+self.interval, [empty] )  
            else:
                data = EMPTY_BYTE << 8 * (self.bcktSize -1)
                for i in range( self.bcktSize ):
                    self.cache[i] = (data >> 8 * (self.bcktSize -i -1)) & 0xFF
                if self.fwdFlag & 0x80 == 0x80:
                    self.cache[0] |= 0x80
                else:
                    self.cache[0] &= 0x7F
                self.lastWrBckt += 1
                self.lastWrDttm += self.interval
                bcktAddr = self.lastWrBckt*self.bcktSize+8
                self.buf.write( bcktAddr, self.cache[:3] )
                if self.availBckts <= self.lastRingBckt: self.availBckts += 1
            bcktDelta -= 1 
        # update with aray data
        for i in range( self.bcktSize ):
            self.cache[i] = (aray[0] >> 8 * (self.bcktSize -i -1)) & 0xFF
        if self.fwdFlag & 0x80 == 0x80:
            self.cache[0] |= 0x80
        else:
            self.cache[0] &= 0x7F
        self.lastWrBckt = self.getBucket(bcktDelta)
        self.lastWrDttm += self.interval
        bcktAddr = self.lastWrBckt*self.bcktSize+8
        self.buf.write( bcktAddr, self.cache[:self.bcktSize], True )
        if self.availBckts <= self.lastRingBckt: self.availBckts += 1
        return           

        
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

    print 'Welcome to the testing controller.'
    selection = '?'
    while not (selection == 'l' or selection == 'b'):
        selection = raw_input(  \
            'Select by typing first character { Log, Buffer }  ' )
        selection = selection.lower()
    test = 0
    if selection == 'b':
        bfr = Buffer( pgSz=32, addr=0x57, allocSize=4096)
        while not (test == 'q' or test == 'Q'):
            test = 0
            while test <= 0 or test > 9:
                print "test  1 = printObjState(),   test  2 = read(?)"
                print "test  3 = write(?),          test  4 = put(?)"
                print "test  5 = flush(),           test  6 = ?"
                print "test  7 = SaveEEPROMtoFile,  test  8 = LoadEEPROMfromFile"
                print "test  9 = openFile"
                test = raw_input( 'Reply with desired test # or Q to quit ' )
                if test == 'q' or test == 'Q':
                    break
                test = int(test)
            if test == 1:
                bfr.prnObjState()
            elif test == 2:
                addr = getInt('Begin reading from addr?  ', 0, 100000)
                cnt = getInt('How many bytes to read?  ', 1, 256)
                result = bfr.read( addr, cnt )
                print result 
            elif test == 3:
                pass
            elif test == 4:
                pass                
            elif test == 5:
                pass
            elif test == 6:
                pass
            elif test == 7:
                fn = str( datetime.utcnow()) + '.intlog.data'
                with open( fn, 'wb', 0 ) as f:
                    f.write( bytearray( bfr.read( 0, bfr.storeSize )))
                print fn + ' save complete.'
            elif test == 8:
                pass
            elif test == 9:
                fbin = None
                try:
                    reply = raw_input( 'What path/filename? ' )
                    fbin = Buffer( pgSz=32, addr=reply, allocSize=0 )
                except Exception as ex:
                    print str(ex)
                else:           
                    data = fbin.read( 0, fbin.storeSize )
                    aray = []
                    for i in range( len(data)):
                        aray.append( ord(data[i]) )
                    print 'here is the data buffer...'
                    print aray[0:16]
                    print 'filesize=' + str(fbin.storeSize) + ', first 16 bytes...'
                    print hexDump16( 0, aray[0:16] )
                    fbin.write( 2, [ 1, 2, 3], True )
                    
                    data = fbin.read( 0, 16 )
                    aray = []
                    for i in range( len(data)):
                        aray.append( ord(data[i]) )
                    print hexDump16( 0, aray[0:16] )
                    
    elif selection == 'l':
        log = PeriodicLog()
        testLock = Lock( 'intlog.lock' )
        while not (test == 'q' or test == 'Q'):
            test = 0
            while test <= 0 or test > 8:
                print "test  1 = printObjState(),   test  2 = format(?)"
                print "test  3 = bucketDelta(?),    test  4 = getBucket(?)"
                print "test  5 = fetch(?),          test  6 = store(?)"
                print "test  7 = ByteView,          test  8 = LoggingView"
                print "test  9 = setAnchor(?),      test 10 = runExersizer()"
                test = raw_input( 'Reply with desired test # or Q to quit  ' )
                if test == 'q' or test == 'Q':
                    break
                test = int(test)
            if test == 1:
                log.prnObjState()            
            elif test == 2:
                t = getInt( 'What is the bucket interval in seconds?  ', 1, 16000 )
                s = getInt( 'What is the bucket size in bytes?  ', 1, 8 )
                log.format( timedelta(seconds=t), s )
            elif test == 3:
                dt = getDT( )
                print 'bucketDelta returned ' + str(log.bucketDelta(dt))
            elif test == 4:
                i = getInt( 'What bucketDelta is to be used?  ', -4000, 4000 )
                print 'getBucket returned ' + str(log.getBucket( i ))
            elif test == 5:
                dt = getDT()
                cnt = getInt( 'How many buckets to return?  ', 1, 200 )
                print 'fetch() results=', log.fetch( dt, cnt )
            elif test == 6:
                dt = getDT()
                value = getInt( 'What value to store?  ',  \
                                 (0xC0 << (8 * (log.bcktSize -1))) - 1,  \
                                   0x3FFFFFFFFFFFFFFF >> (8 *  (8 - log.bcktSize )))
                log.store( dt, [ value ] )
                print 'store() complete.'
            elif test == 7:             # Hex Dump 32K EEPROM
                testLock.acquire()
                i2c = smbus.SMBus(1)
                i2c.write_byte_data(0x57,0,0) #start address=0
                for i in range(0,256):        #lines
                    data=[]
                    for j in range(0,16):  
                        data.append(i2c.read_byte(0x57))
                    print( hexDump16( 16*i, data ))    
                testLock.release()
            elif test == 8:
                testLock.acquire()
                pass
                testLock.release()
            elif test == 9:
                dt = getDT()
                value = getInt( 'What value to store?  ',  \
                                 (0xC0 << (8 * (log.bcktSize -1))) - 1,  \
                                   0x3FFFFFFFFFFFFFFF >> (8 *  (8 - log.bcktSize )))
                log.setAnchor( dt, [value] )
                print 'setAnchor() complete.'
            elif test == 10:
                trash = PeriodicLog( foo, 8 )
                trash.format( timedelta(seconds=300), 3 ) 
                print "constructing ring using memory(28), pgSz=8, interval=300, bucketSize=3"
                ring = PeriodicLog( foo, 8 )
                future0 = datetime(2006,5,4,3,4,31)     #6.5.4.3.2.1
                ring.store( future0, [0x000] )
                print str(future0)
                ring.prnObjState()               
                raw_input("store(000)")  
                                   
                aray = ring.fetch(future0)
                print hex(aray[0])
                aray = ring.fetch(future0,5)
                print hex(aray[0])
                td = timedelta(seconds=300)
                future1= future0 + td
                print 'future1='+str(future1)
                ring.store( future1, [0x111] )
                ring.prnObjState()          
                raw_input("store(111)")  
                                          
                future2= future1+td
                ring.store( future2, [0x222] )
                ring.prnObjState()          
                raw_input("store(222)")  
                                          
                future3=future2+td
                ring.store(future3,[0x333])
                ring.prnObjState()        
                raw_input("store(333)")  
                         
                future4 = future3 + td
                ring.store( future4, [0x444] )
                ring.prnObjState()
                raw_input( "store(444)" )
                
                future5 = future4 + td
                ring.store( future5, [0x555] )
                ring.prnObjState()
                raw_input( "store(555)" )
                
                future6 = future5 + td
                ring.store( future6, [0x666] )
                ring.prnObjState()
                raw_input( "store(666)" )
                
                future9 = future6 + td + td + td
                ring.store( future9, [0x999] )
                ring.prnObjState()                        
                raw_input( "store(999)" )     
                                        
                print hex(ring.fetch(future9)[0])
                raw_input("fetch(999)")                
                

                sec = 0
                bckt1 = 1
                while bckt1 == 1:
                    td1= timedelta(seconds=sec)    
                    fu = ring.lastWrDttm + td1
                    delta1 = ring.bucketDelta( fu )
                    bckt1 = ring.getBucket( delta1)
                    print "seconds="+str(sec)+", bckt1="+str(bckt1)
                    sec -= 1   
                
                                        
                #check the PeriodicLog __init__ open for initialized PeriodicLog
                ring2 = PeriodicLog( foo, 8 )                        

                ring2.prnObjState()
                raw_input( "ring2 __init__" )                        
                #print 'fetch > # avail, len(aray) should==1, aray=', aray

                print( hex(ring2.fetch(future6)[0]))
                raw_input("fetch(666)")
                
                aray = ring2.fetch(future9,4)
                a=[]
                for i in range(len(aray)):
                    a.append( hex(aray[i]))
                print a
                raw_input("9's + mt + mt +6's")
    
#THE End               
