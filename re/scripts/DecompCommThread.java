// DecompCommThread.java
// Step-3 follow-up: decompile the CommunicationThread loop body and the
// per-frame poll/work functions to find the device WRITE issued each frame.
//
// Seeds come straight from FUN_004313a0 (CPausebleWorker<CommunicationThread>::operator()):
//   loop:  while (FUN_004319d0()) { FUN_005aef40(); FUN_00433920(); FUN_00434c10(); }
// FUN_00434c10 is the CommunicationThread-specific per-iteration work (poll the device).
// We expand each seed 2 levels deep so the per-frame WritePort is visible.
//
// Run:
//   JAVA_HOME="$P/re/jdk21" "$P/re/ghidra/support/analyzeHeadless" "$P/re/project" ElfMPort \
//     -process ElfMPort.exe -noanalysis -scriptPath "$P/re/scripts" \
//     -postScript DecompCommThread.java > "$P/re/logs/comm_thread.log" 2>&1

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompCommThread extends GhidraScript {
  DecompInterface dec;
  FunctionManager fm;
  ConsoleTaskMonitor mon;
  Set<Long> dumped = new HashSet<>();

  long[] seeds = {
    0x4313a0L,  // CPausebleWorker<CommunicationThread>::operator()  (the run loop)
    0x431120L,  // CPausebleWorker<AutoconnectionThread>::operator()
    0x4319d0L,  // CommunicationThread loop-continue / ServicePauseRequests test
    0x433920L,  // shared per-iteration work (pause servicing?)
    0x434c10L,  // CommunicationThread-specific per-frame work  <-- PRIME (poll device)
    0x4348a0L,  // AutoconnectionThread-specific per-iteration work
    0x40bd00L,  // SetFrameRate writer (issues "setting frame rate" command)
  };

  String decompile(Function fn) {
    DecompileResults r = dec.decompileFunction(fn, 240, mon);
    if (r != null && r.decompileCompleted()) return r.getDecompiledFunction().getC();
    return "// <decompile failed>";
  }

  void dump(Function fn, String tag, int depth) {
    if (fn == null) return;
    long off = fn.getEntryPoint().getOffset();
    if (!dumped.add(off)) return;
    println("\n// ============================================================");
    println("// " + tag + "  " + fn.getName() + " @ " + fn.getEntryPoint() + "  (depth " + depth + ")");
    println("// ============================================================");
    println(decompile(fn));
    if (depth > 0) {
      Set<Function> callees;
      try { callees = fn.getCalledFunctions(mon); }
      catch (Exception e) { callees = Collections.emptySet(); }
      List<Function> sorted = new ArrayList<>(callees);
      sorted.sort(Comparator.comparing(f -> f.getEntryPoint().getOffset()));
      for (Function c : sorted) {
        if (c.isThunk()) continue;
        if (c.getName().startsWith("FID_")) continue;
        dump(c, "  callee-of " + fn.getName(), depth - 1);
      }
    }
  }

  public void run() throws Exception {
    dec = new DecompInterface();
    dec.setOptions(new DecompileOptions());
    dec.openProgram(currentProgram);
    fm = currentProgram.getFunctionManager();
    mon = new ConsoleTaskMonitor();

    println("// ===== CommunicationThread loop / per-frame poll dump =====");
    for (long s : seeds) {
      Function fn = fm.getFunctionContaining(toAddr(s));
      if (fn == null) { println("// none @ " + Long.toHexString(s)); continue; }
      dump(fn, "SEED", 2);
    }
    println("\n// Total functions dumped: " + dumped.size());
    println("DECOMP_DONE");
  }
}
