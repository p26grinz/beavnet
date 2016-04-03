/*
// A bit_banging programmer for KM93C46 EEPROM, using microwire interface.
// Memory organization is 64 registers of 16-bits each.
//
// Author:         MK Beavers
// Created:        25 Jan 2016
// Dependencies:   Tested only on Raspberry Pi V2/Raspian Jessie with WiringPi package 
//                     and level shifter between 5V and 3.3V interface lines. 
// Build:          gcc -Wall -Wformat=0 -g -o2 -std=c99 -lwiringPi -mcpu=cortex-a7 
//                     -mfpu=neon-vfpv4 -mfloat-abi=hard -o uWire uWire.c
// Run Command:    sudo ./uWire  [/optional/uWire/eepromRegistersFile.hex]
// Change History: Initial version 
//    20160202     Rewrite device busy detection/handler in transact for regs2eeprom 
//                 error, symptom: even #'s OK but odd #'s recorded as 0xFFFF.   
//                 Solution: deselect the device before delay then recheck status.  
// Reference:      https://en.wikipedia.org/wiki/Serial_Peripheral_Interface_Bus
//                 Microwire,[13] often spelled μWire, is essentially a predecessor 
//                 of SPI and a trademark of National Semiconductor. 
//                 It's a strict subset of SPI: half-duplex, and using SPI mode 0. 
*/

/*
 *  This work, including the source code, documentation
 *  and related data, is placed into the public domain.
 *  The orginal author is Morris K Beavers.
 *  THIS SOFTWARE IS PROVIDED AS-IS WITHOUT WARRANTY
 *  OF ANY KIND, NOT EVEN THE IMPLIED WARRANTY OF
 *  MERCHANTABILITY. THE AUTHOR OF THIS SOFTWARE,
 *  ASSUMES _NO_ RESPONSIBILITY FOR ANY CONSEQUENCE
 *  RESULTING FROM THE USE, MODIFICATION, OR
 *  REDISTRIBUTION OF THIS SOFTWARE.
 */

#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <time.h>

unsigned int  registers[] = { 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  //  3
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  //  7
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 11
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 15
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 19
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 23
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 27
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 31
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 35
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 39
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 43
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 47
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 51
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 55
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 59
                            , 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF  // 63
                            };

// The KM93C46 supports 7 operations/commands (start bit is 0x100):
//   Op    Code   Addr     Data      Comment 
// -------------------------------------------------------
//  EWDS    00   00xxxx     -       Erase/Write disable 
//  WRAL    00   01xxxx   D15->D0   Write all registers
//  ERAL    00   10xxxx     -       Erase all registers
//  EWEN    00   11xxxx     -       Erase/Write enable
//  WRITE   01   A5->A0   D15->D0   Write reg. A5->A0
//  READ    10   A5->A0    Dout     Read reg. A5->A0
//  ERASE   11   A5->A0     -       Erase reg. A5->A0
//--------------------------------------------------------
#define   opWriteDisable  0x100
#define   opWriteAll      0x110    //add data short
#define   opEraseAll      0x120
#define   opWriteEnable   0x130
#define   opWriteShort    0x140    //add address & data short
#define   opReadShort     0x180    //add address (read short from MIN)
#define   opEraseShort    0x1C0    //add address

#define BUSY      LOW
#define READY     HIGH

//    Broadcom Port definitions
//--------------------------------------------------------
#define     CE0      8       //Chip Select/Enable
#define     MIN      9       //Master Input
#define    MOUT     10       //Master Output
#define    SCLK     11       //Serial Clock

/*  Write any modified (those not 0xFFFFxxxx) memory registers to the console.
 */
void  displayRegisters()
{
    char   l[80];
    
    strcpy(l, "                                                                 ");
    printf("ADDR   +0   +1   +2   +3   +4   +5   +6   +7   |...as..char...|\n");
    for (int row = 0; row < 8; ++row)
    {
        char  num[10];
        sprintf(num, "0x%0.2X", 8 * row);
        memcpy(l, num, 4);   
        for (int col = 0; col < 8; ++col)
        {
            int index = 8 * row + col;
            unsigned int  x = registers[index];
            if ((x & 0xFFFF0000) != 0xFFFF0000 )
            {
                sprintf(num, "%0.4X", x & 0xFFFF);
                memcpy(&l[5 * col + 6], num, 4);
                l[2 * col + 47] = isprint(x & 0xFF) ? (x & 0xFF) : '.';
                l[2 * col + 48] = isprint(x >> 8 & 0xFF) ? (x >> 8 & 0xFF) : '.';
            }
            else  //just overlay the buffer if never updated from READ
            {
                memcpy(&l[5 * col + 6], "    ", 4);
                l[2 * col + 47] = ' ';
                l[2 * col + 48] = ' ';
            }
        }
        puts(l);
    }
}
                
