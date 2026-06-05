// DecompChannelChain.java
// Comprehensive decompilation dump of the select-channel / poll / read call graph
// in ElfMPort.exe, 2 levels deep, so analysis agents can reason over the C text
// without each spawning its own Ghidra run.
//
// Run (against the SAVED, pre-analyzed project, -process mode = fast):
//   JAVA_HOME=re/jdk21 re/ghidra/support/analyzeHeadless re/project ElfMPort \
//     -process ElfMPort.exe -noanalysis \
//     -scriptPath re/scripts -postScript DecompChannelChain.java \
//     > re/logs/chain_dump.log 2>&1

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompChannelChain extends GhidraScript {
  DecompInterface dec;
  FunctionManager fm;
  ConsoleTaskMonitor mon;
  Set<Long> dumped = new HashSet<>();

  // Seed functions: the known landmarks of the read path.
  long[] seeds = {
    0x40c0f0L,  // FUN_0040c0f0  select-channel builder  <-- PRIME TARGET
    0x409b60L,  // FUN_00409b60  OnConnect (calls select-channel with chan from +0x82)
    0x40cbd0L,  // FUN_0040cbd0  sendCommand (transport, retries 15x/333ms)
    0x4471a0L,  // FUN_004471a0  WritePort
    0x4468b0L,  // FUN_004468b0  ReadPort
    0x409d50L,  // FUN_00409d50  ButtCellDevice::OnNewDataAvailable (parses [v][~v])
    0x432ad0L,  // FUN_00432ad0  sendAndAck (posts to async message queue)
    0x446f30L,  // FUN_00446f30  CCommHandler connect (init sequence)
  };

  String decompile(Function fn) {
    DecompileResults r = dec.decompileFunction(fn, 240, mon);
    if (r != null && r.decompileCompleted()) return r.getDecompiledFunction().getC();
    return "// <decompile failed>";
  }

  void dump(Function fn, String tag, int depth) {
    if (fn == null) return;
    long off = fn.getEntryPoint().getOffset();
    if (!dumped.add(off)) return;  // de-dupe
    println("\n// ============================================================");
    println("// " + tag + "  " + fn.getName() + " @ " + fn.getEntryPoint()
            + "   (depth " + depth + ")");
    println("// ============================================================");
    println(decompile(fn));

    if (depth > 0) {
      // Recurse into callees one level shallower.
      Set<Function> callees;
      try { callees = fn.getCalledFunctions(mon); }
      catch (Exception e) { callees = Collections.emptySet(); }
      // Sort callees by address for stable output.
      List<Function> sorted = new ArrayList<>(callees);
      sorted.sort(Comparator.comparing(f -> f.getEntryPoint().getOffset()));
      for (Function c : sorted) {
        // Skip obvious library/thunk noise to keep the dump focused.
        String nm = c.getName();
        if (c.isThunk()) continue;
        if (nm.startsWith("FID_") ) continue;
        dump(c, "  callee-of " + fn.getName(), depth - 1);
      }
    }
  }

  public void run() throws Exception {
    dec = new DecompInterface();
    DecompileOptions opts = new DecompileOptions();
    dec.setOptions(opts);
    dec.openProgram(currentProgram);
    fm = currentProgram.getFunctionManager();
    mon = new ConsoleTaskMonitor();

    println("// ===== ElfMPort.exe select-channel/read call-graph dump (2 levels) =====");
    println("// seeds = select-channel chain landmarks; callees expanded 2 deep");
    for (long s : seeds) {
      Function fn = fm.getFunctionContaining(toAddr(s));
      if (fn == null) { println("// none @ " + Long.toHexString(s)); continue; }
      dump(fn, "SEED", 2);
    }
    println("\n// Total functions dumped: " + dumped.size());
    println("DECOMP_DONE");
  }
}
