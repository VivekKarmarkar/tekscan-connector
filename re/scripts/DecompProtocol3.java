import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.data.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompProtocol3 extends GhidraScript {
  DecompInterface dec; FunctionManager fm; ReferenceManager rm; ConsoleTaskMonitor mon;
  Set<Long> seen = new HashSet<>();
  void dump(Function fn, String tag) {
    if (fn==null) return;
    if (!seen.add(fn.getEntryPoint().getOffset())) return;
    println("\n// ===== "+tag+"  "+fn.getName()+" @ "+fn.getEntryPoint()+" =====");
    DecompileResults r = dec.decompileFunction(fn, 160, mon);
    println(r!=null && r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// decompile failed");
  }
  public void run() throws Exception {
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); rm=currentProgram.getReferenceManager();
    mon=new ConsoleTaskMonitor();
    // Strings that name ButtCellDevice methods (logged by name) + scan/connect verbs
    String[] keys = {"ButtCellDevice::", "ButtCell"};
    Set<String> printed = new HashSet<>();
    DataIterator di = currentProgram.getListing().getDefinedData(true);
    while (di.hasNext()) {
      Data d = di.next(); Object v = d.getValue();
      if (!(v instanceof String)) continue;
      String s = (String) v;
      boolean hit = false;
      for (String k: keys) if (s.contains(k)) { hit = true; break; }
      if (!hit) continue;
      println("// STR @ " + d.getAddress() + " : " + s.replace("\n"," | "));
      for (Reference r: rm.getReferencesTo(d.getAddress()))
        dump(fm.getFunctionContaining(r.getFromAddress()), "ref@"+r.getFromAddress());
    }
    println("\nDECOMP_DONE");
  }
}
