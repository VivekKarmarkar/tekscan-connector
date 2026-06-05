#!/usr/bin/env python3
"""Trace one level up from the FTDI wrappers to the methods that supply the real
constants (baud, data format, bit mode) and the FT_Write command buffers."""
import pefile, capstone, re

P = "/home/vivekkarmarkar/Python Files/tekscan-connector/vendor/elf_extracted/App_Executables/ElfMPort.exe"
IAT = {0x5cb040:'FT_Close',0x5cb044:'FT_Read',0x5cb048:'FT_Write',0x5cb04c:'FT_SetBaudRate',
       0x5cb050:'FT_SetDataCharacteristics',0x5cb054:'FT_SetFlowControl',0x5cb058:'FT_Purge',
       0x5cb05c:'FT_SetTimeouts',0x5cb068:'FT_SetLatencyTimer',0x5cb06c:'FT_SetBitMode',
       0x5cb07c:'FT_OpenEx'}
pe = pefile.PE(P); base = pe.OPTIONAL_HEADER.ImageBase
text = next(s for s in pe.sections if s.Name.rstrip(b'\x00') == b'.text')
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
insns = list(md.disasm(text.get_data(), base + text.VirtualAddress))

def find_entry(i):
    for j in range(i, max(0, i - 6000), -1):
        if (insns[j].mnemonic == 'push' and insns[j].op_str == 'ebp'
                and j + 1 < len(insns) and insns[j+1].mnemonic == 'mov'
                and insns[j+1].op_str == 'ebp, esp'):
            return insns[j].address
    return None

sites = {}
for i, ins in enumerate(insns):
    if ins.mnemonic == 'call' and 'ptr' in ins.op_str:
        m = re.search(r'0x([0-9a-f]+)', ins.op_str)
        if m and int(m.group(1), 16) in IAT:
            sites.setdefault(IAT[int(m.group(1), 16)], []).append(i)

def callers(entry):
    e = hex(entry)
    return [i for i, ins in enumerate(insns) if ins.mnemonic == 'call' and ins.op_str == e]

for fn in ['FT_SetBaudRate', 'FT_SetDataCharacteristics', 'FT_SetBitMode', 'FT_Write']:
    for ci in sites.get(fn, []):
        entry = find_entry(ci)
        cs = callers(entry) if entry else []
        print(f"\n##### {fn}: wrapper@{entry:#x}  callers={[hex(insns[c].address) for c in cs][:6]}")
        for c in cs[:3]:
            print(f"  --- caller @ {insns[c].address:#x} ---")
            for j in range(max(0, c - 20), c + 1):
                print(f"    {insns[j].address:#010x}: {insns[j].mnemonic:<7} {insns[j].op_str}")
