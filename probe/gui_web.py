#!/usr/bin/env python3
"""
gui_web.py — SIMPLE live browser GUI for the Tekscan ELF handle. Stdlib only.
Big live force readout + scrolling strip chart + basic 2-point calibration.

Decoded protocol @ 1,000,000 baud:
  SetReferenceVoltage(0x32,0xFF) -> SetFrameRate(0x39,30,48,ea) ->
  StartRecording(0x3d) -> one byte per frame = 8-bit force (no-load 0, rises w/ force).

RUN:  replug the handle, then  .venv/bin/python probe/gui_web.py
      open  http://localhost:8777  in your browser.
It auto-connects and auto-recovers (incl. after a replug); no buttons needed.
"""
import sys, os, time, json, threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tekscan_connector.protocol import TekscanHandle  # noqa: E402
from pyftdi.usbtools import UsbTools  # noqa: E402

BAUD = 1_000_000
PORT = 8777
STALL = 2.0  # seconds with no data => auto-recover (invisible)

LOCK = threading.Lock()
STATE = {
    "raw": 0, "peak": 0, "fps": 0.0, "status": "starting…", "connected": False,
    "samples": deque(maxlen=400),     # (t, value)
    "cal": {"raw0": None, "raw1": None, "g1": 1000.0},
}
CTRL = {"reconnect": False, "running": True}


def reader():
    """Connect, run the start sequence, stream force, and self-heal silently."""
    while CTRL["running"]:
        h = None
        try:
            with LOCK:
                STATE["status"] = "connecting…"; STATE["connected"] = False; STATE["fps"] = 0.0
            UsbTools.flush_cache()          # so a replug is seen
            h = TekscanHandle()
            f = h.ftdi
            f.set_baudrate(BAUD); time.sleep(0.01)
            f.purge_buffers(); time.sleep(0.003)
            f.write_data(bytes([0x32, 0xFF])); time.sleep(0.1); f.read_data_bytes(16, attempt=2)
            f.write_data(bytes([0x39, 0x30, 0x48, 0xea])); time.sleep(0.15); f.read_data_bytes(16, attempt=2)
            f.write_data(bytes([0x3d]))
            with LOCK:
                STATE["status"] = "streaming"; STATE["connected"] = True
            CTRL["reconnect"] = False
            t0 = time.time(); count = 0; last_fps = t0; last_data = time.time()
            while CTRL["running"] and not CTRL["reconnect"]:
                d = f.read_data_bytes(256, attempt=2)
                now = time.time()
                if d:
                    last_data = now; count += len(d)
                    with LOCK:
                        for b in d:
                            STATE["samples"].append((round(now - t0, 3), b))
                        STATE["raw"] = d[-1]
                        STATE["peak"] = max(STATE["peak"], max(d))
                elif now - last_data > STALL:
                    with LOCK:
                        STATE["status"] = "reconnecting…"; STATE["connected"] = False; STATE["fps"] = 0.0
                    break
                if now - last_fps >= 1.0:
                    with LOCK:
                        STATE["fps"] = round(count / (now - last_fps), 1)
                    count = 0; last_fps = now
        except Exception:
            with LOCK:
                STATE["status"] = "waiting for handle…"; STATE["connected"] = False; STATE["fps"] = 0.0
            time.sleep(0.6)
        finally:
            if h:
                try: h.close()
                except Exception: pass
        time.sleep(0.2)


