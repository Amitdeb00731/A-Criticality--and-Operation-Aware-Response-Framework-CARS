# Diagram C: detection-to-response cycle with self-heal (refines the old detresp 3.12).
import cairosvg
INK="#1f2d3d"; SUB="#5b6b7d"; LINE="#3a4a5c"
ATK="#b23b3b"; SNORT="#8a4fb0"; BR="#c9922b"; CTRL="#2f6db0"; ENF="#3a8f5b"; HEAL="#2f8f8f"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
P=[]
def box(x,y,w,h,fill,stroke,title,subs=None,tsize=13):
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    P.append(f'<text x="{x+w/2}" y="{y+22}" text-anchor="middle" font-family="Helvetica" font-size="{tsize}" font-weight="700" fill="{INK}">{esc(title)}</text>')
    if subs:
        for i,s in enumerate(subs):
            P.append(f'<text x="{x+w/2}" y="{y+40+i*15}" text-anchor="middle" font-family="Helvetica" font-size="11" fill="{INK}">{esc(s)}</text>')
def arrow(x1,y1,x2,y2,col=LINE,w=2.2,dash="",label=None):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    P.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"{d} marker-end="url(#ah)"/>')
    if label: P.append(f'<text x="{(x1+x2)/2}" y="{y1-8}" text-anchor="middle" font-family="Helvetica" font-size="10.5" fill="{SUB}">{esc(label)}</text>')
def txt(x,y,s,size=11,col=INK,anchor="middle",weight="400",style=""):
    st=f' font-style="{style}"' if style else ""
    P.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Helvetica" font-size="{size}" font-weight="{weight}" fill="{col}"{st}>{esc(s)}</text>')
W,H=1180,470
txt(60,40,"Detection to response, and self-heal",18,INK,"start","700")
y=110; h=88
box(50,y,170,h,"#fdeef0",ATK,"Attacker frame",["crosses the fabric,","copied to the mirror"])
arrow(220,y+h/2,270,y+h/2)
box(270,y,180,h,"#f2ebf7",SNORT,"Snort DPI",["recovers the operation,","writes an alert"])
arrow(450,y+h/2,500,y+h/2)
box(500,y,180,h,"#fbf1dc",BR,"Bridge",["tails the alert, posts","to /cars/respond"])
arrow(680,y+h/2,730,y+h/2)
box(730,y,200,h,"#eaf1f9",CTRL,"Controller decides",["rulebook + criticality","→ response  (~0.03 ms)"])
arrow(930,y+h/2,980,y+h/2)
box(980,y,150,h,"#e8f5ee",ENF,"Switch enforces",["installs 0x00ca rule,","drops or meters"])
# wire-to-enforcement timing
txt(590,y-16,"wire to enforcement: median 7.6 ms",11.5,SUB,"middle","600","italic")
# self-heal loop-back from enforce to switch (dashed teal)
P.append(f'<path d="M 1055 {y+h} C 1055 320, 700 340, 640 340 C 560 340, 300 340, 250 {y+h}" fill="none" stroke="{HEAL}" stroke-width="2.2" stroke-dasharray="6 4" marker-end="url(#ah)"/>')
txt(650,356,"hard_timeout expiry → the rule is removed and the source forgiven (self-heal, unless the attack renews it)",11.5,HEAL,"middle","600","italic")
# flow-integrity self-check watching the tables (dashed, above enforce)
box(980,y-64,150,44,"#eef2f6","#5b6b7d","Flow-integrity check",None)
P.append(f'<line x1="1055" y1="{y-20}" x2="1055" y2="{y}" stroke="#5b6b7d" stroke-width="1.6" stroke-dasharray="4 3"/>')
txt(1055,y-70,"",10)
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica">
<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="{LINE}"/></marker></defs>
<rect width="{W}" height="{H}" fill="white"/>{"".join(P)}</svg>'''
open("/tmp/diagC.svg","w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to="/tmp/diagC.png",scale=2)
print("C ok")
