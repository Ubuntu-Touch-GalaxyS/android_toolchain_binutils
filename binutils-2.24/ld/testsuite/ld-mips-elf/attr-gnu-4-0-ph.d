#source: attr-gnu-4-0.s -mips32r2 -32 -EB
#ld: -melf32btsmip -e 0
#objdump: -p

[^:]*:     file format elf32-tradbigmips

Program Header:
0x70000003 off    0x000000.. vaddr 0x004000.. paddr 0x004000.. align 2\*\*3
         filesz 0x00000018 memsz 0x00000018 flags r--
#...
    LOAD off    0x00000000 vaddr 0x00400000 paddr 0x00400000 align 2\*\*16
         filesz 0x000000.. memsz 0x000000.. flags r--
private flags = 70001000: \[abi=O32\] \[mips32r2\] \[not 32bitmode\]

MIPS ABI Flags Version: 0

ISA: .*
GPR size: 32
CPR1 size: 32
CPR2 size: 0
FP ABI: Hard or soft float
ISA Extension: None
ASEs:
	None
FLAGS 1: 00000000
FLAGS 2: 00000000