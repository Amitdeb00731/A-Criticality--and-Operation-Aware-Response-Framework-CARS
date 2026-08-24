# Diagram A: CARS architecture + deployment (merges the old overview 3.7 and deployment 3.13).
import cairosvg
INK="#1f2d3d"; SUB="#5b6b7d"; LINE="#3a4a5c"
CTRL="#c9922b"; SW="#2f6db0"; PLC="#3a8f5b"; SNORT="#8a4fb0"; PROC="#b23b3b"; NODE="#9aa6b2"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
P=[]
def box(x,y,w,h,fill,stroke,title,subs=None,tcol="#1f2d3d",rx=8,tsize=13,sw=2):
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    P.append(f'<text x="{x+w/2}" y="{y+18}" text-anchor="middle" font-family="Helvetica" font-size="{tsize}" font-weight="700" fill="{tcol}">{esc(title)}</text>')
    if subs:
        for i,s in enumerate(subs):
            P.append(f'<text x="{x+w/2}" y="{y+34+i*14}" text-anchor="middle" font-family="Helvetica" font-size="10.5" fill="{tcol}">{esc(s)}</text>')
def asset(x,y,w,name,tier,col):
    box(x,y,w,44,"#ffffff",col,name,[tier],INK,7,12,1.8)
def line(x1,y1,x2,y2,col=LINE,w=2,dash="",arrow=True):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    a=' marker-end="url(#ah)"' if arrow else ""
    P.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d}{a}/>')
def txt(x,y,s,size=11,col=INK,anchor="middle",weight="400",style=""):
    st=f' font-style="{style}"' if style else ""
    P.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Helvetica" font-size="{size}" font-weight="{weight}" fill="{col}"{st}>{esc(s)}</text>')
W,H=1180,620
txt(60,38,"CARS architecture and deployment",18,INK,"start","700")
# deployment node backgrounds (dashed grey groups)
P.append('<rect x="360" y="58" width="360" height="96" rx="10" fill="#f7f9fb" stroke="#9aa6b2" stroke-width="1.4" stroke-dasharray="5 4"/>')
txt(690,74,"controller node",10.5,NODE,"end","600")
P.append('<rect x="70" y="196" width="770" height="250" rx="10" fill="#f7f9fb" stroke="#9aa6b2" stroke-width="1.4" stroke-dasharray="5 4"/>')
txt(830,212,"fabric + sensing node (Cell-1 + gateway)",10.5,NODE,"end","600")
P.append('<rect x="860" y="196" width="250" height="250" rx="10" fill="#f7f9fb" stroke="#9aa6b2" stroke-width="1.4" stroke-dasharray="5 4"/>')
txt(1100,212,"Cell-2 node",10.5,NODE,"end","600")
P.append('<rect x="360" y="500" width="360" height="86" rx="10" fill="#f7f9fb" stroke="#9aa6b2" stroke-width="1.4" stroke-dasharray="5 4"/>')
txt(690,516,"Windows engineering + Factory IO node",10.5,NODE,"end","600")
# controller
box(390,74,300,74,"#fbf1dc",CTRL,"CARS Controller — decides",["os-ken, OpenFlow 1.3 · REST control API","proactive policy · reactive decision · self-check"],INK,8,14)
# switches
sy=250
box(120,sy,200,66,"#eaf1f9",SW,"ovs1 — Cell-1",["OpenFlow switch, fail-secure"])
box(410,sy,220,66,"#eaf1f9",SW,"ovsgw — gateway",["OpenFlow switch, fail-secure"])
box(890,sy,190,66,"#eaf1f9",SW,"ovs2 — Cell-2",["OpenFlow switch, fail-secure"])
# control-plane links (dashed) controller -> switches
for cx in (220,520,985):
    line(540 if cx==520 else (460 if cx==220 else 620),148, cx, sy, CTRL,1.8,"5 4")
txt(770,175,"control plane (out-of-band, OpenFlow)",10.5,CTRL,"middle","600","italic")
# data-plane links between switches
line(320,sy+33,410,sy+33,LINE,2.6,"",False); txt(365,sy+26,"patch",9.5,SUB)
line(630,sy+33,890,sy+33,LINE,2.6,"",False); txt(760,sy+26,"transit (NAT)",9.5,SUB)
# assets under switches
asset(120,sy+96,120,"PLC1","CRITICAL",PLC); asset(250,sy+96,90,"HMI1","HIGH","#c9922b")
asset(400,sy+96,74,"SCADA","scada",NODE); asset(478,sy+96,64,"EWS","ews",NODE)
asset(400,sy+146,84,"Historian","MEDIUM","#c9922b"); asset(490,sy+146,74,"Modbus","LOW",PLC)
asset(568,sy+96,66,"attacker","unknown",PROC)
asset(890,sy+96,110,"PLC2","HIGH","#c9922b"); asset(1006,sy+96,74,"HMI2","MED","#c9922b")
# links switch->assets (thin)
for (ax,sx) in [(180,180),(295,295)]:
    line(sx,sy+66,ax,sy+96,LINE,1.3,"",False)
line(520,sy+66,520,sy+96,LINE,1.3,"",False)
line(945,sy+66,945,sy+96,LINE,1.3,"",False)
# Snort sensor + mirror
box(660,sy,150,66,"#f2ebf7",SNORT,"Snort sensor",["DPI on a gateway mirror"])
line(630,sy+18,660,sy+18,SNORT,1.8,"4 3"); txt(645,sy+12,"mirror",9,SNORT)
# Factory IO process (HIL) linked to PLC1
box(390,516,300,58,"#fdeef0",PROC,"Factory IO — live tank process (HIL)",["engineering workstation .2.55"],INK,8,12)
P.append(f'<path d="M 180 {sy+140} L 180 545 L 390 545" fill="none" stroke="{PROC}" stroke-width="1.8" stroke-dasharray="4 3" marker-end="url(#ah)"/>'); txt(150,420,"S7 control loop",9.5,PROC,"start","600","italic")
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica">
<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="{LINE}"/></marker></defs>
<rect width="{W}" height="{H}" fill="white"/>{"".join(P)}</svg>'''
open("/tmp/diagA.svg","w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to="/tmp/diagA.png",scale=2)
print("ok")
