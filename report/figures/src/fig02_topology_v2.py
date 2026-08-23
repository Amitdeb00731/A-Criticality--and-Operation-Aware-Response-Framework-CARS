#!/usr/bin/env python3
# Clean, high-level logical topology for Fig 3.1: switches + roles + criticality tiers.
# Addresses and the full port map are deferred to the appendix (per the general-design pass).
import cairosvg, os
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK="#1B2A3A"; MUT="#6B7E8F"; LINE="#B7C4CE"
CTRL_F="#EAE1F5"; CTRL_S="#7B5EA7"
SW_F="#D9EEF2"; SW_S="#0B6E7A"
CELL_F="#F4F8FB"; CELL_S="#C7D4DE"
PLC_F="#FCE7CC"; PLC_S="#E0952F"
HMI_F="#E9DCF3"; HMI_S="#7B5EA7"
SUP_F="#FBF3CF"; SUP_S="#C9A227"
SNS_F="#DCECF6"; SNS_S="#3D7EA6"
HP_F="#DDEFDD"; HP_S="#4E9A51"
ATK_F="#F8D7D7"; ATK_S="#B21F26"
W,H=1440,880
def box(x,y,w,h,f,s,r=10,sw=2): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" stroke="{s}" stroke-width="{sw}"/>'
def t(x,y,s,sz=15,c=INK,anc="middle",b=True,it=False):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial" font-size="{sz}" fill="{c}" text-anchor="{anc}" font-weight="{"bold" if b else "normal"}" font-style="{"italic" if it else "normal"}">{s}</text>'
def node(x,y,w,h,f,s,name,tier=None):
    g=box(x,y,w,h,f,s,8,2)+t(x+w/2,y+(h/2 if not tier else h/2-6),name,14)
    if tier: g+=t(x+w/2,y+h/2+15,tier,11,MUT,b=False)
    return g
def switch(cx,cy,label):
    return (box(cx-46,cy-26,92,52,SW_F,SW_S,10,2.5)
            + f'<path d="M{cx-24} {cy-4} h48 M{cx-24} {cy+6} h48" stroke="{SW_S}" stroke-width="3"/>'
            + f'<path d="M{cx+24} {cy-9} l6 5 l-6 5 M{cx-24} {cy+1} l-6 5 l6 5" fill="none" stroke="{SW_S}" stroke-width="2.5"/>'
            + t(cx,cy+40,label,15,SW_S))
body=[]
# controller
body.append(box(560,26,320,74,CTRL_F,CTRL_S,12,2.5))
body.append(t(720,55,"CARS controller",17,CTRL_S))
body.append(t(720,78,"os-ken · OpenFlow 1.3 · decision brain",12,MUT,b=False))
# cells
body.append(box(40,190,360,470,CELL_F,CELL_S,14,2)); body.append(t(70,222,"Cell-1  ·  ovs1",15,SW_S,anc="start"))
body.append(box(470,170,500,690,CELL_F,CELL_S,14,2)); body.append(t(500,202,"Gateway  ·  ovsgw",15,SW_S,anc="start"))
body.append(box(1040,190,360,470,CELL_F,CELL_S,14,2)); body.append(t(1070,222,"Cell-2  ·  ovs2  (via NAT)",15,SW_S,anc="start"))
# switches
body.append(switch(220,300,"ovs1")); body.append(switch(720,300,"ovsgw")); body.append(switch(1220,300,"ovs2"))
# control-plane dashed links
for sx in (220,720,1220):
    body.append(f'<path d="M720 100 L{sx} 274" stroke="{CTRL_S}" stroke-width="2" stroke-dasharray="6 6" fill="none" opacity="0.8"/>')
# data links
body.append(f'<path d="M266 300 H674" stroke="{INK}" stroke-width="2.5"/>'); body.append(t(470,290,"patch",12,MUT,b=False))
body.append(f'<path d="M766 300 H1174" stroke="{INK}" stroke-width="2.5"/>'); body.append(t(970,290,"transit + NAT",12,MUT,b=False))
# Cell-1 assets
body.append(node(70,470,140,80,PLC_F,PLC_S,"PLC1","plc · CRITICAL"))
body.append(node(230,470,150,80,HMI_F,HMI_S,"HMI1","hmi · HIGH"))
body.append(f'<path d="M160 356 L140 466" stroke="{LINE}" stroke-width="2"/>')
body.append(f'<path d="M280 356 L300 466" stroke="{LINE}" stroke-width="2"/>')
# Gateway roles (2 cols)
gx=[(500,"SCADA","supervisory"),(720,"Historian","supervisory"),(500,"EWS / Factory IO","engineering + HIL"),(720,"Modbus unit","plc · LOW"),
    (500,"Snort mirror","DPI sensor"),(720,"Honeypot","deception decoy"),(610,"Attacker vantage","unregistered")]
ys=[380,380,470,470,560,560,650]
cols={"SCADA":(SUP_F,SUP_S),"Historian":(SUP_F,SUP_S),"EWS / Factory IO":(SUP_F,SUP_S),"Modbus unit":(PLC_F,PLC_S),
      "Snort mirror":(SNS_F,SNS_S),"Honeypot":(HP_F,HP_S),"Attacker vantage":(ATK_F,ATK_S)}
for (x,name,sub),y in zip(gx,ys):
    f,s=cols[name]; w=200 if name=="Attacker vantage" else 200
    body.append(node(x,y,200,70,f,s,name,sub))
# Cell-2 assets
body.append(node(1070,470,140,80,PLC_F,PLC_S,"PLC2","plc · HIGH"))
body.append(node(1230,470,150,80,HMI_F,HMI_S,"HMI2","hmi · MEDIUM"))
body.append(f'<path d="M1160 356 L1140 466" stroke="{LINE}" stroke-width="2"/>')
body.append(f'<path d="M1280 356 L1300 466" stroke="{LINE}" stroke-width="2"/>')
# footnote
body.append(t(720,838,"All traffic to a protected asset crosses the CARS fabric. Roles and criticality tiers shown; host addresses and the full port map are in the appendix.",12.5,MUT,b=False,it=True))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>{"".join(body)}</svg>'
cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT,"fig02_topology_v2.png"), output_width=W*2, output_height=H*2)
print("wrote fig02_topology_v2.png")
