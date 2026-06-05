// DumpConstants.java — read the double constants used by the SetFrameRate
// request encoder FUN_0045e730: value = (C1/Hz - C2)*scale_band + C3.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.Memory;

public class DumpConstants extends GhidraScript {
  double rd(long a){
    try{ long bits = ((long)currentProgram.getMemory().getInt(toAddr(a))&0xffffffffL)
                   | (((long)currentProgram.getMemory().getInt(toAddr(a+4)))<<32);
      return Double.longBitsToDouble(bits);
    }catch(Exception e){ return Double.NaN; }
  }
  void show(String nm,long a){ println(String.format("// %-14s @0x%06x = %.10g", nm, a, rd(a))); }
  public void run(){
    println("// SetFrameRate encoder (FUN_0045e730) constants:");
    show("C1_num",   0x5cc470L);   // DAT_005cc470  numerator (C1/Hz)
    show("C2_off",   0x5d38c0L);   // _DAT_005d38c0 subtracted offset
    show("C3_add",   0x5ccc08L);   // DAT_005ccc08  final addend
    println("// per-band scale (dVar11):");
    show("scale_0x30", 0x5d38c8L); // 6-11 Hz
    show("scale_0x20", 0x5d38d0L); // 12-22 Hz
    show("scale_0x10", 0x5d38d8L); // 23-45 Hz
    show("scale_0x00", 0x5d38e0L); // 46-91 Hz
    show("scale_0x50", 0x5d38e8L); // 92-183 Hz
    show("scale_0x40", 0x5d38f0L); // >=184 Hz
    println("DUMPCONST_DONE");
  }
}