PAGE = """<!doctype html><html><head><meta charset=utf-8><title>Tekscan Live</title>
<style>
 body{background:#0d1117;color:#e6edf3;font-family:system-ui,sans-serif;margin:0;padding:18px}
 h1{font-size:18px;color:#7ee787;margin:0 0 10px}
 .big{font-size:96px;font-weight:800;line-height:1;letter-spacing:-2px}
 .unit{font-size:24px;color:#8b949e}
 .row{display:flex;gap:24px;align-items:flex-end;flex-wrap:wrap}
 .card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px;margin-bottom:14px}
 .bar{height:34px;background:#21262d;border-radius:8px;overflow:hidden;margin-top:8px}
 .fill{height:100%;width:0;background:linear-gradient(90deg,#2ea043,#d29922,#f85149);transition:width .07s}
 .status{font-size:15px;padding:6px 12px;border-radius:8px;background:#21262d;display:inline-block}
 .ok{color:#7ee787} .warn{color:#f0883e} .err{color:#ff7b72}
 button{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:9px 14px;font-size:14px;cursor:pointer}
 button:hover{background:#30363d}
 input{background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:7px;width:90px;font-size:14px}
 canvas{background:#0d1117;border:1px solid #30363d;border-radius:8px;width:100%;height:240px}
 .muted{color:#8b949e;font-size:13px}
 .grams{font-size:40px;font-weight:700;color:#79c0ff}
</style></head><body>
<h1>● TEKSCAN FLEXIFORCE ELF — LIVE (Linux, no Windows)</h1>
<div id=status class=status>connecting…</div>
<div class=row style="margin-top:14px">
 <div class=card style="min-width:280px">
   <div class=muted>RAW FORCE COUNT</div>
   <div><span class=big id=raw>0</span> <span class=unit>/ 255</span></div>
   <div class=bar><div class=fill id=fill></div></div>
   <div class=muted style="margin-top:8px">peak <b id=peak>0</b> · <span id=fps>0</span> frames/s</div>
 </div>
 <div class=card style="min-width:280px">
   <div class=muted>CALIBRATED FORCE</div>
   <div><span class=grams id=grams>—</span></div>
   <div class=muted id=calinfo style="margin-top:8px">set 2 points below (optional)</div>
 </div>
</div>
<div class=card>
  <div class=muted style="margin-bottom:6px">STRIP CHART (last ~40 s)</div>
  <canvas id=chart width=1100 height=240></canvas>
</div>
<div class=card>
  <b>Calibrate (optional):</b>
  <button onclick="cmd('mark0')">① Mark NO-LOAD (0 g)</button>
  weight: <input id=g type=number value=1000> g
  <button onclick="markload()">② Mark LOADED</button>
  <button onclick="cmd('reset_peak')">Reset peak</button>
  <button onclick="cmd('reconnect')">⟳ Reconnect</button>
</div>
<script>
let R0=null,R1=null,G1=1000;
function setStatus(s,cls){let e=document.getElementById('status');e.textContent=s;e.className='status '+(cls||'')}
async function cmd(a,extra){let q=extra?('&'+extra):'';await fetch('/cmd?action='+a+q);}
function markload(){G1=parseFloat(document.getElementById('g').value)||1000;cmd('markload','g='+G1);}
const cv=document.getElementById('chart'),cx=cv.getContext('2d');
function draw(samples){
  cx.clearRect(0,0,cv.width,cv.height);
  cx.strokeStyle='#30363d';cx.lineWidth=1;
  for(let y=0;y<=255;y+=51){let yy=cv.height-(y/255)*cv.height;cx.beginPath();cx.moveTo(0,yy);cx.lineTo(cv.width,yy);cx.stroke();}
  if(!samples.length)return;
  cx.strokeStyle='#2ea043';cx.lineWidth=2;cx.beginPath();
  let n=samples.length;
  for(let i=0;i<n;i++){let x=i/(n-1)*cv.width,y=cv.height-(samples[i][1]/255)*cv.height;i?cx.lineTo(x,y):cx.moveTo(x,y);}
  cx.stroke();
}
async function tick(){
  try{
    let r=await fetch('/data');let d=await r.json();
    document.getElementById('raw').textContent=d.raw;
    document.getElementById('peak').textContent=d.peak;
    document.getElementById('fps').textContent=d.fps;
    document.getElementById('fill').style.width=(d.raw/255*100)+'%';
    if(d.connected)setStatus('● streaming live','ok');
    else setStatus(d.status,'warn');
    R0=d.cal.raw0;R1=d.cal.raw1;G1=d.cal.g1;
    let ci=document.getElementById('calinfo');
    if(R0!==null&&R1!==null&&R1!==R0){
      let g=(d.raw-R0)*(G1)/(R1-R0);
      document.getElementById('grams').textContent=g.toFixed(1)+' g';
      ci.textContent='raw0='+R0+'  raw1='+R1+'  ('+G1+' g)';
    }else{
      document.getElementById('grams').textContent=(R0!==null?'set ②':'—');
      ci.textContent='raw0='+(R0===null?'—':R0)+'  raw1='+(R1===null?'—':R1);
    }
    draw(d.samples);
  }catch(e){setStatus('page lost server','err');}
}
setInterval(tick,80);tick();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif u.path == "/data":
            with LOCK:
                snap = {
                    "raw": STATE["raw"], "peak": STATE["peak"], "fps": STATE["fps"],
                    "status": STATE["status"], "connected": STATE["connected"],
                    "samples": list(STATE["samples"]), "cal": STATE["cal"],
                }
            self._send(200, json.dumps(snap).encode())
        elif u.path == "/cmd":
            q = parse_qs(u.query); action = q.get("action", [""])[0]
            with LOCK:
                if action == "reset_peak":
                    STATE["peak"] = 0
                elif action == "mark0":
                    STATE["cal"]["raw0"] = _avg_recent()
                elif action == "markload":
                    STATE["cal"]["g1"] = float(q.get("g", ["1000"])[0])
                    STATE["cal"]["raw1"] = _avg_recent()
                elif action == "reconnect":
                    CTRL["reconnect"] = True
            self._send(200, b'{"ok":true}')
        else:
            self._send(404, b'{"error":"not found"}')


def _avg_recent(n=15):
    vals = [v for _, v in list(STATE["samples"])[-n:]]
    return round(sum(vals) / len(vals)) if vals else 0


def main():
    threading.Thread(target=reader, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("=" * 60)
    print(f"  Tekscan live GUI running.  OPEN:  http://localhost:{PORT}")
    print("  (Ctrl-C to stop.)")
    print("=" * 60)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        CTRL["running"] = False
        print("\n  stopped.")


if __name__ == "__main__":
    main()
