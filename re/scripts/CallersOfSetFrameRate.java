// CallersOfSetFrameRate.java
// Find who CALLS the SetFrameRate writer FUN_0040bd00 (and StartRecording handlers),
// to confirm the UI -> start-acquisition trigger path.
//
//   JAVA_HOME="$P/re/jdk21" "$P/re/ghidra/support/analyzeHeadless" "$P/re/project" ElfMPort \
//     -process ElfMPort.exe -noanalysis -scriptPath "$P/re/scripts" \
//     -postScript CallersOfSetFrameRate.java > "$P/re/logs/setrate_callers.log" 2>&1

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Reference;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class CallersOfSetFrameRate extends GhidraScript {
  public void run() throws Exception {
    DecompInterface dec = new DecompInterface();
    dec.setOptions(new DecompileOptions());
    dec.openProgram(currentProgram);
    FunctionManager fm = currentProgram.getFunctionManager();
    ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

    long[] targets = {
      0x40bd00L,  // SetFrameRate writer
      0x45f270L,  // StartRecording dispatch a
      0x45f300L,  // StartRecording dispatch b
    };
    Set<Long> dumped = new HashSet<>();
    for (long t : targets) {
      Function tgt = fm.getFunctionContaining(toAddr(t));
      if (tgt == null) { println("// no func @ " + Long.toHexString(t)); continue; }
      println("\n// ===== CALLERS of " + tgt.getName() + " @ " + tgt.getEntryPoint() + " =====");
      Set<Function> callers = tgt.getCallingFunctions(mon);
      List<Function> sorted = new ArrayList<>(callers);
      sorted.sort(Comparator.comparing(f -> f.getEntryPoint().getOffset()));
      for (Function c : sorted)
        println("//   caller: " + c.getName() + " @ " + c.getEntryPoint());
      // decompile each caller once
      for (Function c : sorted) {
        if (!dumped.add(c.getEntryPoint().getOffset())) continue;
        println("\n// ---- caller " + c.getName() + " @ " + c.getEntryPoint() + " ----");
        DecompileResults r = dec.decompileFunction(c, 180, mon);
        if (r != null && r.decompileCompleted()) println(r.getDecompiledFunction().getC());
        else println("// <decompile failed>");
      }
    }
    println("DECOMP_DONE");
  }
}
