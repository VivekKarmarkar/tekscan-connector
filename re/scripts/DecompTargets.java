import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompTargets extends GhidraScript {
    public void run() throws Exception {
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        Set<Long> seen = new HashSet<>();
        List<Function> todo = new ArrayList<>();

        long[] curated = {0x446f68L,0x44705eL,0x447105L,0x455bb0L,0x4099b0L,0x4471a0L,0x40a9a7L,
            0x446500L,0x4466a0L,0x446f30L,0x4470c0L,0x4468b0L,0x446680L,0x446570L,0x446560L,
            0x446670L,0x446690L,0x446530L};
        for (long av: curated) {
            Function fn = fm.getFunctionContaining(toAddr(av));
            if (fn!=null) todo.add(fn);
        }
        // every function that touches an FTDI call (write/read/bitmode/openex/baud/datachars)
        long[] iat = {0x5cb048L,0x5cb044L,0x5cb06cL,0x5cb07cL,0x5cb04cL,0x5cb050L,0x5cb058L};
        ReferenceManager rm = currentProgram.getReferenceManager();
        for (long ia: iat)
            for (Reference r: rm.getReferencesTo(toAddr(ia))) {
                Function fn = fm.getFunctionContaining(r.getFromAddress());
                if (fn!=null) todo.add(fn);
            }

        println("DECOMP_BEGIN total_candidates=" + todo.size());
        for (Function fn: todo) {
            if (!seen.add(fn.getEntryPoint().getOffset())) continue;
            println("\n// ===================== " + fn.getName() + " @ " + fn.getEntryPoint() + " =====================");
            DecompileResults r = dec.decompileFunction(fn, 120, mon);
            if (r!=null && r.decompileCompleted()) println(r.getDecompiledFunction().getC());
            else println("// decompile failed");
        }
        println("\nDECOMP_DONE");
    }
}
