import os, py_compile
P = os.path.expanduser('~/cars_dashboard.py')
s = open(P, encoding='utf-8').read()
PAIRS = [
  (' .rDEFLECT{background:#08343a;color:#39d0d8}',
   ' .rDEFLECT{background:#08343a;color:#39d0d8}.rRESTORE{background:#241a3a;color:#c792ea}\n .opRESTORE{background:#241a3a;color:#c792ea}'),
  ("ALLOW:'rALLOW',REFUSE:'rREFUSE'};",
   "ALLOW:'rALLOW',REFUSE:'rREFUSE',RESTORE:'rRESTORE'};"),
  ('<option>REFUSE</option><option>ALLOW</option></select>',
   '<option>REFUSE</option><option>ALLOW</option><option>RESTORE</option></select>'),
  ('<option>READ</option><option>S7</option></select>',
   '<option>READ</option><option>S7</option><option>RESTORE</option></select>'),
  ("'defense','maintenance'].map(function(e){",
   "'defense','maintenance','remediation'].map(function(e){"),
  ('df=res[6],mt=res[7];',
   'df=res[6],mt=res[7],rem=res[8];'),
  ('   <div class="card"><h2>Active enforcement</h2><div id="blocks"></div></div>\n </div>\n</div>',
   '   <div class="card"><h2>Active enforcement</h2><div id="blocks"></div></div>\n   <div class="card"><h2>Process remediation &middot; agent .2.45</h2><div id="remed"><div class="none">agent offline \u2014 no process-state feed</div></div></div>\n </div>\n</div>'),
  ("+mid+'</span></div>';}).join('');\n });}",
   '+mid+\'</span></div>\';}).join(\'\');\n   // ---- Process-remediation feed (agent .2.45, read from local file, not the controller) ----\n   (function(){var el=document.getElementById(\'remed\');if(!el)return;\n     var s=rem&&rem.status;\n     if(!s){el.innerHTML=\'<div class="none">agent offline \u2014 no process-state feed</div>\';return;}\n     var fresh=(Date.now()/1000-(s.ts||0))<6;\n     var lvl=(s.level!=null)?(+s.level).toFixed(1):\'?\',lg=(s.last_good!=null)?(+s.last_good).toFixed(1):\'?\';\n     var restos=(rem.events||[]).filter(function(e){return e.event===\'RESTORED\';});\n     el.innerHTML=\'<div class="sub" style="margin-bottom:6px;line-height:1.9">\'\n       +\'<span class="tier \'+(fresh?\'OPERATIONAL\':\'FORBIDDEN\')+\'">agent \'+(fresh?\'online\':\'stale\')+\'</span> \'\n       +\'<span class="tier rALLOW">Tank.Level \'+lvl+\'</span> \'\n       +\'<span class="tier SENSITIVE">last-good \'+lg+\'</span> \'\n       +\'<span class="tier rRESTORE">restores \'+(s.restores||0)+\'</span></div>\'\n       +(restos.slice(-6).reverse().map(function(e){\n           return \'<div class="blk" style="background:#1c1330;color:#c792ea;border:1px solid #3a2a55">&#8635; restored last-good \'\n             +(e.last_good!=null?(+e.last_good).toFixed(1):\'?\')+\' &middot; saw tampered \'+(e.level!=null?(+e.level).toFixed(1):\'?\')+\'</div>\';}).join(\'\')\n         ||\'<div class="none">no tamper \u2014 process nominal, tracking last-good</div>\');});\n   ((rem&&rem.events)||[]).forEach(function(e){if(e.event!==\'RESTORED\')return;\n     var key=\'REM#\'+e.ts+\'#\'+e.restores;if(window._seen[key])return;window._seen[key]=1;\n     window._log.push({time:new Date((e.ts||0)*1000).toLocaleTimeString(),tier:\'OPERATIONAL\',\n       src:\'192.168.2.45\',srole:\'remediation\',dst:\'192.168.2.10\',drole:\'plc\',proto:\'S7\',op:\'RESTORE\',\n       resp:\'RESTORE\',mode:\'MAINT\',\n       action:\'RESTORED last-good \'+(e.last_good!=null?(+e.last_good).toFixed(1):\'?\')+\' (saw tampered \'+(e.level!=null?(+e.level).toFixed(1):\'?\')+\')\',\n       raw:\'REM \'+e.ts+\' restored last-good \'+e.last_good+\' saw \'+e.level});});\n   if(typeof renderLog===\'function\'&&document.getElementById(\'viewLog\')&&document.getElementById(\'viewLog\').style.display!==\'none\')renderLog();\n });}'),
  ('CARS = "http://10.10.10.1:8080"\nPORT = 8090',
   'CARS = "http://10.10.10.1:8080"\nPORT = 8090\nREM_STATUS = "/tmp/cars_remediation_status.json"   # written by cars_remediation.py (same host)\nREM_FEED = "/tmp/cars_remediation.jsonl"\n\n\ndef remediation_feed():\n    """Read the local remediation agent status + recent events (the agent is in the OT netns and cannot reach the\n    control plane, so the dashboard reads its files directly)."""\n    out = {"status": None, "events": []}\n    try:\n        with open(REM_STATUS) as f:\n            out["status"] = json.load(f)\n    except Exception:\n        pass\n    try:\n        with open(REM_FEED) as f:\n            lines = f.readlines()[-40:]\n        out["events"] = [json.loads(x) for x in lines if x.strip()]\n    except Exception:\n        pass\n    return json.dumps(out).encode()'),
  ('            if self.path == "/":\n                self._s(HTML.encode(), "text/html")\n            elif self.path.startswith("/api/"):',
   '            if self.path == "/":\n                self._s(HTML.encode(), "text/html")\n            elif self.path == "/api/remediation":\n                self._s(remediation_feed(), "application/json")\n            elif self.path.startswith("/api/"):'),
]
for old, new in PAIRS:
    if new in s: continue
    n = s.count(old)
    assert n == 1, 'anchor not unique: %r (%d)' % (old[:55], n)
    s = s.replace(old, new, 1)
open('/tmp/_dc.py','w',encoding='utf-8').write(s)
py_compile.compile('/tmp/_dc.py', doraise=True)
open(P,'w',encoding='utf-8').write(s)
print('dashboard patched OK ->', P)
