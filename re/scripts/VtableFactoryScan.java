// VtableFactoryScan.java — find the command-FACTORY interface vtable: a large
// vtable (>=19 slots so slot 0x48 exists) whose slots 0xc, 0x14, 0x48 are all
// valid functions. Decompile slot 0x14 (make-set-rate) AND follow one level into
// any function it calls (the command constructor that sets opcode '9').
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.util.*;

public class VtableFactoryScan extends GhidraScript {
  DecompInterface dec; FunctionManager fm; Memory mem;
  ghidra.util.task.ConsoleTaskMonitor monitor = new ghidra.util.task.ConsoleTaskMonitor();

  boolean isFn(long v){ try{ return v>=0x401000L&&v<=0x5b0000L&&fm.getFunctionAt(toAddr(v))!=null; }catch(Exception e){return false;} }
  String nm(long v){ try{ Function f=fm.getFunctionAt(toAddr(v)); return f==null?"?":f.getName(); }catch(Exception e){return "?";} }
  long rd(long a){ try{ return ((long)mem.getInt(toAddr(a)))&0xffffffffL; }catch(Exception e){return 0;} }
  String dC(long v){ Function f=fm.getFunctionAt(toAddr(v)); if(f==null)return "// none @"+Long.toHexString(v);
    DecompileResults r=dec.decompileFunction(f,240,monitor);
    return r!=null&&r.decompileCompleted()?r.getDecompiledFunction().getC():"// fail"; }

  public void run(){
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); mem=currentProgram.getMemory();
    println("// ===== VtableFactoryScan: large vtables w/ slots 0xc,0x14,0x48 valid =====");
    List<long[]> hits=new ArrayList<>();
    for (long base=0x5b0000L; base<=0x5e0000L; base+=4){
      int n=0; while(isFn(rd(base+n*4L))){ n++; if(n>60)break; }
      if (n<19){ if(n>0) base+=(n-1)*4L; continue; }
      long s0c=rd(base+0xcL), s14=rd(base+0x14L), s48=rd(base+0x48L);
      if (isFn(s0c)&&isFn(s14)&&isFn(s48)&&s0c!=s14){
        hits.add(new long[]{base,s0c,s14,s48});
        println(String.format("// VT 0x%06x slots=%2d [0xc]->%-18s [0x14]->%-18s [0x48]->%-18s",
                base,n,nm(s0c),nm(s14),nm(s48)));
      }
      base+=(n-1)*4L;
    }
    println("\n// ===== "+hits.size()+" candidates; decompile slot 0x14 + its callees (find opcode) =====");
    int shown=0;
    for (long[] h: hits){
      if (shown++>10){ println("// (truncated)"); break; }
      long s14=h[2];
      println("\n// ######### VT 0x"+Long.toHexString(h[0])+" SLOT 0x14 -> "+nm(s14)+" @0x"+Long.toHexString(s14)+" #########");
      String c = dC(s14);
      println(c);
      // follow one level into callees to find the command constructor (opcode setter)
      Function f=fm.getFunctionAt(toAddr(s14));
      if (f!=null){
        try{
          for (Function callee: f.getCalledFunctions(monitor)){
            if (callee.isThunk()) continue;
            long ca=callee.getEntryPoint().getOffset();
            if (ca>=0x401000&&ca<=0x4b0000){
              println("\n//   --- callee "+callee.getName()+" @ "+callee.getEntryPoint()+" ---");
              println(dC(ca));
            }
          }
        }catch(Exception e){}
      }
    }
    println("\nFACTORYSCAN_DONE");
  }
}
