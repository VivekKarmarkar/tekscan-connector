import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompProtocol6 extends GhidraScript {
  DecompInterface dec; FunctionManager fm; ConsoleTaskMonitor mon; Set<Long> seen=new HashSet<>();
  void dump(long a, String tag){
    Function fn=fm.getFunctionContaining(toAddr(a));
    if(fn==null){ println("// none @ "+Long.toHexString(a)); return; }
    if(!seen.add(fn.getEntryPoint().getOffset())) return;
    println("\n// ===== "+tag+"  "+fn.getName()+" @ "+fn.getEntryPoint()+" =====");
    DecompileResults r=dec.decompileFunction(fn,200,mon);
    println(r!=null&&r.decompileCompleted()? r.getDecompiledFunction().getC():"// fail");
  }
  public void run() throws Exception {
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager(); mon=new ConsoleTaskMonitor();
    dump(0x432ad0L,"sendAndAck");   // serialize command -> WritePort -> read ack
    dump(0x405ac0L,"lockCmdObj");   // what the command/protocol object is
    println("\nDECOMP_DONE");
  }
}
