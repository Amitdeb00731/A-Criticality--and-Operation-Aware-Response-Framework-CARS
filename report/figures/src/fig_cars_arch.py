# Diagram A (v2): the CARS FRAMEWORK architecture — environment-independent, no testbed.
import cairosvg
INK="#1f2d3d"; SUB="#5b6b7d"; LINE="#3a4a5c"
CTRL="#2f6db0"; CFG="#c9922b"; DP="#3a8f5b"; SENS="#8a4fb0"; ASSET="#6b7480"; ACC="#b23b3b"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
P=[]
def box(x,y,w,h,fill,stroke,title,subs=None,tcol="#1f2d3d",rx=9,tsize=14,sw=2,talign="middle"):
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    tx = x+w/2 if talign=="middle" else x+12
    P.append(f'<text x="{tx}" y="{y+22}" text-anchor="{talign}" font-family="Helvetica" font-size="{tsize}" font-weight="700" fill="{tcol}">{esc(title)}</text>')
    if subs:
        for i,s in enumerate(subs):
            P.append(f'<text x="{x+w/2}" y="{y+43+i*15}" text-anchor="middle" font-family="Helvetica" font-size="11" fill="{tcol}">{esc(s)}</text>')
def arrow(x1,y1,x2,y2,col=LINE,w=2.2,dash="",label=None,lx=None,ly=None):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    P.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d} marker-end="url(#ah)"/>')
    if label: txt(lx or (x1+x2)/2, ly or (y1+y2)/2, label, 10.5, col, "middle","600","italic")
def txt(x,y,s,size=11,col=INK,anchor="middle",weight="400",style=""):
    st=f' font-style="{style}"' if style else ""
    P.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Helvetica" font-size="{size}" font-weight="{weight}" fill="{col}"{st}>{esc(s)}</text>')
W,H=1180,560
txt(60,40,"The CARS framework: a criticality- and operation-aware SDN intrusion-response architecture",16,INK,"start","700")
# --- site configuration (left, portable) ---
box(50,120,220,215,"#fbf1dc",CFG,"Site configuration")
for i,s in enumerate(["asset registry + criticality tiers","role / operation taxonomy","rulebook (role x op -> tier)","conduit allowlist","identity bindings"]):
    P.append(f'<text x="160" y="{165+i*26}" text-anchor="middle" font-family="Helvetica" font-size="12" fill="{INK}">{esc("- "+s)}</text>')
txt(160,320,"describes a site; the engine is unchanged",10,CFG,"middle","600","italic")
# --- control plane: the decision engine ---
box(320,95,540,175,"#eaf1f9",CTRL,"Control plane — CARS decision engine",None,INK,15)
box(340,135,160,120,"#ffffff",CTRL,"Proactive policy",["identity binding","conduit allowlist","default-deny"],INK,7,12,1.6)
box(512,135,180,120,"#ffffff",CTRL,"Reactive decision",["operation x role x","criticality -> tier","-> response ladder"],INK,7,12,1.6)
box(704,135,140,120,"#ffffff",CTRL,"Self-check",["flow-integrity","authenticated","control API"],INK,7,12,1.6)
# config -> controller
arrow(270,180,320,180,CFG,2.4)
# --- DPI sensor (right) feeding reactive decision ---
box(910,140,230,80,"#f2ebf7",SENS,"DPI sensor",["recovers the industrial operation","from mirrored traffic"],INK,9,13)
arrow(910,180,860,180,SENS,2.2); txt(885,170,"operation",9.5,SENS,"middle","600")
# --- data plane: enforcement pipeline ---
box(320,370,540,120,"#e8f5ee",DP,"Data plane — enforcement pipeline (on every switch)",None,INK,15)
for i,(t,c) in enumerate([("Table 0\nGUARD","identity"),("Table 1\nPOLICY","stateful + reactive"),("Table 2\nSWITCH","forward")]):
    bx=340+i*172
    P.append(f'<rect x="{bx}" y="410" width="152" height="64" rx="7" fill="#ffffff" stroke="{DP}" stroke-width="1.6"/>')
    lines=t.split("\n")
    txt(bx+76,432,lines[0],12,INK,"middle","700"); txt(bx+76,448,lines[1],12,INK,"middle","700")
    txt(bx+76,466,c,10,SUB,"middle")
    if i<2: arrow(bx+152,442,bx+172,442)
# controller -> data plane (install rules)
arrow(590,270,590,370,CTRL,2.4,"","",0,0)
txt(600,325,"installs flow rules (OpenFlow):  proactive 0x00a2,  reactive 0x00ca (criticality-scaled self-heal)",10.5,CTRL,"start","600","italic")
# traffic in and asset out
txt(300,442,"traffic",11,SUB,"end"); arrow(302,442,340,442)
arrow(860,442,905,442); box(905,415,150,54,"#eef0f2",ASSET,"protected asset",None,INK,8,12)
# principles strip
txt(60,530,"Principles:  decide is separate from enforce   ·   the decision (a tier) is separate from the response (an action)   ·   every response is bounded, reversible and evidence-generating",11.5,ACC,"start","600")
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica">
<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="{LINE}"/></marker></defs>
<rect width="{W}" height="{H}" fill="white"/>{"".join(P)}</svg>'''
open("/tmp/diagA2.svg","w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to="/tmp/diagA2.png",scale=2)
print("ok")
