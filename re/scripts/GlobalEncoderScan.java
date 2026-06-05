// GlobalEncoderScan.java — find the command-encoder vtable by signature:
// a vtable whose slot 0xc (select-channel) and slot 0x14 (set-frame-rate) both
// point to small functions; decompile the slot 0x14 (and 0xc) targets to read
// the literal ASCII opcode bytes (expect '9'=0x39 for frame rate).
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import java.util.*;

public class GlobalEncoderScan extends GhidraScript {
  DecompInterface dec; FunctionManager fm; Memory mem;
  ghidra.util.task.ConsoleTaskMonitor monitor = new ghidra.util.task.ConsoleTaskMonitor();

  boolean isFn(long v){ try{ return v>=0x401000L&&v<=0x5b0000L&&fm.getFunctionAt(toAddr(v))!=null; }catch(Exception e){return false;} }
  long fnSize(long v){ try{ Function f=fm.getFunctionAt(toAddr(v)); return f==null?99999:f.getBody().getNumAddresses(); }catch(Exception e){return 99999;} }
  String nm(long v){ try{ Function f=fm.getFunctionAt(toAddr(v)); return f==null?"?":f.getName(); }catch(Exception e){return "?";} }
  long rd(long a){ try{ return ((long)mem.getInt(toAddr(a)))&0xffffffffL; }catch(Exception e){return 0;} }

  String decompile(long v){ Function f=fm.getFunctionAt(toAddr(v)); if(f==null)return "// none";
    DecompileResults r=dec.decompileFunction(f,200,monitor);
    return r!=null&&r.decompileCompleted()?r.getDecompiledFunction().getC():"// fail"; }

  public void run(){
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); mem=currentProgram.getMemory();
    println("// ===== GlobalEncoderScan: vtables with slot0xc & slot0x14 -> small fns =====");
    List<long[]> hits = new ArrayList<>();   // {base, slot0xc, slot0x14}
    // scan rdata/data region for vtables (>=8 consecutive code ptrs)
    for (long base = 0x5b0000L; base <= 0x5e0000L; base += 4) {
      int n=0; while (isFn(rd(base + n*4L))) { n++; if(n>40)break; }
      if (n < 6) continue;
      long s0c = rd(base + 0xcL), s14 = rd(base + 0x14L);
      if (!isFn(s0c) || !isFn(s14)) { base += (n-1)*4L; continue; }
      // encoder heuristic: both slot targets are SMALL functions (command builders)
      if (fnSize(s0c) < 400 && fnSize(s14) < 400 && s0c != s14) {
        hits.add(new long[]{base, s0c, s14});
        println(String.format("// VT 0x%06x  slots=%2d  [0xc]->0x%06x %-22s  [0x14]->0x%06x %-22s",
                 base, n, s0c, nm(s0c), s14, nm(s14)));
      }
      base += (n-1)*4L; // skip past this vtable
    }
    println("\n// ===== candidate encoder vtables: " + hits.size() + " =====");
    // Decompile slot 0x14 (and 0xc) of each hit; the real one emits opcode '9' (0x39) + period.
    int shown=0;
    for (long[] h : hits) {
      if (shown++ > 8) { println("// (truncated decompiles at 8 candidates)"); break; }
      println("\n// ##### VT 0x"+Long.toHexString(h[0])+" slot0x14 (set-rate?) @ 0x"+Long.toHexString(h[2])+" "+nm(h[2])+" #####");
      println(decompile(h[2]));
      println("\n// ##### VT 0x"+Long.toHexString(h[0])+" slot0xc (select-chan?) @ 0x"+Long.toHexString(h[1])+" "+nm(h[1])+" #####");
      println(decompile(h[1]));
    }
    println("\nGLOBALSCAN_DONE");
  }
}
