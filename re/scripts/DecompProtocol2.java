import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.data.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompProtocol2 extends GhidraScript {
  DecompInterface dec; FunctionManager fm; ReferenceManager rm; ConsoleTaskMonitor mon;
  Set<Long> seen = new HashSet<>();
  void dump(Function fn, String tag) {
    if (fn==null) return;
    if (!seen.add(fn.getEntryPoint().getOffset())) return;
    println("\n// ===== "+tag+"  "+fn.getName()+" @ "+fn.getEntryPoint()+" =====");
    DecompileResults r = dec.decompileFunction(fn, 120, mon);
    println(r!=null && r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// decompile failed");
  }
  void dumpAddr(long a, String t){ dump(fm.getFunctionContaining(toAddr(a)), t); }
  void refs(long a, String t){
    for (Reference r: rm.getReferencesTo(toAddr(a)))
      dump(fm.getFunctionContaining(r.getFromAddress()), t+"@"+r.getFromAddress());
  }
  public void run() throws Exception {
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); rm=currentProgram.getReferenceManager();
    mon=new ConsoleTaskMonitor();
    // remaining connect helpers (confirm pure-FTDI)
    for (long a: new long[]{0x447180L,0x446d20L,0x446a00L,0x446c20L,0x446d50L,0x446e40L})
      dumpAddr(a,"helper");
    println("\n//#### WritePort DIRECT callers ####"); refs(0x4471a0L,"WPdirect");
    println("\n//#### WritePort VTABLE-SLOT (virtual) callers ####"); refs(0x5d2148L,"WPvslot");
    println("\n//#### sensitivity string xrefs ####");
    DataIterator di=currentProgram.getListing().getDefinedData(true);
    while (di.hasNext()){
      Data d=di.next(); Object v=d.getValue();
      if (v instanceof String){
        String s=((String)v);
        if (s.toLowerCase().contains("sensitiv")){
          println("// STR @ "+d.getAddress()+" : "+s);
          for (Reference r: rm.getReferencesTo(d.getAddress()))
            dump(fm.getFunctionContaining(r.getFromAddress()),"SENS@"+r.getFromAddress());
        }
      }
    }
    println("\nDECOMP_DONE");
  }
}
