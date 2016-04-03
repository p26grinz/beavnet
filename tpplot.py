import matplotlib.pyplot as plot
from matplotlib import pyplot
import math
from intlog import PeriodicLog
from datetime import datetime
from datetime import timedelta

x = []
y = []
xaxis = 72
min = 10000
max = 0
def s15(x):
    return -(x & 0x4000) | (x & 0x3FFF)

if not True:
    const = (4 * math.pi) / xaxis
    for i in range(0, -xaxis, -1):
        value = 1000 + ( 50 * math.sin( abs(i) * const))
        x.append( i )
        y.append( value )
        if min > value: min = value
        if max < value: max = value             
else:        
    log = PeriodicLog( 'good.intlog.bin' )
    print 'log.availBckts=' + str(log.availBckts)
    logdata = log.fetch( log.lastWrDttm, 7 * 288 )
    print 'log.lastWrDttm=' + str(log.lastWrDttm)
    print 'len(logdata)=' + str(len(logdata))
    incr = 5                    #length between log entries (in minutes)
    xaxis = len(logdata)
    for i in range( xaxis ):
        value = logdata[i]
        # print 'logdata['+str(i)+']=' + hex(value) + '=' + str(s15(value))
        if value == 0xC000:     #the empty indicator
            continue
        else:
            value = s15(value)          #convert to 2's complement
        value = (value + 8500) / 10     #restore pre-normalization value
        if min > value: min = value
        if max < value: max = value
        x.append( -i )
        y.append(value)

#all_data = [[1,10],[2,10],[3,10],[4,10],[5,10],[3,1],[3,2],[3,3],[3,4],[3,5]]
#for point in all_data:
#    for point2 in all_data:
#        pyplot.plot([point[0], point2[0]], [point[1], point2[1]])
#  pyplot.plot( [xs, xd], [ys, yd] )    #s=source d=destination
    if xaxis > 3000:
        reduce = 6
        xx = [ x[0]]
        yy = [ y[0]]
        for i in range( -1, -xaxis, -reduce ):
            upper = 0
            lower = 2000
            for j in range( 0, -reduce, -1 ):
                value = y[i+j]
                if value > upper: upper = value
                if value < lower: lower = value
            index = -1 + i / reduce
            xx.append( index )     #add 1 hr old point for scatter plot
            yy.append( value )
            pyplot.plot( [index, index], [lower, upper] )
        x = xx
        y = yy
        xaxis = len(x)
        incr *= reduce
                
    
plot.scatter(x,y)
min -= 20
max += 20
plot.axis( [-xaxis, 0, min, max] )
plot.title( 'Pressure History' )
plot.ylabel( 'Pressure (in millibars)' )
plot.xlabel( 'Time (in ' + str(incr) + ' minute increments from ' +  \
              str(log.lastWrDttm) + ')' )

pyplot.show()
