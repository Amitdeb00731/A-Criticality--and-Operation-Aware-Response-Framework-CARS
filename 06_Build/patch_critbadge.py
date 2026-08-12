import os, py_compile
P=os.path.expanduser('~/cars_dashboard.py')
s=open(P,encoding='utf-8').read()
PAIRS=[
  ("var TYPEOF={plc:'plc',hmi:'hmi',historian:'sup',gateway:'fw',cell2gw:'fw',ews:'sup',remediation:'sup',unknown:'atk'};",
   "var TYPEOF={plc:'plc',hmi:'hmi',historian:'sup',gateway:'fw',cell2gw:'fw',ews:'sup',remediation:'sup',unknown:'atk'};\nvar CRIT={'192.168.2.10':'CRITICAL','192.168.3.10':'HIGH','192.168.2.9':'HIGH','192.168.3.9':'MEDIUM','192.168.2.30':'MEDIUM','192.168.2.20':'LOW'};\nvar CRITC={CRITICAL:'#f85149',HIGH:'#d9902b',MEDIUM:'#e3b341',LOW:'#3a3f4a'};\nfunction acl(ip){return (window._crit&&window._crit[ip])||CRIT[ip]||null;}\nfunction critColor(ip){var a=acl(ip);return a?CRITC[a]:null;}"),
  (" var g=document.createElementNS(NS,'g');g.setAttribute('class','node');\n var c=document.createElementNS(NS,'circle');c.setAttribute('r',ty.r);",
   " var g=document.createElementNS(NS,'g');g.setAttribute('class','node');\n var cr=document.createElementNS(NS,'circle');cr.setAttribute('r',ty.r+4);cr.setAttribute('fill','none');cr.setAttribute('stroke-width','3');cr.setAttribute('stroke',critColor(n.ip)||'none');\n var c=document.createElementNS(NS,'circle');c.setAttribute('r',ty.r);"),
  (' g.appendChild(c);g.appendChild(gl);g.appendChild(tx);ng.appendChild(g);\n n.g=g;n.c=c;n.tx=tx;n.vx=0;n.vy=0;bindDrag(n);return n;}',
   ' g.appendChild(cr);g.appendChild(c);g.appendChild(gl);g.appendChild(tx);ng.appendChild(g);\n n.g=g;n.c=c;n.cr=cr;n.tx=tx;n.vx=0;n.vy=0;bindDrag(n);return n;}'),
  ('<span class="sub">discovered &middot; drag &middot; click to inspect</span>',
   '<span class="sub">discovered &middot; drag &middot; click to inspect</span><span class="sub" style="margin-left:10px">criticality <span style="color:#f85149">&#9679;</span>CRIT <span style="color:#d9902b">&#9679;</span>HIGH <span style="color:#e3b341">&#9679;</span>MED <span style="color:#6e7681">&#9679;</span>LOW</span>'),
  ("'defense','maintenance','remediation'].map(function(e){",
   "'defense','maintenance','remediation','criticality'].map(function(e){"),
  ('   var st=res[0],ho=res[1],po=res[2],li=res[3],gu=res[4],au=res[5],df=res[6],mt=res[7],rem=res[8];',
   "   var st=res[0],ho=res[1],po=res[2],li=res[3],gu=res[4],au=res[5],df=res[6],mt=res[7],rem=res[8],crit=res[9];\n   window._crit=(crit&&crit.criticality)||window._crit||{};for(var _k in nodes){var _n=nodes[_k];if(_n.cr){_n.cr.setAttribute('stroke',critColor(_n.ip)||'none');}}"),
]
for old,new in PAIRS:
    if new in s: continue
    assert s.count(old)==1,'anchor %r (%d)'%(old[:45],s.count(old))
    s=s.replace(old,new,1)
open('/tmp/_critdc.py','w',encoding='utf-8').write(s)
py_compile.compile('/tmp/_critdc.py',doraise=True)
open(P,'w',encoding='utf-8').write(s)
print('criticality badge applied ->',P)
