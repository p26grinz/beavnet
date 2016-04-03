/*
   Find the first 1,015,808 primes (assembler version)
   
   By:         MK Beavers
   Created:    11 July 2015
   Platform:   Raspberry Pi V2 (ARMv7)
   Build with: gcc-4.8 -Wall -g -o2 -mcpu=cortex-a7 -mfpu=neon-vfpv4 \
               -mfloat-abi=hard -Wa,-alh -g -o primesFast primesFast.s
   Updated:    5 March 2016, rebuild on Raspberry Pi 3 (armv8),
	       2 April 2016, add timer recording
               
   pseudo code:
   	Initialize prime[] with prime[0]=1, prime[1]=2
   	var candidate=3, saveTo=2
   	do
   	    for i=1; True; ++i
   	        if candidate % prime[i] == 0  		//not a prime
   	            break
   	        if candidate / prime[i] < prime[i]	//found prime
   	            primes[saveTo++]=candidate
   	            break
   	    ++candidate
   	until saveTo >= len(prime[])
   	print all prime[]
   	            
   Register Usage:
     R0=parameter passing
     R1=quotient of candidate/prime[]
     R2=remainder of candidate/prime[]
     R3=candidate for primeness
     R4=member of prime[], already discovered
     R5=* to [R4]
     R6=* to save new prime discovered
     R7=* to prime[1] during looping
     R8=* to prime[Last+1]
     R9=index 
     R11=Frame pointer
 */
 
FP	.req	R11

	.data
	.balign  4
RUNTIME: .asciz "primesFast: runtime=%d+%d (in sec+microsec).\n"	

	.text
	.balign 4
 	.global	main
 	.global gettimeofday 
 	.func	main
main: 
	STR	LR,[SP,#-24]!	@save LinkReg 
	MOV	FP,SP
	STMFD	SP!,{R1-R12}	@save working regs 
@get start time
	ADD	R0,FP,#8	@ &struct timeval
	MOV	R1,#0		@ &struct timezone
	BL	gettimeofday
p1:	
	nop	
@Initialize registers
	MOV	R9,#0		@R9=0, used when printing	
	MOV	R8,SP		@remember the limit of primes to find
	SUB	SP,SP,#1015808*4  	@get space for 1000000+ primes
	MOV	R7,SP		@start of primes Found
	MOV	R3,#1		@prime[0]=1
	STR	R3,[R7],#4	@save prime[0]=1 and adj. *prime
	ADD	R3,#1
	STR	R3,[R7]		@save prime[1]=2
	ADD	R6,R7,#4	@initialize where to save next prime
@OK, now find some primes	
NEXTPRIME:
	ADD	R3,#1		@next candidate	
	MOV	R5,R7		@begin testing with prime[1]
LOOP:
	LDR	R4,[R5],#4	@test with next prime
	UDIV	R1,R3,R4	@R1=R3/R4
	MLS 	R2,R1,R4,R3	@R2=R3-R1*R4
	CMP	R2,#0		@if remainder==0 then not prime
	BEQ	NEXTPRIME
	CMP	R4,R1		@if prime<=quotient then test with next prime
	BLE	LOOP
@new prime found
	STR	R3,[R6],#4
	CMP	R6,R8		@if storage is filled then print Primes[]
	BLT	NEXTPRIME	
@get stop time
	ADD	R0,FP,#16
	MOV	R1,#0
	BL	gettimeofday		
@Print the Primes to STDOUT
	SUB	R7,R7,#4	@set R7=* to prime[0] for printing
PRTNEXT:
	LDR	R0,=PRTSTR	@R0=what to print
	MOV	R1,R9		@R1=index of Primes
	LDR	R2,[R7],#4	@R2=Prime[index]
	BL	printf		
	ADD	R9,R9,#1	@R9+=1
	CMP	R7,R8		@are we at the end of Primes[]?	
	BLT	PRTNEXT		@if more Primes[] then do next prime
@report runtime
	ADD	R0,FP,#8
	LDMFD	R0,{R1-R4}
	SUBS	R2,R4,R2 
	SBC	R1,R3,R1
	LDRMI	R0,aMillion	@if negative then
	ADDMI	R2,R0		@fix-up by adding aMillion
	LDR	R0,RTIME
	BL	printf	
	MOV	R0,#0		@set 0 return code
	ADD	SP,SP,#1015808*4	@restore SP for reg loading	
	LDMFD	SP!,{R1-R12}	@restore working regs
	LDR	LR,[SP],#24	@restore LinkReg
	BX	LR		@return to caller
	
PRTSTR:	.asciz	"Prime[%d]=%d\n"
RTIME:	.word	RUNTIME
aMillion: .word 0xF4240
	
