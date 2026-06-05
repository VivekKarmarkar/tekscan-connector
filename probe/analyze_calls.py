#!/usr/bin/env python3
"""Disassemble ElfMPort.exe and dump context around each FTDI call site, so we can
read the baud, serial format, bit mode, and the command bytes written to the handle."""
import pefile, capstone, re
from collections import Counter

P = "/home/vivekkarmarkar/Python Files/tekscan-connector/vendor/elf_extracted/App_Executables/ElfMPort.exe"
IAT = {0x5cb040:'FT_Close',0x5cb044:'FT_Read',0x5cb048:'FT_Write',0x5cb04c:'FT_SetBaudRate',
       0x5cb050:'FT_SetDataCharacteristics',0x5cb054:'FT_SetFlowControl',0x5cb058:'FT_Purge',
       0x5cb05c:'FT_SetTimeouts',0x5cb060:'FT_GetQueueStatus',0x5cb064:'FT_SetEventNotification',
       0x5cb068:'FT_SetLatencyTimer',0x5cb06c:'FT_SetBitMode',0x5cb070:'FT_StopInTask',
       0x5cb074:'FT_RestartInTask',0x5cb078:'FT_CreateDeviceInfoList',0x5cb07c:'FT_OpenEx',
       0x5cb080:'FT_GetDeviceInfoList'}

pe = pefile.PE(P); base = pe.OPTIONAL_HEADER.ImageBase
text = next(s for s in pe.sections if s.Name.rstrip(b'\x00') == b'.text')
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
insns = list(md.disasm(text.get_data(), base + text.VirtualAddress))

sites = []
for i, ins in enumerate(insns):
    if ins.mnemonic == 'call' and 'ptr' in ins.op_str:
        m = re.search(r'0x([0-9a-f]+)', ins.op_str)
        if m and int(m.group(1), 16) in IAT:
            sites.append((i, ins.address, IAT[int(m.group(1), 16)]))

print("call-site counts:", dict(Counter(n for _, _, n in sites)))
WANT = {'FT_SetBaudRate','FT_SetDataCharacteristics','FT_SetBitMode',
        'FT_SetLatencyTimer','FT_SetTimeouts','FT_OpenEx'}
seen_write = 0
for i, addr, name in sites:
    if name == 'FT_Write':
        seen_write += 1
        if seen_write > 8:    # cap noisy FT_Write dumps
            continue
    elif name not in WANT:
        continue
    print(f"\n### {name} @ {addr:#x}")
    for j in range(max(0, i - 16), i + 1):
        ins = insns[j]
        print(f"  {ins.address:#010x}: {ins.mnemonic:<7} {ins.op_str}")
