#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import fcntl

def  hexField( num, width=2 ):
    ''' return hex converted num w/o leading '0x' filling field '''
    result = hex(num)[2:]
    if len(result) > width:
        return '['+result+']'       #indicate overflow
    elif len(result) == width:
        return result
    else:
        return  '0000000000'[-width+len(result):] + result

def  hexDump16( addr, max16 ):
    ''' return formatted 32bit address with 16 byte [] of hex & char data '''
    seg=[]
    chrs=[]
    base=hexField(addr, 8)
    seg.append( base[0:4] + ':' + base[4:] )
    base=addr & 15
    bcnt = len(max16)
    if base + bcnt > 16:
        bcnt = 16 - base
    #print 'base='+str(base)+', bcnt='+str(bcnt)    
    for i in range(0,base):
        seg.append('  ')
        chrs.append(' ')
    for i in range(0,bcnt):
        seg.append(hexField(max16[i]))
        if max16[i] >= 0x20 and max16[i] < 0x7F:
            chrs.append( chr(max16[i]))
        else:
            chrs.append( '.' )
    for i in range(base+bcnt,16):
        seg.append('  ')
        chrs.append(' ')
    for i in range(0,4):
        seg.append(seg[i*4+1]+seg[i*4+2]+seg[i*4+3]+seg[i*4+4])
    result = seg[0] +'   '+ seg[17] +' '+ seg[18] +' '+ \
              	seg[19] +' '+ seg[20] +'  |'+ ''.join(chrs) +'|'
    if bcnt < len(max16):
        result = result + ' +['+str(len(max16)-bcnt)+'] ...'
    return result

def  isqrt( sq ):    #sq is assumed to be 32-bit int
    ''' return largest int whose square root is <= sq ** 1/2
        from: http://www.embedded.com/electronics-blogs/
              programmer-s-toolbox/4219659/Integer-Square-Roots
    '''
    rem = 0
    root = 0
    for i in range(16):     #word size of result
        root <<= 1
        rem = (rem << 2) + ((sq >> 30) & 3) #add '& 3' for >32-bit int
        sq <<= 2
        root += 1
        if root <= rem:
            rem -= root
            root += 1
        else:
            root -= 1
    #at return time: rem = sq - root * root 
    return root >> 1
            
class Lock:
    
    def __init__(self, filename):
        self.filename = "/tmp/" + filename
        # This will create it if it does not exist already
        self.handle = open(self.filename, 'w')
    
    # Bitwise OR fcntl.LOCK_NB if you need a non-blocking lock 
    def acquire(self):
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        self.handle.write(str(os.getpid())+'\n')
        
    def release(self):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        
    def __del__(self):
        self.handle.close()
   

if __name__ == '__main__':

	for x in range(0, 111, 3):
		print('isqrt(%d)=%d.' % (x,isqrt(x)))
    
	print('Overflow mark "[12345678]"?=' + hexField( 0x12345678, 2 ))
	print('no padding "48"?=' + hexField(0x48, 2))
	print('with padding "02"?=' + hexField( 2, 2 ))
          
	print( hexDump16( 0x63, [100,10,102,103,200,105] ))
	print( hexDump16( 0x1234560, \
    	  [48,49,50,51,52,53,54,55,56,57,65,66,67,68,69,70]))
	print( hexDump16( 0,         \
    	  [48,49,50,51,52,53,54,55,56,57,65,66,67,68,69,70,64]))
	print( hexDump16( 0x123456,         \
    	  [48,49,50,51,52,53,54,55,56,57,65,66,67,68,69,70,64]))
	try:
		lock = Lock("mkblib_TEST.tmp")
		lock.acquire()
		tick = tock = time.time()
        # Do important stuff that needs to be synchronized
		while tick - tock < 30:
			tick = time.time()
			print( 'waiting 3 seconds...' )
			time.sleep(3)
	finally: 
		lock.release()

#THE END
