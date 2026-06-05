// FindAutomationMethods.java — enumerate the IDispatch automation API by finding
// all callers of the registration helper FUN_0045ca80(dispid,"Name",argc). Each
// caller IS that method's encoder; print its name + the registration line so we
// can locate a connect/select-channel command encoder (sibling of SetFrameRate
// FUN_0045e730).
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;

public class FindAutomationMethods extends GhidraScript {
  DecompInterface dec; FunctionManager fm;
  ghidra.util.task.ConsoleTaskMonitor mon = new ghidra.util.task.ConsoleTaskMonitor();

  public void run(){
    dec=new DecompInterface(); dec.openProgram(currentProgram);
    fm=currentProgram.getFunctionManager();
    long[] regHelpers = {0x45ca80L, 0x45c920L};  // both dispid-registration helpers
    Set<Long> callers=new TreeSet<>();
    for (long rh: regHelpers){
      Function target=fm.getFunctionAt(toAddr(rh));
      if (target==null){ println("// no reg helper @"+Long.toHexString(rh)); continue; }
      for (Reference r: getReferencesTo(toAddr(rh))){
        Function c=fm.getFunctionContaining(r.getFromAddress());
        if (c!=null) callers.add(c.getEntryPoint().getOffset());
      }
    }
    println("// ===== "+callers.size()+" automation-method encoders (callers of reg helper) =====");
    for (long ca: callers){
      Function f=fm.getFunctionAt(toAddr(ca));
      if (f==null) continue;
      DecompileResults r=dec.decompileFunction(f,200,mon);
      if (r==null||!r.decompileCompleted()) continue;
      String c=r.getDecompiledFunction().getC();
      // print the registration line(s) -> dispid + method name
      for (String line: c.split("\n")){
        if (line.contains("FUN_0045ca80(")||line.contains("FUN_0045c920(")){
          println(String.format("// %s @0x%06x :  %s", f.getName(), ca, line.trim()));
        }
      }
    }
    println("\nAUTOMETHODS_DONE");
  }
}