/* Serialize the op code (+ address) and optionally data to the device.
 * If a Read op then deserialize the 16-bit data supplied
 * Note: delayMicroseonds comments refer to device datasheet t*** parameters.
 */
int  writeRead(unsigned int op, unsigned int * pRead)
{
    //write the op/addr/data to the device
    for (unsigned int bit = 0x80000000; bit; bit >>= 1) 
    {
        // Shift-out a bit to the MOSI line 
        digitalWrite(MOUT, (op & bit) ? HIGH : LOW);
        delayMicroseconds(2);         //Delay for at least tdis & tskl & tcss
        // Activate the clock line (data read by device)
        // The device ignores leading zeros before start bit 
        digitalWrite(SCLK, HIGH);
        delayMicroseconds(2);         //Delay for at least tdih & tskh & tdh
        digitalWrite(SCLK, LOW);      //Idle the clock line 
    }
    if (NULL != pRead)                //if this is a READ then get data
    {
        digitalWrite(MOUT, LOW);      //Shift-out a bit to the MOSI line 
        for ( int i = 17; i; --i )    //dummy 0-bit + 16 data bits
        {
            delayMicroseconds(2);     //Delay for at least tdis & tskl & tpd
            // Read the next bit
            *pRead = (*pRead << 1) + (digitalRead(MIN) & 1);
            digitalWrite(SCLK, HIGH);
            delayMicroseconds(2);     //Delay for at least tdih & tskh
            digitalWrite(SCLK, LOW);  //Idle the clock line 
        }   
    }
    return 0;
}

/* Handle device select/reset.
 * Verify the device is Ready.
 *    Error return=1 if timesout waiting for device READY
 */
int  transact(unsigned int op, unsigned int * pRead)
{
    int   result  = 0;	
    int   status  = BUSY;
    int   timeout = 111;             //at least 22 msec. before timeout
    
    //idle the device data in
    digitalWrite(MOUT, LOW);         //ignored by device until start-bit (HIGH)
    digitalWrite(SCLK, LOW);         //idle the clock
    delayMicroseconds(2);            //short delay
    while (BUSY == status && timeout-- > 0)
    {
        digitalWrite(CE0, HIGH);     //select the device        
        delayMicroseconds(2);        //Delay for at least tdis & tskl & tcss
        digitalWrite(SCLK, HIGH);    //status should be available after tpd0       
        delayMicroseconds(2);        //Delay for at least tdih & tskh & tdh & tsv
        digitalWrite(SCLK, LOW);     //completed one SCLK cycle
        status = digitalRead(MIN);   //read status (after CE0 Active + tcss + tdb0)
        if (BUSY == status)
        {
            digitalWrite(CE0, LOW);  //deselect device
            delayMicroseconds(200);  //short delay
        }                            //then retry
    }
    //printf("uWire: debug device status timeout=%d, op=%X.\n", timeout, op);    
    if (BUSY == status)
    { 
        digitalWrite(CE0, LOW);      //Deselect the device
        return 1;                    //return error code
    }
 
    result = writeRead(op, pRead);   //send/receive data to/from device
    
    delayMicroseconds(1);            //delay at least tcsh
    digitalWrite(CE0, LOW);          //deselect the device
    delayMicroseconds(1);            //delay at least tdf and tcs
    return result;
}

/* Update the registers from a .hex file if provided
 * Initialize the GPIO ports.
 * Get the command and parameters from the console.
 * Report the operation results.
 */
