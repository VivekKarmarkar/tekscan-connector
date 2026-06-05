// ResolveEncoder.java
// Resolve the command-ENCODER vtable used by FUN_00409480 (the object whose
// slot 0xc = select-channel encoder, slot 0x14 = SetFrameRate encoder), then
// decompile those two slot targets to recover the literal opcode bytes.
//
// Strategy (disassembly + raw memory, NOT the misleading __thiscall C):
//   1. Walk instructions of the encoder constructors (FUN_00409480, FUN_00405ac0)
//      and collect every immediate/operand address that points into initialized
//      data (candidate vtable bases).
//   2. For each candidate base V, read consecutive 4-byte pointers; if >=3 in a row
//      resolve to functions in .text, treat V as a vtable and print slots 0..9.
//   3. For any vtable whose slot 0xc and slot 0x14 both land in the 0x40bxxx/0x40cxxx
//      builder cluster, decompile slot 0xc and slot 0x14 (the encoders).
//
// Run: -process ElfMPort.exe -noanalysis -postScript ResolveEncoder.java

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class ResolveEncoder extends GhidraScript {
  DecompInterface dec;
  FunctionManager fm;
  ConsoleTaskMonitor mon;
  Memory mem;

  long[] constructors = { 0x409480L, 0x405ac0L };

  boolean looksLikeCodePtr(long v) {
    if (v < 0x401000L || v > 0x5b0000L) return false; // .text-ish range for this PE
    try {
      Address a = toAddr(v);
      if (fm.getFunctionAt(a) != null) return true;
      // also accept addresses inside a known function (thunks/labels)
      if (fm.getFunctionContaining(a) != null) return true;
    } catch (Exception e) {}
    return false;
  }

  int countVtableSlots(long base) {
    int n = 0;
    try {
      for (int i = 0; i < 24; i++) {
        long p = ((long) mem.getInt(toAddr(base + i * 4L))) & 0xffffffffL;
        if (looksLikeCodePtr(p)) n++; else break;
      }
    } catch (Exception e) {}
    return n;
  }

  String fnName(long v) {
    try {
      Function f = fm.getFunctionAt(toAddr(v));
      if (f != null) return f.getName();
      f = fm.getFunctionContaining(toAddr(v));
      if (f != null) return f.getName() + "+off";
    } catch (Exception e) {}
    return "?";
  }

  void dumpVtable(long base) {
    int slots = countVtableSlots(base);
    println("\n// ----- candidate vtable @ " + Long.toHexString(base) + "  (" + slots + " code-ptr slots) -----");
    try {
      for (int i = 0; i < Math.max(slots, 8); i++) {
        long p = ((long) mem.getInt(toAddr(base + i * 4L))) & 0xffffffffL;
        println(String.format("//   [+0x%02x] slot%-2d -> 0x%08x  %s", i*4, i, p, fnName(p)));
      }
    } catch (Exception e) { println("//   <read error>"); }
  }

  String decompile(long addr) {
    Function f = fm.getFunctionAt(toAddr(addr));
    if (f == null) f = fm.getFunctionContaining(toAddr(addr));
    if (f == null) return "// no function @ " + Long.toHexString(addr);
    DecompileResults r = dec.decompileFunction(f, 240, mon);
    String hdr = "\n// ===== decompile " + f.getName() + " @ " + f.getEntryPoint() + " =====\n";
    if (r != null && r.decompileCompleted()) return hdr + r.getDecompiledFunction().getC();
    return hdr + "// <decompile failed>";
  }

  public void run() throws Exception {
    dec = new DecompInterface(); dec.openProgram(currentProgram);
    fm = currentProgram.getFunctionManager(); mon = new ConsoleTaskMonitor();
    mem = currentProgram.getMemory();

    println("// ===== ResolveEncoder: find encoder vtable (slot 0xc=select-chan, 0x14=set-rate) =====");

    Set<Long> candidates = new TreeSet<>();
    // 1. Collect data addresses referenced by the constructors.
    for (long c : constructors) {
      Function fn = fm.getFunctionContaining(toAddr(c));
      if (fn == null) { println("// no ctor @ " + Long.toHexString(c)); continue; }
      println("\n// --- ctor " + fn.getName() + " @ " + fn.getEntryPoint() + " instruction refs ---");
      InstructionIterator it = currentProgram.getListing().getInstructions(fn.getBody(), true);
      while (it.hasNext()) {
        Instruction insn = it.next();
        for (Reference ref : insn.getReferencesFrom()) {
          Address to = ref.getToAddress();
          if (to == null) continue;
          long v = to.getOffset();
          // a vtable base is data with code pointers; record any data-ish ref
          if (v >= 0x5b0000L && v <= 0x650000L) {  // .rdata/.data range
            if (countVtableSlots(v) >= 3) {
              candidates.add(v);
              println("//   " + insn.getAddress() + ": " + insn + "   -> VTABLE? 0x" + Long.toHexString(v));
            }
          }
        }
        // also catch raw scalar immediates that point into rdata (MOV reg, imm32)
        for (int oi = 0; oi < insn.getNumOperands(); oi++) {
          ghidra.program.model.scalar.Scalar s = insn.getScalar(oi);
          if (s != null) {
            long v = s.getUnsignedValue();
            if (v >= 0x5b0000L && v <= 0x650000L && countVtableSlots(v) >= 3) {
              candidates.add(v);
              println("//   " + insn.getAddress() + ": " + insn + "   -> imm VTABLE? 0x" + Long.toHexString(v));
            }
          }
        }
      }
    }

    println("\n// ===== candidate vtables found: " + candidates.size() + " =====");
    long encoderVtable = 0;
    for (long v : candidates) {
      dumpVtable(v);
      // Identify the encoder: slot 0xc and 0x14 both point into the builder cluster.
      try {
        long s0c = ((long) mem.getInt(toAddr(v + 0xcL))) & 0xffffffffL;
        long s14 = ((long) mem.getInt(toAddr(v + 0x14L))) & 0xffffffffL;
        if (looksLikeCodePtr(s0c) && looksLikeCodePtr(s14)) {
          println("//   ^ slot0xc=0x" + Long.toHexString(s0c) + " slot0x14=0x" + Long.toHexString(s14)
                  + "  (encoder candidate)");
          if (encoderVtable == 0) encoderVtable = v;
        }
      } catch (Exception e) {}
    }

    // 3. Decompile the two encoder slots of the best candidate(s).
    println("\n// ===== DECOMPILE encoder slots (0xc select-channel, 0x14 set-frame-rate) =====");
    for (long v : candidates) {
      try {
        long s0c = ((long) mem.getInt(toAddr(v + 0xcL))) & 0xffffffffL;
        long s14 = ((long) mem.getInt(toAddr(v + 0x14L))) & 0xffffffffL;
        if (looksLikeCodePtr(s0c) && looksLikeCodePtr(s14)) {
          println("\n// ##### vtable 0x" + Long.toHexString(v) + " : slot0x14 SetFrameRate encoder #####");
          println(decompile(s14));
          println("\n// ##### vtable 0x" + Long.toHexString(v) + " : slot0xc select-channel encoder #####");
          println(decompile(s0c));
        }
      } catch (Exception e) {}
    }
    println("\nRESOLVE_DONE");
  }
}
