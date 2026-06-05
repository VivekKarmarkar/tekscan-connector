#!/usr/bin/env python3
"""Dump a function of ElfMPort.exe with virtual calls resolved against the
reconstructed CCommHandler vtable (slot offset -> method address)."""
import pefile, capstone, sys, re

P="/home/vivekkarmarkar/Python Files/tekscan-connector/vendor/elf_extracted/App_Executables/ElfMPort.exe"
pe=pefile.PE(P); base=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\x00')==b'.text')
code=text.get_data(); tva=base+text.VirtualAddress
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
insns=list(md.disasm(code, tva))
idx={ins.address:i for i,ins in enumerate(insns)}

# CCommHandler vtable: offset(=slot*4) -> method VA
VT={0x00:0x446500,0x04:0x4466a0,0x08:0x446f30,0x0c:0x4470c0,0x10:0x4468b0,
    0x14:0x4471a0,0x18:0x446680,0x1c:0x446570,0x20:0x42d310,0x24:0x446560,
    0x28:0x446670,0x2c:0x446690,0x30:0x42d340,0x34:0x42d2e0,0x38:0x42d300,
    0x3c:0x42d2f0,0x40:0x42d320,0x44:0x446530}
NAME={0x4471a0:'WritePort/FT_Write'}

def find_entry(addr):
    i=idx.get(addr)
    if i is None:
        # nearest below
        i=max(j for j,ins in enumerate(insns) if ins.address<=addr)
    for j in range(i,max(0,i-8000),-1):
        if insns[j].mnemonic=='push' and insns[j].op_str=='ebp' and insns[j+1].op_str=='ebp, esp':
            return j
    return i

def dump(addr, maxn=150):
    i=find_entry(addr)
    for k in range(i, min(len(insns), i+maxn)):
        ins=insns[k]; note=""
        m=re.search(r'\[e\w\w \+ (0x[0-9a-f]+)\]', ins.op_str)
        if ins.mnemonic=='call' and m:
            off=int(m.group(1),16)
            if off in VT:
                fn=VT[off]; note=f"   ; vcall slot {off//4} -> {fn:#x} {NAME.get(fn,'')}"
        elif ins.mnemonic=='call' and re.fullmatch(r'0x[0-9a-f]+', ins.op_str):
            note=f"   ; -> {ins.op_str}"
        print(f"  {ins.address:#010x}: {ins.mnemonic:<7} {ins.op_str}{note}")
        if ins.mnemonic=='ret': break

for a in [int(x,16) for x in sys.argv[1:]]:
    print(f"\n===== function containing {a:#x} =====")
    dump(a)