int main (int argc, char **argv)
{
    int                  i = 0;
    int            iResult = 0;
    int           iRunning = 1;
    char         caCmdline[80];
    char         caCommand[80];
    unsigned int        uiAddr;
    unsigned int        uiData;
    unsigned int        uiRead;
    unsigned int          uiOp;
    
    if (argc > 1)	//was a path/filename supplied???
    {
        FILE  * fHex;
        fHex = fopen(argv[1], "r");
        if (NULL==fHex)
        {
            printf("Failed to open %s, invalid path/filename?\n", argv[1]);
        }
        else
        {
            int      lineNumber = 0;
            char     line[80];
            
            //parse each record and update the registers
            while (NULL != fgets(line, sizeof(line), fHex)) 
            {
                int     toks, length, address, type, byte1, byte2, chksum;
                
                --lineNumber;
                length = strlen(line);
                while (length > 0 && iscntrl(line[--length]))     //0 any trailing control chars
                    line[length] = 0;    
                while (length >= 0 && isxdigit(line[length--]));  //all chars hex except the first
                if (length >= 0)
                {
                    printf("uWire: parse error1, non-hex digit, line #=%d, record=%s.\n", -lineNumber, line);
                    continue;
                }                                     
                if (line[0] == ':')                   //all records begin with ':'
                {
                    length = strlen(line);
                    if (15 == length)                 //for data record of 2 bytes
                    {    
                        toks = sscanf(line, ":%2X%4X%2X%2X%2X%2X"
		                          , &length, &address, &type, &byte1, &byte2, &chksum );
		        chksum += length + address + type + byte1 + byte2;
		        if (6 == toks && 2 == length && 64 > address && 0 == type && 0 == (0xFF & chksum))
		            registers[address] = byte2 * 256 + byte1;
		        else
		            printf("uWire: parse error2, line #=%d, record=%s.\n", -lineNumber, line);
		    }
		    else if (11 == length)            //for EOF record
		    {
		        for( int i = 0; ++i < length; line[i] = toupper(line[i]));
		        if (0 == strcmp(":00000001FF", line))	 //test for EOF record
		        {
		            lineNumber = -lineNumber;		//give visual indicator of EOF record
		            break;
		        }
		        else
		            printf("uWire: parse error3, bad EOF record, line #=%d, record=%s.\n", -lineNumber, line);
		    }
		    else
		        printf("uWire: parse error4, wrong line length, line #=%d, record=%s.\n", -lineNumber, line);
                }
                else
                    printf("uWire: parse error5, missing ':', line #=%d, record=%s.\n", -lineNumber, line);
            }    
            fclose(fHex);    
            displayRegisters();
            printf("uWire: Initialized memRegs from %s[%d].\n", argv[1], lineNumber);
        }         
    }
    
    wiringPiSetupGpio();

    digitalWrite(CE0, LOW);        //device not selected
    pinMode(CE0, OUTPUT);          //Chip Select
    digitalWrite(MOUT, LOW);       //inactive data output
    pinMode(MOUT, OUTPUT);         //Master Output
    digitalWrite(SCLK, LOW);       //clock in idle state
    pinMode(SCLK, OUTPUT);         //Clock
    pinMode(MIN, INPUT);           //Master Input
     
    while(iRunning)
    {
        caCommand[0] = uiAddr = uiData = uiRead = iResult = 0;
        printf("\nuWire: Enter command and any required parameters:\n");
        printf("uWire:   WRITE xAddr xData;   READ  xAddr;   EWEN;   EWDS;   \n");
        printf("uWire:   WRAL  xAddr xData;   ERASE xAddr;   ERAL;   ReadAll; \n"); 
        printf("uWire:   ViewRegs;   Regs2File;   Regs2Eeprom;  or Enter to quit!\n");
        printf("uWire:   ???   ");
        fgets( caCmdline, sizeof(caCmdline), stdin );
        sscanf(caCmdline, "%s %X %X", caCommand, &uiAddr, &uiData);
        i = strlen(caCommand);
        if (0 == i) break;	//test for QUIT
        if (uiAddr > 0x3F)
        {
            printf("uWire: Invalid xAddr (0 >= xAddr <= 3F).\n");
            continue;
        } 
        if (uiData > 0xFFFF)
        {
            printf("uWire: Invalid xData (0 >= xData <= FFFF).\n");
            continue;
        } 
        while(0 <= --i) 
            caCommand[i] = tolower(caCommand[i]);
        printf("uWire: Debug: cmd=%s, addr=0x%X, data=0x%X\n", caCommand, uiAddr, uiData);
        
        if (0 == strcmp("read", caCommand))
        {
            uiRead = 0xFFFFFFFF;             //initialize for all set
            uiOp = opReadShort + uiAddr;
            iResult = transact( uiOp, &uiRead );
            if (0 == iResult)
            {
                registers[uiAddr] = uiRead;       //save to buffer
                printf("uWire: Address 0x%X contains 0x%X.\n", uiAddr, uiRead); 
            }
        }
        else if (0 == strcmp("write", caCommand))
        {
            //the datasheet indicates an ERASE is required before WRITE
            uiOp = opEraseShort + uiAddr;
            iResult = transact( uiOp, NULL );
            uiOp = ((opWriteShort + uiAddr) << 16) + uiData;
            iResult = transact( uiOp, NULL );
        }
        else if (0 == strcmp("erase", caCommand))
        {
            uiOp = opEraseShort + uiAddr;
            iResult = transact( uiOp, NULL );
        }
        else if (0 == strcmp("ewen", caCommand))
        {
            uiOp = opWriteEnable;
            iResult = transact( uiOp, NULL );
        }
        else if (0 == strcmp("ewds", caCommand))
        {
            uiOp = opWriteDisable;
            iResult = transact( uiOp, NULL );
        }
        else if (0 == strcmp("eral", caCommand))
        {
            uiOp = opEraseAll;
            iResult = transact( uiOp, NULL );
        }
        else if (0 == strcmp("wral", caCommand))
        {
            //the datasheet indicates an ERAL is required before WRAL
            uiOp = opEraseAll;			
            iResult = transact( uiOp, NULL );
            uiOp = (opWriteAll << 16) + uiData;
            iResult = transact( uiOp, NULL );
        }
        else if (0 == strcmp("readall", caCommand))
        {
            unsigned int  uiWord;
            
            for (int i = 0; i < 64; ++i)
            {
                uiWord = 0xFFFFFFFF;       //initialize for all set
                uiOp = opReadShort + i;
                iResult = transact( uiOp, &uiWord );
                if (0 != iResult)
                    printf("uWire: ERROR: Read of address 0x%X returned 0x%X.\n", i, iResult); 
                else
                    registers[i] = uiWord;	//save to buffer
            }     
            displayRegisters();                
        }
         else if (0 == strcmp("viewregs", caCommand))
        {
            displayRegisters();
        }
        else if (0 == strcmp("regs2file", caCommand))
        {
            FILE  * fHex;
            time_t  timeNow;
            int     count = 0;
            
            for(int q = 0; q < 64; ++q) 
                if ((registers[q] & 0xFFFF0000) == 0xFFFE0000)
                    ++count;
            if (count != sizeof(registers) / sizeof(registers[0]))
            {
                printf("uWire: Error: All registers not initialized, issue READALL before REGS2FILE.\n");
                continue;
            }
            timeNow = time(NULL);
            strftime(caCommand, sizeof(caCommand), "uWire.%Y%m%d.%H%M%S.hex", localtime(&timeNow));
            fHex = fopen(caCommand, "w");
            if (NULL==fHex)
            {
                printf("Failed to create %s, check space.\n");
            }
            //write a register record
            for(int q = 0; q < 64; ++q)
            {
                unsigned char   one = registers[q] & 0xFF;
                unsigned char   two = registers[q] >> 8 & 0xFF;
                unsigned char   sum = 2 + q + one + two;
                fprintf(fHex, ":02%0.4X00%0.2X%0.2X%0.2X\n", q, one, two, (0 - sum) & 0xFF);
            }
            fprintf(fHex, ":00000001FF");	//write the EOF record
            fclose(fHex);    
            printf("Created %s containing the registers image.\n", caCommand);
        }
        else if (0 == strcmp("regs2eeprom", caCommand))
        {
            iResult = 0;
            uiAddr = 0;
            
            while (0 == iResult && uiAddr < 64)
            {
                uiOp = ((opWriteShort + uiAddr) << 16) + (registers[uiAddr] & 0xFFFF);               
                iResult = transact( uiOp, NULL );
                ++uiAddr;
            }
            if (uiAddr != 64)
                printf("uWire: Incomplete update, %d registers processed.\n", uiAddr);
        }
        else 
        {
            printf("uWire: unknown command, care to try again?\n");
            continue;
        }
        printf("uWire: Debug: CmdStatus=%d, uiOp=0x%X.\n", iResult, uiOp);
    }
    pinMode(MOUT, INPUT);        //restore default pin direction/mode
    pinMode(SCLK, INPUT);
    // pinMode(CE0, INPUT);      //leave the device deselected
    digitalWrite(CE0, LOW);
    return 0;
    
} //CODE END

