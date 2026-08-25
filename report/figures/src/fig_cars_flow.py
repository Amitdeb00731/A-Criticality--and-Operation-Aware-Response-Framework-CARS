import cairosvg
INK="#1f2d3d"; SUB="#5b6b7d"; LINE="#3a4a5c"
GUARD="#2f6db0"; POLICY="#3a8f5b"; SWITCH="#6b7480"; DEC="#8a5a2b"; ACC="#b23b3b"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
P=[]
def box(x,y,w,h,fill,stroke,title,subs=None,tcol="#1f2d3d",rx=9,tsize=15):
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    P.append(f'<text x="{x+w/2}" y="{y+23}" text-anchor="middle" font-family="Helvetica" font-size="{tsize}" font-weight="700" fill="{tcol}">{esc(title)}</text>')
    if subs:
        for i,s in enumerate(subs):
            P.append(f'<text x="{x+w/2}" y="{y+44+i*16}" text-anchor="middle" font-family="Helvetica" font-size="11.5" fill="{tcol}">{esc(s)}</text>')
def arrow(x1,y1,x2,y2,col=LINE,w=2.2,dash=""):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    P.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d} marker-end="url(#ah)"/>')
def txt(x,y,s,size=12,col=INK,anchor="middle",weight="400",style=""):
    st=f' font-style="{style}"' if style else ""
    P.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Helvetica" font-size="{size}" font-weight="{weight}" fill="{col}"{st}>{esc(s)}</text>')
def chip(x,y,w,s):
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="13" fill="#eef2f6" stroke="#c2ccd6" stroke-width="1.4"/>')
    txt(x+w/2,y+17,s,11.5,INK,"middle","600")
W,H=1180,470
txt(60,40,"A packet's path through the CARS fabric",18,INK,"start","700")
txt(40,92,"packet",12,SUB); arrow(40,100,90,100)
box(90,72,250,110,"#eaf1f9",GUARD,"Table 0: GUARD",["identity binding (anti-spoof):","a bound source goes to Table 1,","a spoofed one is dropped"])
arrow(340,127,392,127)
box(392,72,300,110,"#e8f5ee",POLICY,"Table 1: POLICY (stateful)",["established passes; an allowlisted","conduit commits; default-deny;","reactive rules sit on top"])
arrow(692,127,744,127)
box(744,72,250,110,"#eef0f2",SWITCH,"Table 2: SWITCH",["learning forward to the","destination asset"])
arrow(994,127,1044,127); txt(1052,131,"asset",12,SUB,"start")
# decision band
txt(60,222,"The reactive decision that installs a rule into Table 1",15,INK,"start","700")
box(60,250,300,150,"#fbf3ea",DEC,"Snort DPI recovers the operation")
for i,o in enumerate(["READ","WRITE","CONTROL","DIAG","PROGRAM","ILLEGAL"]):
    chip(76+(i%3)*96,286+(i//3)*34,88,o)
txt(210,390,"+ source role  + asset criticality",12,SUB,"middle","600")
arrow(360,325,410,325)
box(410,258,250,134,"#eef2f6","#5b6b7d","Rulebook  →  tier")
for i,(t,c) in enumerate([("OPERATIONAL","#3a8f5b"),("SENSITIVE","#c08a2b"),("FORBIDDEN","#b23b3b"),("CRITICAL = safety loop","#4a5568")]):
    txt(535,300+i*22,"•  "+t,12,c,"middle","600")
arrow(660,325,710,325)
box(710,258,210,134,"#fdeef0",ACC,"Criticality elevation",["SENSITIVE on a CRITICAL","asset → FORBIDDEN","(outside a maintenance window)"])
arrow(920,325,970,325)
box(970,240,170,180,"#eef2f6","#5b6b7d","Response ladder")
for i,r in enumerate(["ALLOW","MONITOR","THROTTLE","DEFLECT","ISOLATE","BLOCK","REFUSE"]):
    txt(1055,276+i*19,r,11.5,INK,"middle","700" if r in("ISOLATE","BLOCK","REFUSE") else "400")
# feedback arrow: response ladder -> Table 1 (install the chosen response)
P.append(f'<path d="M 1055 240 C 1055 205, 660 202, 545 184" fill="none" stroke="{ACC}" stroke-width="2.6" marker-end="url(#ah)"/>')
P.append('<rect x="608" y="191" width="250" height="21" rx="4" fill="white" opacity="0.92"/>')
txt(733,206,"install the response into Table 1",11.5,ACC,"middle","700")
txt(1055,442,"reactive rule, cookie 0x00ca",10.5,ACC,"middle","600")
txt(1055,456,"criticality-scaled self-heal",10.5,ACC,"middle","400")
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica">
<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="{LINE}"/></marker></defs>
<rect width="{W}" height="{H}" fill="white"/>
{"".join(P)}</svg>'''
open("/tmp/diagB.svg","w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to="/tmp/diagB.png",scale=2)
print("ok")
