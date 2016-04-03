/* Euler problem #92
   How many starting numbers below ten million will arrive at 89?

   A number chain is created by continuously adding the square of
   the digits in a number to form a new number until it has been
   seen before.

   For example,
          44 → 32 → 13 → 10 → 1 → 1
          85 → 89 → 145 → 42 → 20 → 4 → 16 → 37 → 58 → 89

   Therefore any chain that arrives at 1 or 89 will become stuck
   in an endless loop. What is most amazing is that EVERY starting
   number will eventually arrive at 1 or 89.

   By:         MK Beavers
   Created:    5 March 2016
   Platform:   Raspberry Pi V3 (armv8)          
 
   Pseudo code:
    e89 = 0
    for x in range(2, 10000000):
        s = x
        do:
            y = 0
            do:
                quotient = s / 10
		remainder = s % 10 
                y += remainder * remainder
		s = quotient
	    while quotient != 0:
            s = y	(chain)
        while y != 89 and y != 1:
        if y == 89:
            e89 += 1
    print(e89)          #8581146  

   Frame Usage:
    +20	stop_microsec
    +16	stop_sec
    +12	start_microsec
     +8	start_sec
     +4	reserved	To maintain 8-byte alignment
     +0	LinkReg
     fp -----------  
 */
 
//   REGISTER USAGE
//
quotient	.req R0
e89			.req R1
s			.req R2
y			.req R3
x			.req R4 
ten			.req R5
limit		.req R6
remainder	.req R7
@            sl .req R10  Lexical scope (Position Independent code)
@            fp .req R11  Frame pointer (local variables)
@            ip .req R12    Used by linker for distance branch
@            sp .req R13  Stack Pointer
@            lr .req R14  Link Register
@            pc .req R15  Program Counter

	.data
	.balign  4
RESULTS: .asciz "Euler92: numbers arriving at 89=%d.\n"
RUNTIME: .asciz "Euler92: runtime=%d+%d (in sec+microsec).\n"
	

	.text
	.balign 4
	.global printf
	.global gettimeofday 
 	.global	main
 	.func	main 
main: 
	STR	LR,[SP,#-24]!	@save LinkReg 
	MOV	FP,SP
	STMFD	SP!,{R1-R12}	@save working regs 
@get start time
	ADD	R0,FP,#8		@ &struct timeval
	MOV	R1,#0			@ &struct timezone
	BL	gettimeofday
@begin Pseudo code/asm translation	
	MOV	e89,#0		@ e89 = 0
	MOV	ten,#10		@ divisor
	MOV	x,#1  		@ for x in range(2,limit):
	LDR	limit,TenMil
NEXT:
	ADD	x,#1
	CMP	x,limit
	BPL	PDETAIL
	MOV 	s,x		@ s = x
DO:	
	MOV 	y,#0   		@ y = 0    
LOOP:
	UDIV	quotient,s,ten		 @ quotient = s / 10
	MLS 	remainder,quotient,ten,s @ remainder = s % 10	
	MLA 	y,remainder,remainder,y	 @ y += remainder * remainder
	MOVS 	s,quotient	@ s = quotient
	BNE	LOOP            @ while quotient != 0:
	CMP	y,#89		@ set y == 89
	ADDEQ	e89,#1		@ if #89 then e89 += 1
	BEQ	NEXT
	CMP	y,#1		@ while y != 1
	BEQ	NEXT
	MOV	s,y		@ s = y (chain)
	B	DO
	
PDETAIL:			@print(e89)    #8581146  
	LDR	R0,PRTSTR	@ R1 has e89	
	BL	printf 
@get stop time	
	ADD	R0,FP,#16
	MOV	R1,#0
	BL	gettimeofday
@compute/print runtime
	ADD	R0,FP,#8
	LDMFD	R0,{R1-R4}
	SUBS	R2,R4,R2 
	SBC	R1,R3,R1
	LDRMI	R0,OneMil	@if negative then
	ADDMI	R2,R0		@ fix-up by adding aMillion
	LDR	R0,RTIME
	BL	printf
	MOV	R0,#0		@set 0 return code	
	LDMFD	SP!,{R1-R12}	@restore working regs
	LDR	LR,[SP],#24	@restore LinkReg
	BX	LR		@return to caller
	
PRTSTR:	.word	RESULTS
RTIME:	.word	RUNTIME
OneMil: .word   0xF4240
TenMil: .word   0x989680

	.end