/*       Test bench set-up/interconnection

                        --------------------------------------
                       |                                      |
                       |         SparkFun Level Shifter       |
           RPi GPIO    |               BOB-12009              |        KM93C46
          ---------    |      ----------------------------    |       ---------
                   |   |     |                            |   |      |
           +5v   2 |---      |                            |   |      | 6  N/C
         +3.3v  17 |---------| 4  LV                HV  3 |--- ------| 8  Vcc
           GND  20 |---------| 6  GND              HV1  1 |----------| 3  DI
          MOUT  19 |---------| 3  LV1              HV2  2 |----------| 4  DO
           MIN  21 |---------| 5  LV2              HV3  5 |----------| 2  SK
          SCLK  23 |---------| 2  LV3              HV4  6 |----------| 1  CS
           CE0  24 |---------| 1  LV4              GND  4 |--- ------| 5  GND
           GND  25 |---      |                            |   |      | 7  N/C
                   |   |     | JP1                    JP2 |   |      |
          ---------    |      ----------------------------    |       ---------
                       |                                      |
                       |                                      |
                        --------------------------------------   


//Here is the console output from reading the uWire.parser.test.hex file below:
$ sudo ./uWire uWire.parser.test.hex
uWire: parse error1, non-hex digit, line #=1, record=:x20000002020BE.
uWire: parse error1, non-hex digit, line #=2, record=:020001002020Bx.
uWire: parse error5, missing ':', line #=3, record=&020002002020BC.
uWire: parse error4, wrong line length, line #=4, record=:020003002020BB0.
uWire: parse error2, line #=5, record=:030004002020B9.
uWire: parse error2, line #=6, record=:02004000202078.
uWire: parse error2, line #=7, record=:020006022020B6.
uWire: parse error2, line #=8, record=:020007002020B8.
uWire: parse error3, bad EOF record, line #=57, record=:00000000FF.
ADDR   +0   +1   +2   +3   +4   +5   +6   +7   |...as..char...|
0x00                                                             
0x08  2020 2020 2020 2020 2020 2020 2020 2020                    
0x10  2020 2020 7520 6957 6572 2020 2020 2020       uWire        
0x18  2020 7020 6F72 7267 6D61 656D 2072 2020     programmer     
0x20  2020 2020 2020 6F66 2072 2020 2020 2020        for         
0x28  4B20 394D 4333 3634 4520 5045 4F52 204D   KM93C46 EEPROM   
0x30  2020 2020 2020 2020 2020 2020 2020 2020                    
0x38  2020 2020 2020 2020 2020 2020 6D20 626B               mkb  
uWire: Initialized memRegs from uWire.parser.test.hex[66].

//order of error2's: invalid data length; address out of bounds; type != 0; failed checksum
//The following is the contents of uWire.parser.test.hex 
:x20000002020BE
:020001002020Bx
&020002002020BC
:020003002020BB0
:030004002020B9
:02004000202078
:020006022020B6
:020007002020B8
:020008002020B6
:020009002020B5
:02000A002020B4
:02000B002020B3
:02000C002020B2
:02000D002020B1
:02000E002020B0
:02000F002020AF
:020010002020AE
:020011002020AD
:02001200207557
:0200130057692B
:02001400726513
:020015002020A9
:020016002020A8
:020017002020A7
:020018002020A6
:02001900207055
:02001A00726F03
:02001B0067720A
:02001C00616D14
:02001D006D650F
:02001E0072204E
:02001F0020209F
:0200200020209E
:0200210020209D
:0200220020209C
:02002300666F06
:02002400722048
:02002500202099
:02002600202098
:02002700202097
:02002800204B6B
:020029004D394F
:02002A0033435E
:02002B00343669
:02002C0020456D
:02002D0045503C
:02002E00524F2F
:02002F004D2062
:0200300020208E
:0200310020208D
:0200320020208C
:0200330020208B
:0200340020208A
:02003500202089
:02003600202088
:02003700202087
:00000000FF
:02003800202086
:02003900202085
:02003A00202084
:02003B00202083
:02003C00202082
:02003D00202081
:02003E00206D33
:02003F006B62F2
:00000001FF
*/ 
// SUPPLEMENTAL INFO END
