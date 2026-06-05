#!/usr/bin/env python3
"""Disassemble specific functions of ElfMPort.exe (the comm core) given start VAs."""
import pefile, capstone, sys

P = "/home/vivekkarmarkar/Python Files/tekscan-connector/vendor/elf_extracted/App_Executables/ElfMPort.exe"
pe = pefile.PE(P); base = pe.OPTIONAL_HEADER.ImageBase
text = next(s for s in pe.sections if s.Name.rstrip(b'\x00') == b'.text')
code = text.get_data(); tva = base + text.VirtualAddress
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True

IATNAMES = {0x5cb040:'FT_Close',0x5cb044:'FT_Read',0x5cb048:'FT_Write',0x5cb04c:'FT_SetBaudRate',
            0x5cb050:'FT_SetDataCharacteristics',0x5cb058:'FT_Purge',0x5cb060:'FT_GetQueueStatus',
            0x5cb06c:'FT_SetBitMode'}

def dump(start, maxins=140):
    off = start - tva
    for ins in md.disasm(code[off:off+maxins*8], start):
        note = ""
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.disp in IATNAMES and op.mem.base == 0:
                note = "  ; -> " + IATNAMES[op.mem.disp]
        print(f"  {ins.address:#010x}: {ins.mnemonic:<8} {ins.op_str}{note}")
        maxins -= 1
        if maxins <= 0:
            break

for a in [int(x, 16) for x in sys.argv[1:]]:
    print(f"\n===== function {a:#x} =====")
    dump(a)
