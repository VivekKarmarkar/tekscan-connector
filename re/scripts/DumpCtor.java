// DumpCtor.java — print full disassembly (with refs) + decompile of the encoder
// constructors and the select-channel builder, so the vtable install is visible.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.util.task.ConsoleTaskMonitor;

public class DumpCtor extends GhidraScript {
  DecompInterface dec; FunctionManager fm; ConsoleTaskMonitor mon;
  long[] targets = { 0x409480L, 0x405ac0L, 0x40c0f0L, 0x40bd00L };

  void dumpAsm(long a) {
    Function fn = fm.getFunctionContaining(toAddr(a));
    if (fn == null) { println("// no fn @ " + Long.toHexString(a)); return; }
    println("\n// ========== DISASM " + fn.getName() + " @ " + fn.getEntryPoint() + " ==========");
    InstructionIterator it = currentProgram.getListing().getInstructions(fn.getBody(), true);
    while (it.hasNext()) {
      Instruction insn = it.next();
      StringBuilder sb = new StringBuilder();
      sb.append(insn.getAddress()).append("  ").append(insn.toString());
      Reference[] refs = insn.getReferencesFrom();
      for (Reference r : refs) {
        Address to = r.getToAddress();
        Symbol s = (to != null) ? getSymbolAt(to) : null;
        sb.append("   ; ref-> ").append(to);
        if (s != null) sb.append(" (").append(s.getName()).append(")");
      }
      println(sb.toString());
    }
  }

  void dumpC(long a) {
    Function fn = fm.getFunctionContaining(toAddr(a));
    if (fn == null) return;
    DecompileResults r = dec.decompileFunction(fn, 200, mon);
    println("\n// ---------- C " + fn.getName() + " ----------");
    println(r != null && r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// fail");
  }

  public void run() {
    dec = new DecompInterface(); dec.openProgram(currentProgram);
    fm = currentProgram.getFunctionManager(); mon = new ConsoleTaskMonitor();
    for (long t : targets) { dumpAsm(t); dumpC(t); }
    println("\nDUMPCTOR_DONE");
  }
}
