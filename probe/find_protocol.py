#!/usr/bin/env python3
"""Find the command framing in ElfMPort.exe: locate protocol strings, find code
xrefs to them, and dump the surrounding functions (the FW-version + scan methods
that build command buffers and call FT_Write/FT_Read)."""
import pefile, capstone
from capstone import x86

P = "/home/vivekkarmarkar/Python Files/tekscan-connector/vendor/elf_extracted/App_Executables/ElfMPort.exe"
pe = pefile.PE(P); base = pe.OPTIONAL_HEADER.ImageBase
secs = {s.Name.rstrip(b'\x00').decode('latin1','ignore'): (base+s.VirtualAddress, s.get_data()) for s in pe.sections}

targets = [b"GetFWversion", b"Get FW version", b"reading firmware version", b"ScanComplete"]
strvas = {}
for name, (va, d) in secs.items():
    for t in targets:
        i = 0
        while (k := d.find(t, i)) >= 0:
            strvas.setdefault(t.decode(), []).append(va + k); i = k + 1
print("=== protocol string VAs ===")
for t, vs in strvas.items(): print(f"  {t!r}: {[hex(v) for v in vs]}")

tva, td = secs['.text']
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
insns = list(md.disasm(td, tva))
allvas = {v for vs in strvas.values() for v in vs}

print("\n=== code xrefs to those strings ===")
for i, ins in enumerate(insns):
    hit = any(op.type == x86.X86_OP_IMM and op.imm in allvas for op in ins.operands)
    if hit:
        print(f"\n### xref @ {ins.address:#x}  ({ins.mnemonic} {ins.op_str})")
        for j in range(max(0, i - 34), min(len(insns), i + 5)):
            print(f"  {insns[j].address:#010x}: {insns[j].mnemonic:<7} {insns[j].op_str}")
