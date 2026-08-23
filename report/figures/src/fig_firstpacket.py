#!/usr/bin/env python3
# Gap 3: first-packet leakage of an atomic command on a compromised allowlisted conduit.
# Clean sequence diagram, generous spacing, no overlapping text. No invented measurements.
import cairosvg, os
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK="#1B2A3A"; MUT="#6B7E8F"; LINE="#B7C4CE"
TEAL="#0B6E7A"; TEALF="#D9EEF2"
RED="#B21F26"; REDF="#F8D7D7"
PLCF="#FCE7CC"; PLCS="#E0952F"
OOB="#6E7B99"; OOBF="#ECEFF5"
GRN="#4E9A51"; GRNF="#EFF7F3"; BAND="#FBEBEC"
W,H=1400,880
HX={'host':210,'fab':720,'plc':1230}
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def box(x,y,w,h,f,s,r=8,sw=2,op=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" stroke="{s}" stroke-width="{sw}" fill-opacity="{op}"/>'
def t(x,y,s,sz=15,c=INK,anc="middle",b=False,it=False,mono=False):
    fam="DejaVu Sans Mono, monospace" if mono else "Segoe UI, Arial"
    return f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{sz}" fill="{c}" text-anchor="{anc}" font-weight="{"bold" if b else "normal"}" font-style="{"italic" if it else "normal"}">{esc(s)}</text>'
def harrow(x1,x2,y,c,dash=False,sw=2.5):
    d=' stroke-dasharray="7 6"' if dash else ''
    tip=x2-10 if x2>x1 else x2+10
    ah=f'<path d="M{x2} {y} L{tip} {y-5} L{tip} {y+5} Z" fill="{c}"/>'
    return f'<path d="M{x1} {y} H{x2}" stroke="{c}" stroke-width="{sw}"{d} fill="none"/>'+ah
b=[]
# leaked-window band (drawn first = behind)
b.append(box(720,234,510,500,BAND,"none",0,0,0.55))
b.append(t(975,472,"leaked window — first packet already delivered",13.5,RED,it=True))
# headers + lifelines
for k,label,f,s,x0,w in [('host','Compromised allowlisted host',REDF,RED,60,300),
                          ('fab','CARS fabric · Table 1 POLICY',TEALF,TEAL,560,320),
                          ('plc','Target PLC',PLCF,PLCS,1080,300)]:
    x=HX[k]
    b.append(box(x0,40,w,50,f,s,10,2.5))
    b.append(t(x,71,label,15.5,INK,b=True))
    b.append(f'<path d="M{x} 90 V800" stroke="{LINE}" stroke-width="2" stroke-dasharray="4 6"/>')
# 1 STOP
b.append(harrow(HX['host'],HX['fab'],170,RED))
b.append(t((HX['host']+HX['fab'])/2,158,"S7 STOP (0x29) on the permitted conduit",14,INK))
# 2 delivered
b.append(harrow(HX['fab'],HX['plc'],250,INK))
b.append(t((HX['fab']+HX['plc'])/2,238,"permitted (established / allowlisted) → delivered",14,INK))
# 3 PLC state box
b.append(box(1080,290,300,52,PLCF,PLCS,8,2))
b.append(t(1230,322,"state change taken on receipt",13.5,INK,b=True))
# out-of-band stack (centre x=470), clear of the band
oob=[("out-of-band mirror copy",372),("Snort DPI: alert on 0x29",430),
     ("controller classify() → FORBIDDEN",488),("OFPT_FLOW_MOD (isolate)",546)]
b.append(f'<path d="M{HX["fab"]} 250 C 600 300, 560 330, 470 372" stroke="{OOB}" stroke-width="2" stroke-dasharray="7 6" fill="none"/>')
for label,y in oob:
    b.append(box(320,y,300,44,OOBF,OOB,7,1.6))
    b.append(t(470,y+28,label,13,OOB))
# connector down to the green box
b.append(f'<path d="M470 590 C 470 615, 640 610, 720 626" stroke="{OOB}" stroke-width="2" stroke-dasharray="7 6" fill="none"/>')
# green drop box on the fabric
b.append(box(530,628,380,58,GRNF,GRN,8,2))
b.append(t(720,653,"reactive drop installed",14,INK,b=True))
b.append(t(720,674,"Table 1, priority 110, cookie 0x00ca",12,MUT,mono=True))
# annotation arrow, well below the green box
b.append(harrow(912,1078,716,GRN,sw=2))
b.append(t(995,704,"drop now active — but the STOP already landed",12.5,"#3E4A57",it=True))
# footnote
b.append(t(W/2,824,"The proactive default-deny stops an unregistered source before any payload lands; this residual is only reachable from a compromised",12.5,MUT,it=True))
b.append(t(W/2,844,"allowlisted conduit, and is the analytical counterpart of the measured first-packet leak of Section 4.6. Process inertia buffers an analog",12.5,MUT,it=True))
b.append(t(W/2,864,"write; a discrete command does not wait.",12.5,MUT,it=True))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>{"".join(b)}</svg>'
cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT,"fig_firstpacket.png"), output_width=W*2, output_height=H*2)
print("wrote fig_firstpacket.png")
