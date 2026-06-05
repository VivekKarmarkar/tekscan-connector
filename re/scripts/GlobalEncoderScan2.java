// GlobalEncoderScan2.java — find the ButtCell command-encoder vtable: a vtable
// whose slot 0xc and slot 0x14 BOTH target distinct functions in the ButtCell
// builder cluster [0x409000, 0x40e000]. Decompile those slot targets.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.util.*;

public class GlobalEncoderScan2 extends GhidraScript {
  DecompInterface dec; FunctionManager fm; Memory mem;
  ghidra.util.task.ConsoleTaskMonitor monitor = new ghidra.util.task.ConsoleTaskMonitor();
  static final long LO=0x409000L, HI=0x40e000L;   // ButtCell builder cluster

  boolean isFn(long v){ try{ return v>=0x401000L&&v<=0x5b0000L&&fm.getFunctionAt(toAddr(v))!=null; }catch(Exception e){return false;} }
  boolean inCluster(long v){ return v>=LO && v<HI; }
  String nm(long v){ try{ Function f=fm.getFunctionAt(toAddr(v)); return f==null?"?":f.getName(); }catch(Exception e){return "?";} }
  long rd(long a){ try{ return ((long)mem.getInt(toAddr(a)))&0xffffffffL; }catch(Exception e){return 0;} }
  String decompile(long v){ Function f=fm.getFunctionAt(toAddr(v)); if(f==null)return "// none";
    DecompileResults r=dec.decompileFunction(f,240,monitor);
    return r!=null&&r.decompileCompleted()?r.getDecompiledFunction().getC():"// fail"; }

  public void run(){
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); mem=currentProgram.getMemory();
    println("// ===== GlobalEncoderScan2: vtables w/ slot0xc & slot0x14 in ButtCell cluster =====");
    List<long[]> hits=new ArrayList<>();
    for (long base=0x5b0000L; base<=0x5e0000L; base+=4){
      int n=0; while(isFn(rd(base+n*4L))){ n++; if(n>50)break; }
      if (n<5){ continue; }
      long s0c=rd(base+0xcL), s14=rd(base+0x14L);
      if (isFn(s0c)&&isFn(s14)&&s0c!=s14&&inCluster(s0c)&&inCluster(s14)){
        hits.add(new long[]{base,s0c,s14});
        // count how many slots land in the cluster (encoder vtables are cluster-dense)
        int dense=0; for(int i=0;i<n;i++){ long p=rd(base+i*4L); if(inCluster(p))dense++; }
        println(String.format("// VT 0x%06x slots=%2d cluster=%2d  [0xc]->0x%06x %-20s [0x14]->0x%06x %-20s",
                base,n,dense,s0c,nm(s0c),s14,nm(s14)));
      }
      base+=(n-1)*4L;
    }
    println("\n// ===== hits: "+hits.size()+" — decompiling slot 0x14 (set-rate) & 0xc (select) =====");
    for (long[] h: hits){
      println("\n// ######### VT 0x"+Long.toHexString(h[0])+"  SLOT 0x14 -> "+nm(h[2])+" @0x"+Long.toHexString(h[2])+" #########");
      println(decompile(h[2]));
      println("\n// ######### VT 0x"+Long.toHexString(h[0])+"  SLOT 0xc -> "+nm(h[1])+" @0x"+Long.toHexString(h[1])+" #########");
      println(decompile(h[1]));
    }
    println("\nGLOBALSCAN2_DONE");
  }
}
