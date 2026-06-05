// FindOpcode.java — locate where ASCII protocol opcodes are MATERIALIZED (request
// builders) vs COMPARED (response dispatcher). Scans all instructions for the
// frame-rate opcode 0x39 ('9') and neighbors, reporting containing function + role.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import java.util.*;

public class FindOpcode extends GhidraScript {
  FunctionManager fm; DecompInterface dec;
  ghidra.util.task.ConsoleTaskMonitor monitor = new ghidra.util.task.ConsoleTaskMonitor();
  // opcodes seen in the response dispatcher (ASCII): focus on 0x39 (set frame rate)
  long[] opcodes = { 0x39 };

  String fnOf(long a){ try{ Function f=fm.getFunctionContaining(toAddr(a)); return f==null?"?":f.getName()+" @"+f.getEntryPoint(); }catch(Exception e){return "?";} }

  public void run(){
    fm=currentProgram.getFunctionManager();
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    Set<Long> builderFns = new TreeSet<>();
    for (long op : opcodes){
      println("\n// ===== instructions with immediate 0x"+Long.toHexString(op)+" ('"+(char)op+"') =====");
      InstructionIterator it = currentProgram.getListing().getInstructions(true);
      while (it.hasNext()){
        Instruction insn = it.next();
        String mn = insn.getMnemonicString();
        for (int oi=0; oi<insn.getNumOperands(); oi++){
          Scalar s = insn.getScalar(oi);
          if (s!=null && s.getUnsignedValue()==op){
            String role = mn.startsWith("CMP")||mn.startsWith("SUB")||mn.startsWith("TEST") ? "COMPARE(response?)"
                        : (mn.startsWith("MOV")||mn.startsWith("PUSH")||mn.startsWith("OR")) ? "MATERIALIZE(request?)" : mn;
            Function f = fm.getFunctionContaining(insn.getAddress());
            long fa = f!=null? f.getEntryPoint().getOffset() : 0;
            println(String.format("// %s  %-28s  %-18s  in %s", insn.getAddress(), insn.toString(), role, fnOf(insn.getAddress().getOffset())));
            // collect non-dispatcher MATERIALIZE sites in the device/command cluster for decompile
            if (role.startsWith("MATERIALIZE") && fa>=0x401000 && fa<=0x4b0000) builderFns.add(fa);
          }
        }
      }
    }
    println("\n// ===== decompiling MATERIALIZE-site functions (request builders) =====");
    for (long fa : builderFns){
      Function f=fm.getFunctionAt(toAddr(fa)); if(f==null)continue;
      DecompileResults r=dec.decompileFunction(f,240,monitor);
      println("\n// ######### "+f.getName()+" @ "+f.getEntryPoint()+" #########");
      println(r!=null&&r.decompileCompleted()?r.getDecompiledFunction().getC():"// fail");
    }
    println("\nFINDOPCODE_DONE");
  }
}
