#!/usr/bin/env python3
# CARS — IT/OT Live Topology v5 (god-level live sync).  Run on Dell #1:  python3 ~/cars_dashboard.py
# Open http://localhost:8090 . Discovery-driven: nodes, links, PORT bindings, link health, guard drops,
# and brain decisions all pulled live from the controller (/cars/status|hosts|ports|links|guard|audit).
# Threaded server (no broken-pipe spam). Switches & hosts DISCOVERED; north (IT/DMZ/FW/Snort) modeled.
import http.server, socketserver, urllib.request, json

CARS = "http://10.10.10.1:8080"
PORT = 8090
REM_STATUS = "/tmp/cars_remediation_status.json"   # written by cars_remediation.py (same host)
REM_FEED = "/tmp/cars_remediation.jsonl"


def remediation_feed():
    """Read the local remediation agent status + recent events (the agent is in the OT netns and cannot reach the
    control plane, so the dashboard reads its files directly)."""
    out = {"status": None, "events": []}
    try:
        with open(REM_STATUS) as f:
            out["status"] = json.load(f)
    except Exception:
        pass
    try:
        with open(REM_FEED) as f:
            lines = f.readlines()[-40:]
        out["events"] = [json.loads(x) for x in lines if x.strip()]
    except Exception:
        pass
    return json.dumps(out).encode()

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>CARS Live Topology</title>
<style>
 *{box-sizing:border-box}
 body{margin:0;background:#0a0e14;color:#c9d1d9;font-family:system-ui,Arial,sans-serif;overflow:hidden}
 header{height:50px;padding:0 18px;border-bottom:1px solid #1c2330;display:flex;align-items:center;gap:12px;background:#0d1117}
 h1{font-size:16px;margin:0;color:#58a6ff}
 .dot{width:10px;height:10px;border-radius:50%;background:#3fb950;box-shadow:0 0 8px #3fb950}
 .dot.off{background:#f85149;box-shadow:0 0 8px #f85149}
 .sub{color:#6e7681;font-size:12px}
 .btn{background:#1c2330;border:1px solid #2b3444;color:#c9d1d9;border-radius:6px;padding:5px 11px;font-size:12px;cursor:pointer}
 .btn:hover{background:#252d3d}
 .main{display:flex;height:calc(100vh - 50px)}
 .stage{flex:1;position:relative;background:radial-gradient(circle at 50% 42%,#111826,#0a0e14 72%)}
 svg{width:100%;height:100%;display:block}
 .side{width:352px;border-left:1px solid #1c2330;background:#0d1117;overflow-y:auto;padding:13px}
 .card{background:#131a24;border:1px solid #1c2330;border-radius:9px;padding:12px;margin-bottom:11px}
 .card h2{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:#8b949e;margin:0 0 9px}
 .feed{max-height:196px;overflow-y:auto;font-size:12px}
 .row{display:flex;gap:7px;align-items:center;padding:4px 0;border-bottom:1px solid #171e29}
 .t{font-family:ui-monospace,Consolas,monospace;color:#6e7681;font-size:10px}
 .tier{padding:1px 6px;border-radius:5px;font-size:10px;font-weight:700;white-space:nowrap}
 .CRITICAL{background:#3d2b12;color:#e3b341}.FORBIDDEN{background:#45161c;color:#ff7b72}
 .OPERATIONAL{background:#123024;color:#7ee2a8}.SENSITIVE{background:#3d2b12;color:#e3b341}
 .rALLOW{background:#123024;color:#7ee2a8}.rTHROTTLE{background:#3a2a0d;color:#f0b429}
 .rBLOCK{background:#45161c;color:#ff7b72}.rISOLATE{background:#4a1030;color:#f778ba}.rREFUSE{background:#0d2847;color:#58a6ff}
 .rDEFLECT{background:#08343a;color:#39d0d8}.rRESTORE{background:#241a3a;color:#c792ea}
 .opRESTORE{background:#241a3a;color:#c792ea}
 .opWRITE{background:#3a1d0d;color:#ffb86b}.opREAD{background:#0d2233;color:#7fd1e0}.opS7{background:#2a1533;color:#c792ea}
 .opCONTROL{background:#451616;color:#ff9b8b}.opDIAG{background:#4a1030;color:#f778ba}.opPROGRAM{background:#241a3a;color:#c792ea}.opILLEGAL{background:#3d2b12;color:#e3b341}
 .blk{background:#37151a;color:#ff7b72;padding:5px 8px;border-radius:6px;margin:4px 0;font-size:11.5px;font-family:ui-monospace,Consolas,monospace}
 .none{color:#59626e;font-size:12px}
 .inv{font-size:11.5px;width:100%}.inv td{padding:3px 5px;border-bottom:1px solid #171e29}
 .up{color:#3fb950}.down{color:#f85149;font-weight:700}
 .node{cursor:grab}.node:active{cursor:grabbing}
 .nlabel{font-size:10px;fill:#c9d1d9;font-weight:600;text-anchor:middle;pointer-events:none}
 .nglyph{font-size:8.5px;font-weight:800;text-anchor:middle;pointer-events:none}
 .plabel{font-size:8px;fill:#7d8795;text-anchor:middle;pointer-events:none;font-family:ui-monospace,monospace}
 .lk{stroke:#2b3444;stroke-width:1.6}
 .lk.ctl{stroke:#2b4a6b;stroke-dasharray:2 4}.lk.mirror{stroke:#5a3f7a;stroke-dasharray:5 4}
 .lk.model{stroke:#33404f;stroke-dasharray:3 4}
 .lk.fabric{stroke:#3fb950;stroke-width:2.4}
 .lk.host{stroke:#37506b;stroke-dasharray:4 5;animation:dash 1s linear infinite}
 .lk.broken{stroke:#f85149!important;stroke-width:2.6;stroke-dasharray:3 3;animation:none;filter:drop-shadow(0 0 3px #f85149)}
 @keyframes dash{to{stroke-dashoffset:-9}}
 .blkline{stroke:#f85149;stroke-width:2.4;stroke-dasharray:6 4;animation:dash .6s linear infinite;filter:drop-shadow(0 0 4px #f85149)}
 .attack>circle{animation:thr 1s ease-in-out infinite}
 @keyframes thr{0%,100%{stroke-width:2}50%{stroke-width:5.5}}
 #tip{position:absolute;pointer-events:none;background:#0d1117;border:1px solid #2b3444;border-radius:6px;padding:6px 9px;font-size:11.5px;display:none;z-index:9;box-shadow:0 4px 14px #000a}
 .tab{padding:6px 12px;border-radius:6px;font-size:12px;color:#8b949e;cursor:pointer;border:1px solid transparent}
 .tab:hover{background:#161d29}.tab.active{color:#58a6ff;background:#131c2b;border-color:#22314a}
 .viewlog{height:calc(100vh - 50px);display:flex;flex-direction:column}
 .logbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px;border-bottom:1px solid #1c2330;background:#0d1117}
 .logbar select,.logbar input{background:#131a24;border:1px solid #2b3444;color:#c9d1d9;border-radius:6px;padding:4px 8px;font-size:12px}
 .logbar input{min-width:150px}
 .counts{display:flex;gap:6px;flex-wrap:wrap;padding:8px 14px;border-bottom:1px solid #1c2330;min-height:20px}
 .logwrap{flex:1;overflow:auto;padding:0 6px}
 .logtable{width:100%;border-collapse:collapse;font-size:12px}
 .logtable th{position:sticky;top:0;background:#0d1117;color:#8b949e;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:8px;border-bottom:1px solid #1c2330;z-index:2}
 .logtable td{padding:6px 8px;border-bottom:1px solid #141b26;vertical-align:top}
 .logtable tr:hover{background:#0f1622}
 .mono{font-family:ui-monospace,Consolas,monospace}
 .mode{font-size:9px;padding:1px 5px;border-radius:4px}
 .mENFORCED{background:#122a1e;color:#7ee2a8}.mMONITOR{background:#2a2410;color:#e3b341}.mMAINT{background:#241a3a;color:#c792ea}.mREMEDIATE{background:#08343a;color:#39d0d8}
</style></head><body>
<header><span class="dot" id="live"></span><h1>CARS</h1>
 <span class="tab active" id="tabTopo">Topology</span><span class="tab" id="tabLog">Decision Log</span>
 <span class="sub" id="upd"></span><span style="flex:1"></span>
 <button class="btn" id="reflow">Re-flow</button>
 <button class="btn" id="defbtn" title="arm/disarm reactive enforcement">DEFENSE</button>
 <button class="btn" id="maintbtn" title="open a 10-min maintenance window (dangerous eng ops permitted-with-monitoring)">MAINT</button>
 <span class="sub">discovered &middot; drag &middot; click to inspect</span><span class="sub" style="margin-left:10px">criticality <span style="color:#f85149">&#9679;</span>CRIT <span style="color:#d9902b">&#9679;</span>HIGH <span style="color:#e3b341">&#9679;</span>MED <span style="color:#6e7681">&#9679;</span>LOW</span></header>
<div class="main" id="viewTopo">
 <div class="stage"><svg id="net" viewBox="0 0 680 600" preserveAspectRatio="xMidYMid meet">
   <g id="lg"></g><g id="bgl"></g><g id="pl"></g><g id="ng"></g></svg><div id="tip"></div></div>
 <div class="side">
   <div class="card"><h2>Controller &middot; fabric</h2><div id="sw"></div></div>
   <div class="card"><h2>Source-guard &middot; spoof drops (live)</h2><div id="guard"></div></div>
   <div class="card"><h2 id="inspH">Node inspector</h2><div id="insp" class="none">Click a node.</div></div>
   <div class="card"><h2>Discovered hosts</h2><table class="inv" id="inv"></table></div>
   <div class="card"><h2>Live detections &amp; decisions</h2><div class="sub" style="margin-bottom:5px;font-size:9px">response ladder: <span class="tier rALLOW">ALLOW</span> <span class="tier rTHROTTLE">THROTTLE</span> <span class="tier rDEFLECT">DEFLECT</span> <span class="tier rBLOCK">BLOCK</span> <span class="tier rISOLATE">ISOLATE</span> <span class="tier rREFUSE">REFUSE</span></div><div id="feed" class="feed"></div></div>
   <div class="card"><h2>Active enforcement</h2><div id="blocks"></div></div>
   <div class="card"><h2>Process remediation &middot; agent .2.45</h2><div id="remed"><div class="none">agent offline — no process-state feed</div></div></div>
 </div>
</div>
<div id="viewLog" class="viewlog" style="display:none">
 <div class="logbar">
   <b style="color:#58a6ff;font-size:13px">Decision Log</b>
   <select id="fTier"><option value="">Tier: all</option><option>CRITICAL</option><option>FORBIDDEN</option><option>SENSITIVE</option><option>OPERATIONAL</option></select>
   <select id="fResp"><option value="">Response: all</option><option>BLOCK</option><option>ISOLATE</option><option>THROTTLE</option><option>DEFLECT</option><option>REFUSE</option><option>ALLOW</option><option>RESTORE</option></select>
   <select id="fOp"><option value="">Op: all</option><option>CONTROL</option><option>DIAG</option><option>PROGRAM</option><option>ILLEGAL</option><option>WRITE</option><option>READ</option><option>S7</option><option>RESTORE</option></select>
   <select id="fMode"><option value="">Mode: all</option><option value="ENFORCED">enforced</option><option value="MONITOR">monitor (disarmed)</option><option value="MAINT">maint-authorised</option><option value="REMEDIATE">remediation (auto-heal)</option></select>
   <input id="fText" placeholder="search ip / host / text">
   <label class="sub" style="display:flex;align-items:center;gap:4px"><input type="checkbox" id="fNew" checked style="min-width:auto"> newest first</label>
   <span style="flex:1"></span><span class="sub" id="logCount"></span>
   <button class="btn" id="expCsv">CSV</button><button class="btn" id="expJson">JSON</button><button class="btn" id="logClear">Clear</button>
 </div>
 <div class="counts" id="counts"></div>
 <div class="logwrap"><table class="logtable" id="logtbl"></table></div>
</div>

<script>
var NS='http://www.w3.org/2000/svg';
var TYPE={
 atk:{c:'#f85149',g:'!',r:18}, fw:{c:'#d9902b',g:'FW',r:16}, host:{c:'#8b949e',g:'H',r:15},
 sw:{c:'#58a6ff',g:'SW',r:23}, plc:{c:'#3fb950',g:'PLC',r:18}, hmi:{c:'#58c8e0',g:'HMI',r:18},
 sup:{c:'#7ee2a8',g:'SUP',r:16}, ids:{c:'#a371f7',g:'IDS',r:16}, ctrl:{c:'#f0b72f',g:'CTL',r:20}};
var ROLE={'192.168.2.10':'plc','192.168.2.9':'hmi','192.168.2.30':'historian','192.168.2.1':'gateway','192.168.2.55':'ews','192.168.2.45':'remediation','192.168.2.66':'unknown','192.168.2.20':'plc','192.168.2.31':'scada','192.168.2.77':'unknown','192.168.3.10':'plc','192.168.3.9':'hmi','192.168.3.66':'historian','192.168.3.1':'cell2gw'};
var TYPEOF={plc:'plc',hmi:'hmi',historian:'sup',gateway:'fw',cell2gw:'fw',ews:'sup',remediation:'sup',scada:'sup',supervisory:'sup',unknown:'atk'};
var CRIT={'192.168.2.10':'CRITICAL','192.168.3.10':'HIGH','192.168.2.9':'HIGH','192.168.3.9':'MEDIUM','192.168.2.30':'MEDIUM','192.168.2.20':'LOW'};
var CRITC={CRITICAL:'#f85149',HIGH:'#d9902b',MEDIUM:'#e3b341',LOW:'#3a3f4a'};
function acl(ip){return (window._crit&&window._crit[ip])||CRIT[ip]||null;}
function critColor(ip){var a=acl(ip);return a?CRITC[a]:null;}
function hlabel(role,dpid,ip){
 if(role==='plc')return dpid==1?'PLC1':dpid==2?'PLC2':'PLC';
 if(role==='hmi')return dpid==1?'HMI1':dpid==2?'HMI2':'HMI';
 if(role==='historian')return 'Historian'; if(role==='ews')return 'EWS'; if(role==='scada')return 'SCADA'; if(role==='remediation')return 'CARS-Remediation';
 if(role==='supervisory')return ip||'Supervisory';
 if(role==='gateway')return 'OT-FW'; if(role==='cell2gw')return 'Cell-2 GW'; if(role==='unknown')return ip||'host'; return ip;}
var ANCH=[
 {id:'atk', lbl:'IT Attacker', t:'atk', model:1, ip:'10.0.40.66', x:110,y:60},
 {id:'efw', lbl:'Enterprise FW', t:'fw', model:1, x:110,y:135},
 {id:'dmz', lbl:'DMZ / Jump', t:'host', model:1, ip:'172.16.35.10', x:110,y:210},
 {id:'otfw',lbl:'OT FW (NAT)', t:'fw', model:1, ip:'192.168.2.1', x:150,y:285},
 {id:'snort',lbl:'Snort IDS', t:'ids', model:1, x:480,y:205},
 {id:'ctrl',lbl:'CARS Controller', t:'ctrl', ip:'10.10.10.1', x:350,y:80},
 {id:'sw3', lbl:'ovsgw', t:'sw', dpid:3, x:320,y:300},
 {id:'sw1', lbl:'ovs1', t:'sw', dpid:1, x:220,y:420},
 {id:'sw2', lbl:'ovs2', t:'sw', dpid:2, x:460,y:420},
 {id:'nat2',lbl:'Cell-2 NAT · PLC2 .3.10', t:'fw', model:1, ip:'192.168.3.10', x:560,y:330}];
var SLINK=[['atk','efw','model'],['efw','dmz','model'],['dmz','otfw','model'],['otfw','sw3','model'],
           ['snort','sw3','mirror'],['ctrl','sw3','ctl'],['ctrl','sw1','ctl'],['ctrl','sw2','ctl'],
           ['sw3','nat2','model'],['nat2','sw2','model']];
var SWID={1:'sw1',2:'sw2',3:'sw3'};
var W=680,H=600,nodes={},drag=null,moved=0,LINKS=[];
var lg=document.getElementById('lg'),bgl=document.getElementById('bgl'),pl=document.getElementById('pl'),ng=document.getElementById('ng'),svg=document.getElementById('net');
function mkNode(n){var ty=TYPE[n.t];
 var g=document.createElementNS(NS,'g');g.setAttribute('class','node');
 var cr=document.createElementNS(NS,'circle');cr.setAttribute('r',ty.r+4);cr.setAttribute('fill','none');cr.setAttribute('stroke-width','3');cr.setAttribute('stroke',critColor(n.ip)||'none');
 var c=document.createElementNS(NS,'circle');c.setAttribute('r',ty.r);
 c.setAttribute('fill','#131a24');c.setAttribute('stroke',ty.c);c.setAttribute('stroke-width','2');
 if(n.model)c.setAttribute('stroke-dasharray','3 3');
 var gl=document.createElementNS(NS,'text');gl.setAttribute('class','nglyph');gl.setAttribute('y','3');gl.setAttribute('fill',ty.c);gl.textContent=ty.g;
 var tx=document.createElementNS(NS,'text');tx.setAttribute('class','nlabel');tx.setAttribute('y',ty.r+12);tx.textContent=n.lbl;
 g.appendChild(cr);g.appendChild(c);g.appendChild(gl);g.appendChild(tx);ng.appendChild(g);
 n.g=g;n.c=c;n.cr=cr;n.tx=tx;n.vx=0;n.vy=0;bindDrag(n);return n;}
ANCH.forEach(function(a){nodes[a.id]=mkNode(a);});
function bindDrag(n){
 n.g.addEventListener('mousedown',function(ev){drag=n;moved=0;n.fx=n.x;n.fy=n.y;ev.preventDefault();});
 n.g.addEventListener('mousemove',function(ev){showTip(n,ev);});
 n.g.addEventListener('mouseleave',function(){document.getElementById('tip').style.display='none';});}
function svgpt(ev){var r=svg.getBoundingClientRect();return {x:(ev.clientX-r.left)/r.width*W,y:(ev.clientY-r.top)/r.height*H};}
document.addEventListener('mousemove',function(ev){if(!drag)return;var p=svgpt(ev);drag.fx=p.x;drag.fy=p.y;drag.x=p.x;drag.y=p.y;moved++;});
document.addEventListener('mouseup',function(){if(drag){if(moved<3){inspect(drag);drag.fx=null;drag.fy=null;}drag=null;}});
document.getElementById('reflow').onclick=function(){for(var k in nodes){nodes[k].fx=null;nodes[k].fy=null;nodes[k].vx=(Math.random()-.5)*8;nodes[k].vy=(Math.random()-.5)*8;}};
function exportSnapshot(){
 var out={generated:new Date().toISOString(),controller:(window._lastFeeds&&window._lastFeeds.status)||{},nodes:[],links:[]};
 for(var k in nodes){var n=nodes[k];out.nodes.push({id:n.id||k,label:n.lbl,type:n.t,role:n.role||null,ip:n.ip||null,mac:n.mac||null,dpid:(n.dpid!=null?n.dpid:null),port:(n.port!=null?n.port:null),last_seen_s:(n.age!=null?n.age:null),source:(n.model?'model':'discovered'),x:Math.round(n.x),y:Math.round(n.y)});}
 LINKS.forEach(function(l){out.links.push({a:l.a,b:l.b,kind:l.k,aport:(l.aport!=null?l.aport:null),bport:(l.bport!=null?l.bport:null)});});
 out.feeds=window._lastFeeds||{};
 var blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
 var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='cars_snapshot_'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';
 document.body.appendChild(a);a.click();document.body.removeChild(a);setTimeout(function(){URL.revokeObjectURL(a.href);},1500);}
(function(){var rb=document.getElementById('reflow');if(rb&&!document.getElementById('expbtn')){var eb=document.createElement('button');eb.id='expbtn';eb.textContent='Export JSON';try{eb.className=rb.className;}catch(e){}eb.style.marginLeft='6px';eb.onclick=exportSnapshot;rb.parentNode.insertBefore(eb,rb.nextSibling);}})();
function computeHosts(list){
 list=(list||[]).filter(function(h){return h.ip;});
 var pm={};list.forEach(function(h){var k=h.dpid+':'+h.port;(pm[k]=pm[k]||{})[h.mac]=1;});
 var bm={};list.forEach(function(h){(bm[h.mac]=bm[h.mac]||[]).push(h);});
 var out=[];
 Object.keys(bm).forEach(function(mac){var s=bm[mac];
   s.sort(function(a,b){return Object.keys(pm[a.dpid+':'+a.port]).length-Object.keys(pm[b.dpid+':'+b.port]).length;});
   var h=s[0];var role=ROLE[h.ip]||'unknown';
   out.push({id:'h_'+mac,mac:mac,ip:h.ip,dpid:h.dpid,port:h.port,age:h.age,role:role,
             t:TYPEOF[role]||'host',lbl:hlabel(role,h.dpid,h.ip)});});
 return out;}
function reconcile(hostNodes){
 var want={};hostNodes.forEach(function(h){want[h.id]=1;});
 for(var k in nodes){if(k.indexOf('h_')===0&&!want[k]){ng.removeChild(nodes[k].g);delete nodes[k];}}
 hostNodes.forEach(function(h){var ex=nodes[h.id];
   if(!ex){var sw=nodes[SWID[h.dpid]]||{x:W/2,y:H/2};h.x=sw.x+(Math.random()-.5)*44;h.y=sw.y+46+Math.random()*30;nodes[h.id]=mkNode(h);}
   else{ex.age=h.age;ex.port=h.port;ex.dpid=h.dpid;ex.role=h.role;ex.ip=h.ip;}});}
function rebuildLinks(fabric,hostNodes){
 LINKS=[];
 SLINK.forEach(function(l){if(nodes[l[0]]&&nodes[l[1]])LINKS.push({a:l[0],b:l[1],k:l[2]});});
 (fabric||[]).forEach(function(f){var A=SWID[f.src_dpid],B=SWID[f.dst_dpid];
   if(A&&B&&nodes[A]&&nodes[B]&&f.src_dpid<f.dst_dpid)
     LINKS.push({a:A,b:B,k:'fabric',aport:f.src_port,ad:f.src_dpid,bport:f.dst_port,bd:f.dst_dpid});});
 hostNodes.forEach(function(h){var sw=SWID[h.dpid];if(sw&&nodes[sw])LINKS.push({a:h.id,b:sw,k:'host',bport:h.port,bd:h.dpid});});
 lg.innerHTML='';pl.innerHTML='';
 LINKS.forEach(function(l){var e=document.createElementNS(NS,'line');e.setAttribute('class','lk '+l.k);lg.appendChild(e);l.el=e;
   var hit=document.createElementNS(NS,'line');hit.setAttribute('stroke','transparent');hit.setAttribute('stroke-width','14');hit.style.cursor='help';lg.appendChild(hit);l.hit=hit;
   hit.addEventListener('mousemove',(function(ll){return function(ev){showLinkTip(ll,ev);};})(l));
   hit.addEventListener('mouseleave',function(){document.getElementById('tip').style.display='none';});
   if(l.aport!=null){var t=document.createElementNS(NS,'text');t.setAttribute('class','plabel');t.textContent='p'+l.aport;pl.appendChild(t);l.at=t;}
   if(l.bport!=null){var u=document.createElementNS(NS,'text');u.setAttribute('class','plabel');u.textContent='p'+l.bport;pl.appendChild(u);l.bt=u;}});}
function tick(){
 var arr=[];for(var k in nodes)arr.push(nodes[k]);
 for(var i=0;i<arr.length;i++){var a=arr[i];for(var j=i+1;j<arr.length;j++){var b=arr[j];
   var dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1,d=Math.sqrt(d2);var f=2600/d2;var ux=dx/d,uy=dy/d;
   a.vx+=ux*f;a.vy+=uy*f;b.vx-=ux*f;b.vy-=uy*f;}}
 LINKS.forEach(function(l){var a=nodes[l.a],b=nodes[l.b];if(!a||!b)return;var dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1;
   var L=l.k==='host'?58:100;var f=(d-L)*0.014;var ux=dx/d,uy=dy/d;a.vx+=ux*f;a.vy+=uy*f;b.vx-=ux*f;b.vy-=uy*f;});
 arr.forEach(function(n){n.vx+=(W/2-n.x)*0.0015;n.vy+=(H/2-n.y)*0.0015;
   if(n.fx!=null){n.x=n.fx;n.y=n.fy;n.vx=0;n.vy=0;}
   else{n.vx*=0.85;n.vy*=0.85;n.x+=n.vx;n.y+=n.vy;n.x=Math.max(26,Math.min(W-26,n.x));n.y=Math.max(26,Math.min(H-30,n.y));}
   n.g.setAttribute('transform','translate('+n.x.toFixed(1)+','+n.y.toFixed(1)+')');});
 LINKS.forEach(function(l){var a=nodes[l.a],b=nodes[l.b];if(!a||!b||!l.el)return;
   l.el.setAttribute('x1',a.x);l.el.setAttribute('y1',a.y);l.el.setAttribute('x2',b.x);l.el.setAttribute('y2',b.y);
   if(l.hit){l.hit.setAttribute('x1',a.x);l.hit.setAttribute('y1',a.y);l.hit.setAttribute('x2',b.x);l.hit.setAttribute('y2',b.y);}
   var dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1;
   if(l.at){l.at.setAttribute('x',a.x+dx/d*26);l.at.setAttribute('y',a.y+dy/d*26-2);}
   if(l.bt){l.bt.setAttribute('x',b.x-dx/d*26);l.bt.setAttribute('y',b.y-dy/d*26-2);}});
 var kids=bgl.childNodes;for(var q=0;q<kids.length;q++){var ov=kids[q];var a=nodes[ov.dataset.s],b=nodes[ov.dataset.d];
   if(a&&b){ov.setAttribute('x1',a.x);ov.setAttribute('y1',a.y);ov.setAttribute('x2',b.x);ov.setAttribute('y2',b.y);}}
 requestAnimationFrame(tick);}
requestAnimationFrame(tick);
function showTip(n,ev){var t=document.getElementById('tip');
 t.innerHTML='<b>'+n.lbl+'</b><br><span class=sub>'+(n.role||n.t)+(n.ip?' &middot; '+n.ip:'')+(n.dpid?' &middot; dpid '+n.dpid+(n.port!=null?' p'+n.port:''):'')+'</span>';
 t.style.display='block';t.style.left=(ev.clientX-svg.getBoundingClientRect().left+14)+'px';t.style.top=(ev.clientY-svg.getBoundingClientRect().top+10)+'px';}
function inspect(n){document.getElementById('inspH').textContent='Node · '+n.lbl;
 function r(k,v){return v!=null&&v!==''?'<tr><td class=sub style="padding:3px 0">'+k+'</td><td style="padding:3px 0">'+v+'</td></tr>':'';}
 var dn=n.mac&&window._down&&window._down['h_'+n.mac];
 var h='<table style="font-size:12px;width:100%">'+r('Type',n.t)+r('Role',n.role)+r('IP',n.ip?'<span class=t>'+n.ip+'</span>':'')
  +r('MAC',n.mac?'<span class=t>'+n.mac+'</span>':'')+r('Location',n.dpid?('dpid '+n.dpid+(n.port!=null?' · port '+n.port:'')):(n.model?'modeled (not discovered)':''))
  +r('Last seen (ctrl)',n.age!=null?n.age+'s ago':'')+r('Link',n.dpid?(dn?'<span class=down>DOWN</span>':'<span class=up>up</span>'):'')
  +r('Source',n.model?'model':'discovered');
 document.getElementById('insp').className='';document.getElementById('insp').innerHTML=h+'</table>';}
function linkDesc(l){var a=nodes[l.a],b=nodes[l.b];var an=a?a.lbl:l.a,bn=b?b.lbl:l.b;
 if(l.k==='fabric')return an+' p'+l.aport+' &harr; '+bn+' p'+l.bport+' &middot; fabric';
 if(l.k==='host')return an+' &harr; '+bn+' p'+l.bport+' &middot; access port';
 if(l.k==='ctl')return an+' &harr; '+bn+' &middot; control plane';
 if(l.k==='mirror')return an+' &harr; '+bn+' &middot; IDS mirror';
 return an+' &harr; '+bn+' &middot; modeled';}
function showLinkTip(l,ev){var t=document.getElementById('tip');t.innerHTML='<b>link</b><br><span class=sub>'+linkDesc(l)+'</span>';
 t.style.display='block';t.style.left=(ev.clientX-svg.getBoundingClientRect().left+14)+'px';t.style.top=(ev.clientY-svg.getBoundingClientRect().top+10)+'px';}
function apiPost(ep,body){return fetch('/api/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})}).then(function(r){return r.json();}).catch(function(){return {};});}
document.getElementById('defbtn').onclick=function(){apiPost('defense',{on:!window._armed}).then(poll);};
document.getElementById('maintbtn').onclick=function(){apiPost('maintenance',{minutes:window._maint?0:10}).then(poll);};
window._log=[]; window._seen={};
var RK2={BLOCK:'rBLOCK',THROTTLE:'rTHROTTLE',DEFLECT:'rDEFLECT',ISOLATE:'rISOLATE',ALLOW:'rALLOW',REFUSE:'rREFUSE',RESTORE:'rRESTORE'};
function parseAudit(L){
 var m=L.match(/^(\S+)\s+(\w+)\s+([\d.]+)\((\w+)\)\s+->\s+([\d.]+)\((\w+)\)\s+(\w+)\s+(?:([A-Z0-9]+)\s+)?=>\s+(.+)$/);
 if(!m)return null;
 var action=m[9],mode='ENFORCED',resp;
 if(/^DEFENSE DISARMED/.test(action)){mode='MONITOR';resp=(action.match(/would (\w+)/)||[])[1]||'';}
 else if(/^MAINTENANCE-AUTHORISED/.test(action)){mode='MAINT';resp='ALLOW';}
 else{resp=(action.match(/^(\w+)/)||[])[1]||'';if(resp==='REFUSED')resp='REFUSE';}
 return {time:m[1],tier:m[2],src:m[3],srole:m[4],dst:m[5],drole:m[6],proto:m[7],op:m[8]||'',resp:resp,mode:mode,action:action,raw:L};}
function accumulate(lines){(lines||[]).forEach(function(L){if(!window._seen[L]){window._seen[L]=1;var p=parseAudit(L);if(p)window._log.push(p);}});
 if(window._log.length>3000)window._log=window._log.slice(-3000);}
function filteredLog(){
 var ft=document.getElementById('fTier').value,fr=document.getElementById('fResp').value,fo=document.getElementById('fOp').value,fm=document.getElementById('fMode').value,fx=(document.getElementById('fText').value||'').toLowerCase();
 var r=window._log.filter(function(d){return (!ft||d.tier===ft)&&(!fr||d.resp===fr)&&(!fo||d.op===fo)&&(!fm||d.mode===fm)&&(!fx||d.raw.toLowerCase().indexOf(fx)>=0);});
 if(document.getElementById('fNew').checked)r=r.slice().reverse();
 return r;}
function renderLog(){
 var rows=filteredLog();
 document.getElementById('logCount').textContent=rows.length+' / '+window._log.length+' decisions';
 var cc={};window._log.forEach(function(d){cc[d.resp]=(cc[d.resp]||0)+1;});
 document.getElementById('counts').innerHTML=Object.keys(cc).sort(function(a,b){return cc[b]-cc[a];}).map(function(k){return '<span class="tier '+(RK2[k]||'')+'">'+(k||'?')+' '+cc[k]+'</span>';}).join('')||'<span class=sub>no decisions yet</span>';
 var h='<tr><th>time</th><th>source</th><th></th><th>dest</th><th>proto</th><th>op</th><th>tier</th><th>response</th><th>mode</th></tr>';
 h+=rows.slice(0,600).map(function(d){return '<tr><td class="mono t">'+d.time+'</td>'
   +'<td class="mono">'+d.src+' <span class=sub>('+d.srole+')</span></td><td class=sub>&rarr;</td>'
   +'<td class="mono">'+d.dst+' <span class=sub>('+d.drole+')</span></td><td>'+d.proto+'</td>'
   +'<td>'+(d.op?'<span class="tier op'+d.op+'">'+d.op+'</span>':'')+'</td>'
   +'<td><span class="tier '+d.tier+'">'+d.tier+'</span></td>'
   +'<td>'+(d.resp?'<span class="tier '+(RK2[d.resp]||'')+'" title="'+d.action.replace(/"/g,'')+'">'+d.resp+'</span>':'')+'</td>'
   +'<td><span class="mode m'+d.mode+'">'+d.mode+'</span></td></tr>';}).join('');
 document.getElementById('logtbl').innerHTML=h;}
function dl(name,text,type){var b=new Blob([text],{type:type});var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;document.body.appendChild(a);a.click();document.body.removeChild(a);setTimeout(function(){URL.revokeObjectURL(a.href);},1500);}
function csvEsc(v){v=String(v==null?'':v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
(function wireLog(){
 ['fTier','fResp','fOp','fMode','fNew'].forEach(function(id){document.getElementById(id).addEventListener('change',renderLog);});
 document.getElementById('fText').addEventListener('input',renderLog);
 document.getElementById('logClear').onclick=function(){window._log=[];window._seen={};renderLog();};
 document.getElementById('expJson').onclick=function(){dl('cars_decisions_'+Date.now()+'.json',JSON.stringify(filteredLog(),null,2),'application/json');};
 document.getElementById('expCsv').onclick=function(){var rows=filteredLog(),cols=['time','src','srole','dst','drole','proto','op','tier','resp','mode','action'];
   var csv=cols.join(',')+'\n'+rows.map(function(d){return cols.map(function(c){return csvEsc(d[c]);}).join(',');}).join('\n');dl('cars_decisions_'+Date.now()+'.csv',csv,'text/csv');};
 function tab(t){var lg=t==='log';document.getElementById('viewTopo').style.display=lg?'none':'flex';document.getElementById('viewLog').style.display=lg?'flex':'none';
   document.getElementById('tabTopo').className='tab'+(lg?'':' active');document.getElementById('tabLog').className='tab'+(lg?' active':'');if(lg)renderLog();}
 document.getElementById('tabTopo').onclick=function(){tab('topo');};document.getElementById('tabLog').onclick=function(){tab('log');};
})();
function logPoll(){fetch('/api/audit').then(function(r){return r.json();}).then(function(a){accumulate(a.audit);if(document.getElementById('viewLog').style.display!=='none')renderLog();}).catch(function(){});}
setInterval(logPoll,1500);logPoll();

function poll(){
 Promise.all(['status','hosts','ports','links','guard','audit','defense','maintenance','remediation','criticality'].map(function(e){
   return fetch('/api/'+e).then(function(r){return r.json();}).catch(function(){return {error:1};});}))
 .then(function(res){
   var st=res[0],ho=res[1],po=res[2],li=res[3],gu=res[4],au=res[5],df=res[6],mt=res[7],rem=res[8],crit=res[9];
   window._crit=(crit&&crit.criticality)||window._crit||{};for(var _k in nodes){var _n=nodes[_k];if(_n.cr){_n.cr.setAttribute('stroke',critColor(_n.ip)||'none');}}
   window._armed=!!(df&&df.enforce_enabled);window._maint=!!(mt&&mt.active);
   var db=document.getElementById('defbtn');db.textContent='DEFENSE: '+(window._armed?'ARMED':'DISARMED');
   db.style.borderColor=window._armed?'#3fb950':'#f85149';db.style.color=window._armed?'#7ee2a8':'#ff7b72';
   var mb=document.getElementById('maintbtn');mb.textContent='MAINT: '+(window._maint?('ON '+mt.remaining_s+'s'):'off');
   mb.style.borderColor=window._maint?'#e3b341':'#2b3444';mb.style.color=window._maint?'#e3b341':'#c9d1d9';
   window._lastFeeds={status:st,hosts:ho,ports:po,links:li,guard:gu,audit:au};
   var off=!!st.error||!st.switches;
   document.getElementById('live').className=off?'dot off':'dot';
   document.getElementById('upd').textContent=(off?'controller offline · ':'synced ')+new Date().toLocaleTimeString();
   var sw=st.switches||[];
   document.getElementById('sw').innerHTML=[['ovsgw',3],['ovs1',1],['ovs2',2]].map(function(x){
     var up=sw.indexOf(x[1])>=0;return '<span class="tier '+(up?'OPERATIONAL':'FORBIDDEN')+'" style="margin:2px 4px 2px 0;display:inline-block">'+x[0]+' '+(up?'up':'down')+'</span>';}).join('')
     +'<span class="tier '+(off?'FORBIDDEN':'OPERATIONAL')+'" style="display:inline-block">controller '+(off?'DOWN':'ok')+'</span>'
     +'<div style="margin-top:7px"><span class="tier '+(st.guard?'OPERATIONAL':'FORBIDDEN')+'">src-guard '+(st.guard?'armed':'off')+'</span> <span class="tier '+(st.arp_guard?'OPERATIONAL':'FORBIDDEN')+'">arp-guard '+(st.arp_guard?'armed':'off')+'</span></div>';
   var drops=(gu&&gu.drops)||{};var nz=Object.keys(drops).filter(function(k){return drops[k]>0;}).sort(function(a,b){return drops[b]-drops[a];});
   var tot=Object.keys(drops).reduce(function(s,k){return s+drops[k];},0);
   document.getElementById('guard').innerHTML='<div class="sub" style="margin-bottom:6px">'+tot+' spoofed packets dropped at ingress</div>'+
     (nz.length?nz.map(function(k){return '<div class="blk">&#9940; '+drops[k]+' &times; '+k+'</div>';}).join(''):'<div class="none">no spoof attempts — guard armed &amp; clean</div>');
   var modelIP={};ANCH.forEach(function(a){if(a.model&&a.ip)modelIP[a.ip]=1;});
   var discIP={};(ho.hosts||[]).forEach(function(h){if(h.ip)discIP[h.ip]=1;});
   ANCH.forEach(function(a){if(a.model&&a.ip&&nodes[a.id]){if(discIP[a.ip])nodes[a.id].c.removeAttribute('stroke-dasharray');else nodes[a.id].c.setAttribute('stroke-dasharray','3 3');}});
   var hn=computeHosts(ho.hosts||[]).filter(function(h){return !modelIP[h.ip];});
   reconcile(hn); rebuildLinks(li.links||[],hn);
   var ports=po.ports||{};window._down={};
   LINKS.forEach(function(l){var up=true;
     if(l.k==='host'){up=(ports[String(l.bd)]||{})[String(l.bport)]!=='down';}
     else if(l.k==='fabric'){up=(ports[String(l.ad)]||{})[String(l.aport)]!=='down'&&(ports[String(l.bd)]||{})[String(l.bport)]!=='down';}
     l.el.setAttribute('class','lk '+l.k+(up?'':' broken'));});
   [['sw1',1],['sw2',2],['sw3',3]].forEach(function(x){if(nodes[x[0]])nodes[x[0]].c.setAttribute('stroke',sw.indexOf(x[1])>=0?TYPE.sw.c:'#59626e');});
   hn.forEach(function(h){var s2=(ports[String(h.dpid)]||{})[String(h.port)];var dn=s2==='down';
     window._down[h.id]=dn;if(nodes[h.id]){nodes[h.id].c.setAttribute('stroke',dn?'#f85149':TYPE[h.t].c);nodes[h.id].tx.setAttribute('fill',dn?'#f85149':'#c9d1d9');}});
   document.getElementById('inv').innerHTML='<tr><td class=sub>device</td><td class=sub>ip</td><td class=sub>@ port</td><td class=sub>link</td></tr>'+
     hn.map(function(h){var dn=window._down[h.id];
       return '<tr><td><b>'+h.lbl+'</b></td><td class=t>'+(h.ip||'?')+'</td><td class=sub>ovs'+h.dpid+':p'+h.port+'</td><td class="'+(dn?'down':'up')+'">'+(dn?'DOWN':'up')+'</td></tr>';}).join('');
   var seen={},blocks=[];(st.conduit_blocks||[]).concat(st.mac_blocks||[]).forEach(function(x){var k=x.replace(/^dpid\d+:/,'');if(!seen[k]){seen[k]=1;blocks.push(k);}});
   window._blocks=blocks;
   document.getElementById('blocks').innerHTML=blocks.length?blocks.map(function(x){return '<div class="blk">&#9940; '+x+'</div>';}).join(''):'<div class="none">No active blocks — all conduits flowing.</div>';
   bgl.innerHTML='';for(var k in nodes)nodes[k].g.classList.remove('attack');
   var fab={};(li.links||[]).forEach(function(f){fab[f.src_dpid]=1;fab[f.dst_dpid]=1;});
   function byip(ip){var r=[];ANCH.forEach(function(a){if(a.ip===ip&&nodes[a.id])r.push(a);});hn.forEach(function(h){if(h.ip===ip)r.push(h);});return r;}
   blocks.forEach(function(b){var m=b.match(/([\d.]+)->([\d.]+)/);if(!m)return;
     var srcs=byip(m[1]),dsts=byip(m[2]);
     var conn=dsts.filter(function(d){return d.dpid==null||fab[d.dpid];});if(conn.length)dsts=conn;
     srcs.forEach(function(s){if(nodes[s.id])nodes[s.id].g.classList.add('attack');
       dsts.forEach(function(d){if(!nodes[d.id])return;var ov=document.createElementNS(NS,'line');ov.setAttribute('class','blkline');ov.dataset.s=s.id;ov.dataset.d=d.id;bgl.appendChild(ov);});});});
   var lines=(au.audit)||[];var RK={BLOCK:'rBLOCK',THROTTLE:'rTHROTTLE',DEFLECT:'rDEFLECT',ISOLATE:'rISOLATE',ALLOW:'rALLOW',REFUSED:'rREFUSE'};
   document.getElementById('feed').innerHTML=lines.slice().reverse().slice(0,30).map(function(L){
     var m=L.match(/^(\S+)\s+(\S+)\s+(.+?)\s+=>\s+(.+)$/);if(!m)return '';
     var rw=(m[4].match(/^(\w+)/)||[])[1]||'';var rc=RK[rw]||'';
     var rb=rc?'<span class="tier '+rc+'" title="'+m[4].replace(/"/g,'')+'">'+(rw==='REFUSED'?'REFUSE':rw)+'</span> ':'';
     var op=(L.match(/\b(WRITE|READ|S7|CONTROL|DIAG|PROGRAM|ILLEGAL)\b/)||[])[1]||'';var ob=op?'<span class="tier op'+op+'">'+op+'</span> ':'';
     var mid=m[3].replace(/\s+(WRITE|READ|S7|CONTROL|DIAG|PROGRAM|ILLEGAL)$/,'');
     return '<div class="row"><span class="t">'+m[1]+'</span><span class="tier '+m[2]+'">'+m[2]+'</span> '+ob+rb+'<span style="flex:1;font-size:11px">'+mid+'</span></div>';}).join('');
   // ---- Process-remediation feed (agent .2.45, read from local file, not the controller) ----
   if(rem&&rem.status)window._remLast=rem;var REM=(rem&&rem.status)?rem:(window._remLast||{status:null,events:[]});
   (function(){var el=document.getElementById('remed');if(!el)return;
     var s=REM.status;
     if(!s){el.innerHTML='<div class="none">agent offline — no process-state feed</div>';return;}
     var fresh=(Date.now()/1000-(s.ts||0))<6;
     var lvl=(s.level!=null)?(+s.level).toFixed(1):'?',lg=(s.last_good!=null)?(+s.last_good).toFixed(1):'?';
     var restos=(REM.events||[]).filter(function(e){return e.event==='RESTORED';});
     el.innerHTML='<div class="sub" style="margin-bottom:6px;line-height:1.9">'
       +'<span class="tier '+(fresh?'OPERATIONAL':'FORBIDDEN')+'">agent '+(fresh?'online':'stale')+'</span> '
       +'<span class="tier rALLOW">Tank.Level '+lvl+'</span> '
       +'<span class="tier SENSITIVE">last-good '+lg+'</span> '
       +'<span class="tier rRESTORE">restores '+(s.restores||0)+'</span></div>'
       +(restos.slice(-6).reverse().map(function(e){
           return '<div class="blk" style="background:#1c1330;color:#c792ea;border:1px solid #3a2a55">&#8635; restored last-good '
             +(e.last_good!=null?(+e.last_good).toFixed(1):'?')+' &middot; saw tampered '+(e.level!=null?(+e.level).toFixed(1):'?')+'</div>';}).join('')
         ||'<div class="none">no tamper — process nominal, tracking last-good</div>');})();
   ((REM.events)||[]).forEach(function(e){if(e.event!=='RESTORED')return;
     var key='REM#'+e.ts+'#'+e.restores;if(window._seen[key])return;window._seen[key]=1;
     window._log.push({time:(function(t){var d=new Date(t*1000),z=function(n){return(n<10?'0':'')+n;};return z(d.getMonth()+1)+'-'+z(d.getDate())+'T'+z(d.getHours())+':'+z(d.getMinutes())+':'+z(d.getSeconds());})(e.ts||0),tier:'OPERATIONAL',
       src:'192.168.2.45',srole:'remediation',dst:'192.168.2.10',drole:'plc',proto:'S7',op:'RESTORE',
       resp:'RESTORE',mode:'REMEDIATE',
       action:'RESTORED last-good '+(e.last_good!=null?(+e.last_good).toFixed(1):'?')+' (saw tampered '+(e.level!=null?(+e.level).toFixed(1):'?')+')',
       raw:'REM '+e.ts+' restored last-good '+e.last_good+' saw '+e.level});});
   if(typeof renderLog==='function'&&document.getElementById('viewLog')&&document.getElementById('viewLog').style.display!=='none')renderLog();
 });}
poll();setInterval(poll,1200);
</script></body></html>"""


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def do_GET(self):
        try:
            if self.path == "/":
                self._s(HTML.encode(), "text/html")
            elif self.path == "/api/remediation":
                self._s(remediation_feed(), "application/json")
            elif self.path.startswith("/api/"):
                try:
                    d = urllib.request.urlopen(CARS + "/cars/" + self.path[len("/api/"):], timeout=3).read()
                except Exception as e:
                    d = json.dumps({"error": str(e)}).encode()
                self._s(d, "application/json")
            else:
                self._s(b"not found", "text/plain", 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def do_POST(self):
        try:
            if self.path.startswith("/api/"):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n) if n else b"{}"
                req = urllib.request.Request(CARS + "/cars/" + self.path[len("/api/"):], data=body,
                                             headers={"Content-Type": "application/json"}, method="POST")
                try:
                    d = urllib.request.urlopen(req, timeout=3).read()
                except Exception as e:
                    d = json.dumps({"error": str(e)}).encode()
                self._s(d, "application/json")
            else:
                self._s(b"not found", "text/plain", 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def _s(self, body, ctype, code=200):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


class Threaded(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    print("CARS live topology v5 on http://0.0.0.0:%d  (proxying %s)" % (PORT, CARS))
    Threaded(("0.0.0.0", PORT), H).serve_forever()
