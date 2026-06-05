import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompProtocol4 extends GhidraScript {
  public void run() throws Exception {
    DecompInterface dec = new DecompInterface(); dec.openProgram(currentProgram);
    FunctionManager fm = currentProgram.getFunctionManager();
    ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
    Set<Long> seen = new HashSet<>();
    long[] targets = {0x40c0f0L,0x40bc50L,0x40bc00L,0x40ba00L,0x40b640L,0x40bc80L,
                      0x40bcc0L,0x40bc20L,0x40bd00L,0x40be30L,0x40c720L,0x40f610L,0x40f3d0L};
    for (long a: targets) {
      Function fn = fm.getFunctionContaining(toAddr(a));
      if (fn==null) { println("// none @ "+Long.toHexString(a)); continue; }
      if (!seen.add(fn.getEntryPoint().getOffset())) continue;
      println("\n// ===== "+fn.getName()+" @ "+fn.getEntryPoint()+" =====");
      DecompileResults r = dec.decompileFunction(fn, 160, mon);
      println(r!=null && r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// fail");
    }
    println("\nDECOMP_DONE");
  }
}
