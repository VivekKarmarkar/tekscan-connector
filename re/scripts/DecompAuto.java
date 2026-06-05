// DecompAuto.java — decompile selected automation-method encoders to extract
// their exact wire command bytes (same band/complement pattern as SetFrameRate).
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;

public class DecompAuto extends GhidraScript {
  DecompInterface dec; FunctionManager fm;
  ghidra.util.task.ConsoleTaskMonitor mon = new ghidra.util.task.ConsoleTaskMonitor();
  // {addr, label}
  long[] addrs = {0x45cf60L, 0x45f270L, 0x45eb90L, 0x45d2d0L};
  String[] labels = {"CollectSingle(0x30)", "StartRecording(0x3d)", "SetReferenceVoltage(0x32)", "GetFWversion(0x44)"};
  public void run(){
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager();
    for (int i=0;i<addrs.length;i++){
      Function f=fm.getFunctionContaining(toAddr(addrs[i]));
      if (f==null){ println("// no fn @"+Long.toHexString(addrs[i])); continue; }
      println("\n// ######### "+labels[i]+"  "+f.getName()+" @ "+f.getEntryPoint()+" #########");
      DecompileResults r=dec.decompileFunction(f,240,mon);
      println(r!=null&&r.decompileCompleted()?r.getDecompiledFunction().getC():"// fail");
    }
    println("\nDECOMPAUTO_DONE");
  }
}
