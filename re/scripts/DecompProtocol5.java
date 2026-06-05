import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompProtocol5 extends GhidraScript {
  DecompInterface dec; FunctionManager fm; ConsoleTaskMonitor mon; Set<Long> seen=new HashSet<>();
  void dump(long a, String tag){
    Function fn=fm.getFunctionContaining(toAddr(a));
    if(fn==null){ println("// none @ "+Long.toHexString(a)); return; }
    if(!seen.add(fn.getEntryPoint().getOffset())) return;
    println("\n// ===== "+tag+"  "+fn.getName()+" @ "+fn.getEntryPoint()+" =====");
    DecompileResults r=dec.decompileFunction(fn,180,mon);
    println(r!=null&&r.decompileCompleted()? r.getDecompiledFunction().getC():"// fail");
  }
  public void run() throws Exception {
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); mon=new ConsoleTaskMonitor();
    dump(0x409480L,"getCmdObj");     // returns the command-encoder object
    dump(0x40cbd0L,"sendCommand");   // transport: built command -> WritePort
    dump(0x40c720L,"helper");
    // The command-encoder vtable: read .rdata around any vtable referencing 0x40c.. builders.
    // Also dump the select-channel builder chain entry the OnConnect used (slot 0xc target).
    println("\nDECOMP_DONE");
  }
}
