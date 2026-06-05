// DecompAcqStrings.java
// Step-3 acquisition-trigger hunt for ElfMPort.exe.
//
// Goal: map the START-ACQUISITION UI/command strings to code addresses and the
// referencing (handler) functions. Primary hypothesis: setting a NON-ZERO frame
// rate starts the CommunicationThread poll, so "frame rate" strings are prime.
//
// What it does:
//   1. Walk every defined string, match against an acquisition vocabulary.
//   2. Print  string | address | category  for each match (deduped report list).
//   3. For a PRIORITY subset (frame-rate, record, single-frame, ref-voltage),
//      find getReferencesTo(stringAddr), resolve the containing function, and
//      decompile it (deduped). Each decompiled function is tagged with which
//      priority string drew us to it.
//
// Run (saved, pre-analyzed project, -process mode = fast):
//   JAVA_HOME="$P/re/jdk21" "$P/re/ghidra/support/analyzeHeadless" "$P/re/project" ElfMPort \
//     -process ElfMPort.exe -noanalysis -scriptPath "$P/re/scripts" \
//     -postScript DecompAcqStrings.java > "$P/re/logs/acq_strings.log" 2>&1

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class DecompAcqStrings extends GhidraScript {
  DecompInterface dec;
  FunctionManager fm;
  ReferenceManager rm;
  ConsoleTaskMonitor mon;
  Set<Long> dumped = new HashSet<>();

  // Substrings (lowercased compare) -> category, for the REPORT list.
  String[][] vocab = {
    {"set frame rate at",          "framerate"},
    {"failed to set frame rate",   "framerate"},
    {"setting frame rate",         "framerate"},
    {"setframerate",               "framerate"},
    {"frames",                     "framerate"},
    {"frameperiod",                "framerate"},
    {"startrecording",             "start"},
    {"stoprecording",              "stop"},
    {"processstoprecording",       "stop"},
    {"receiverecorddata",          "start"},
    {"recording stopped",          "stop"},
    {"buffer overflow",            "stop"},
    {"getcurrentframe",            "framerate"},
    {"getsingleframe",             "framerate"},
    {"single reading",             "framerate"},
    {"opget",                      "framerate"},
    {"reference voltage",          "framerate"},
    {"dac value",                  "framerate"},
    {"acquired requested",         "start"},
    {"triggered",                  "start"},
    {"communicationthread",        "start"},
    {"autoconnectionthread",       "connect"},
    {"holdrequests",               "start"},
    {"start: holdrequests",        "start"},
    {"::pause",                    "stop"},
    {"::resumeasync",              "start"},
    {"servicepauserequests",       "start"},
    {"onnewrtdata",                "feedback"},
    {"onnewdataavailable",         "feedback"},
    {"generatemovie",              "feedback"},
    {"onconnect",                  "connect"},
    {"no devices selected",        "connect"},
    {"reconnecting will stop",     "stop"},
    {"calibration",                "feedback"},
    {"sensitivity",                "feedback"},
    {"equilibrat",                 "feedback"},
  };

  // PRIORITY substrings: for these we chase xrefs + decompile the handler.
  String[] priority = {
    "set frame rate at",
    "failed to set frame rate",
    "setting frame rate",
    "startrecording",
    "stoprecording",
    "getsingleframe",
    "single reading",
    "reference voltage",
    "acquired requested",
    "start: holdrequests",
    "buffer overflow",
  };

  String catFor(String low) {
    for (String[] v : vocab) if (low.contains(v[0])) return v[1];
    return null;
  }
  boolean isPriority(String low) {
    for (String p : priority) if (low.contains(p)) return true;
    return false;
  }

  String decompile(Function fn) {
    DecompileResults r = dec.decompileFunction(fn, 240, mon);
    if (r != null && r.decompileCompleted()) return r.getDecompiledFunction().getC();
    return "// <decompile failed>";
  }

  public void run() throws Exception {
    dec = new DecompInterface();
    dec.setOptions(new DecompileOptions());
    dec.openProgram(currentProgram);
    fm = currentProgram.getFunctionManager();
    rm = currentProgram.getReferenceManager();
    mon = new ConsoleTaskMonitor();

    println("// ===== ElfMPort.exe acquisition-string map =====");
    println("ACQ_REPORT_BEGIN");

    // List of priority string addresses to chase after the report.
    List<Object[]> chase = new ArrayList<>(); // {Address addr, String text}

    DataIterator it = currentProgram.getListing().getDefinedData(true);
    while (it.hasNext()) {
      Data d = it.next();
      if (d == null || !d.hasStringValue()) continue;
      Object val = d.getValue();
      if (val == null) continue;
      String s = val.toString();
      if (s.length() < 3) continue;
      String low = s.toLowerCase();
      String cat = catFor(low);
      if (cat == null) continue;
      Address a = d.getAddress();
      // single-line, escape newlines
      String oneline = s.replace("\n", "\\n").replace("\r", "\\r");
      println("STR | " + a + " | " + cat + " | " + oneline);
      if (isPriority(low)) chase.add(new Object[]{a, oneline});
    }
    println("ACQ_REPORT_END");

    // Now chase xrefs for the priority strings and decompile handlers.
    println("\nACQ_XREF_BEGIN");
    for (Object[] entry : chase) {
      Address a = (Address) entry[0];
      String txt = (String) entry[1];
      println("\n// ---- xrefs to string @ " + a + "  \"" + txt + "\" ----");
      Reference[] refs = getReferencesTo(a);
      if (refs.length == 0) { println("//   (no direct references)"); continue; }
      for (Reference r : refs) {
        Address from = r.getFromAddress();
        Function fn = fm.getFunctionContaining(from);
        if (fn == null) { println("//   ref from " + from + " (no function)"); continue; }
        println("//   ref from " + from + " in " + fn.getName() + " @ " + fn.getEntryPoint());
      }
    }
    println("ACQ_XREF_END");

    // Decompile each unique referencing function, tagged with the strings that hit it.
    println("\nACQ_DECOMP_BEGIN");
    // Build function -> set of strings that reference it.
    Map<Long, Function> funcs = new LinkedHashMap<>();
    Map<Long, Set<String>> tags = new LinkedHashMap<>();
    for (Object[] entry : chase) {
      Address a = (Address) entry[0];
      String txt = (String) entry[1];
      for (Reference r : getReferencesTo(a)) {
        Function fn = fm.getFunctionContaining(r.getFromAddress());
        if (fn == null) continue;
        long off = fn.getEntryPoint().getOffset();
        funcs.putIfAbsent(off, fn);
        tags.computeIfAbsent(off, k -> new LinkedHashSet<>()).add(txt);
      }
    }
    for (Map.Entry<Long, Function> e : funcs.entrySet()) {
      Function fn = e.getValue();
      println("\n// ============================================================");
      println("// HANDLER " + fn.getName() + " @ " + fn.getEntryPoint());
      println("//   referenced via strings: " + tags.get(e.getKey()));
      println("// ============================================================");
      println(decompile(fn));
    }
    println("ACQ_DECOMP_END");
    println("DECOMP_DONE");
  }
}
