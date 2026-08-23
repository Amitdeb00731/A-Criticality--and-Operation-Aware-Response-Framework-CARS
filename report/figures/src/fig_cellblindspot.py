#!/usr/bin/env python3
# Gap 2: spatial sensing asymmetry. The Snort mirror taps ovsgw only, so an intra-cell
# attack on ovs2 never reaches the sensor (DPI blind), while the proactive layer still applies.
import cairosvg, os
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK="#1B2A3A"; MUT="#6B7E8F"; LINE="#B7C4CE"
TEAL="#0B6E7A"; TEALF="#D9EEF2"
CTRLF="#EAE1F5"; CTRLS="#7B5EA7"
SNSF="#DCECF6"; SNSS="#3D7EA6"
CELLF="#F4F8FB"; CELLS="#C7D4DE"
PLCF="#FCE7CC"; PLCS="#E0952F"
HMIF="#E9DCF3"; HMIS="#7B5EA7"
RED="#B21F26"; REDF="#F8D7D7"
GRN="#2F8F46"
W,H=1480,940
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def box(x,y,w,h,f,s,r=8,sw=2,op=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" stroke="{s}" stroke-width="{sw}" fill-opacity="{op}"{d}/>'
def t(x,y,s,sz=14,c=INK,anc="middle",b=False,it=False,mono=False):
    fam="DejaVu Sans Mono, monospace" if mono else "Segoe UI, Arial"
    return f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{sz}" fill="{c}" text-anchor="{anc}" font-weight="{"bold" if b else "normal"}" font-style="{"italic" if it else "normal"}">{esc(s)}</text>'
def node(cx,cy,w,h,f,s,name,tier=None):
    g=box(cx-w/2,cy-h/2,w,h,f,s,8,2)
    if tier:
        g+=t(cx,cy-3,name,14,INK,b=True)+t(cx,cy+16,tier,11.5,MUT)
    else:
        g+=t(cx,cy+5,name,14,INK,b=True)
    return g
def link(x1,y1,x2,y2,c,sw=2,dash=None,arrow=False):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    s=f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{c}" stroke-width="{sw}"{d} fill="none"/>'
    if arrow:
        import math; ang=math.atan2(y2-y1,x2-x1)
        for da in (math.radians(150),math.radians(-150)):
            s+=f'<path d="M{x2} {y2} L{x2+12*math.cos(ang+da)} {y2+12*math.sin(ang+da)}" stroke="{c}" stroke-width="{sw}" fill="none"/>'
    return s
b=[]
# cells (behind)
CELL1=(70,300,380,470); GW=(520,300,300,470); CELL2=(900,300,500,470)
for (x,y,w,h),lab in [(CELL1,'Cell-1 · ovs1'),(GW,'Gateway · ovsgw'),(CELL2,'Cell-2 · ovs2')]:
    b.append(box(x,y,w,h,CELLF,CELLS,14,2))
    b.append(t(x+18,y+28,lab,15,TEAL,anc='start',b=True))
# out-of-band controller + snort
b.append(box(330,40,240,74,CTRLF,CTRLS,10,2.5)); b.append(t(450,72,'CARS controller',15,CTRLS,b=True)); b.append(t(450,94,'os-ken · OpenFlow 1.3',11.5,MUT))
b.append(box(690,40,250,74,SNSF,SNSS,10,2.5)); b.append(t(815,72,'Snort DPI sensor',15,SNSS,b=True)); b.append(t(815,94,'passive SPAN mirror',11.5,MUT))
# switches
SW={'ovs1':(260,410),'ovsgw':(670,410),'ovs2':(1150,410)}
for k,(cx,cy) in SW.items():
    b.append(box(cx-70,cy-30,140,60,TEALF,TEAL,10,2.5)); b.append(t(cx,cy+6,k,15,TEAL,b=True))
# control-plane dashed (purple)
for k in SW:
    cx,cy=SW[k]; b.append(link(450,114,cx,cy-30,CTRLS,2,'6 6'))
# mirror link (gateway only) - grey, emphasised
b.append(link(815,114,SW['ovsgw'][0],SW['ovsgw'][1]-30,SNSS,3))
b.append(t(880,250,'mirror (gateway only)',12.5,SNSS,it=True,anc='start'))
# data links
b.append(link(330,410,600,410,INK,2.5)); b.append(t(465,398,'patch',12,MUT))
b.append(link(740,410,1080,410,INK,2.5)); b.append(t(910,398,'transit',12,MUT))
# assets
b.append(node(170,600,150,66,PLCF,PLCS,'PLC1','plc · CRITICAL'))
b.append(node(350,600,150,66,HMIF,HMIS,'HMI1','hmi · HIGH'))
b.append(link(200,567,250,440,LINE,2)); b.append(link(330,567,272,440,LINE,2))
b.append(node(1020,600,150,66,PLCF,PLCS,'PLC2','plc · HIGH'))
b.append(node(1290,600,150,66,HMIF,HMIS,'HMI2','hmi · MEDIUM'))
b.append(link(1250,567,1180,440,LINE,2))
# in-cell attacker
b.append(box(1150-95,720-33,190,66,REDF,RED,8,2))
b.append(t(1150,716,'in-cell attacker',13.5,RED,b=True)); b.append(t(1150,736,'compromised / foothold',11,MUT))
# RED intra-cell path: attacker -> ovs2 -> PLC2
b.append(link(1150,687,1150,440,RED,4,None,True))
b.append(link(1120,435,1055,567,RED,4,None,True))
b.append(t(1150,505,'intra-cell attack',13,RED,b=True,anc='start'))
b.append(t(1150,524,'stays on ovs2',12,RED,anc='start'))
# blind badge near cell-2 (below the cell title)
b.append(box(980,344,240,34,'#FBEBEC','none',8,0,0.95))
b.append(t(1100,367,'not mirrored → DPI blind',13,RED,b=True))
# seen badge near gateway (below the gateway title)
b.append(box(528,344,284,34,'#EAF6EE','none',8,0,0.95))
b.append(t(670,367,'crosses here → mirrored → DPI sees',12.5,GRN,b=True))
# legend
ly=828
b.append(link(90,ly,150,ly,GRN,4,None,True)); b.append(t(160,ly+5,'Crosses the gateway → mirrored to Snort → operation-aware (DPI) response.',13,INK,anc='start'))
b.append(link(90,ly+34,150,ly+34,RED,4,None,True)); b.append(t(160,ly+39,'Stays within a cell → never reaches the mirror → no operation-aware response.',13,INK,anc='start'))
b.append(t(90,ly+72,'The proactive layer (GUARD identity-binding and default-deny) runs on every switch, so an unregistered intra-cell source is still refused; the',12,MUT,anc='start',it=True))
b.append(t(90,ly+90,'blind spot is the operation-aware tier for a compromised, already-allowlisted conduit. Per-cell sensing is the mitigation (future work).',12,MUT,anc='start',it=True))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>{"".join(b)}</svg>'
cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT,"fig_cellblindspot.png"), output_width=W*2, output_height=H*2)
print("wrote fig_cellblindspot.png")
