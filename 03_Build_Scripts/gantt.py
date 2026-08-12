import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

fig, ax = plt.subplots(figsize=(11,4.6))
C = {"read":"#2E5496","build":"#9C5700","cars":"#1F3864","eval":"#1E7145","write":"#7030A0","buf":"#999999"}
# rows top->bottom
rows = [
 ("Reading (deep: Ph0-2 + safety)", [(0,2,"read"),(2,2,"read")], [0.9]),
 ("Testbed build (Ph A-C, incl. zones)", [(0,4,"build")], [1.0]),
 ("CARS contribution (Ph D)", [(2,2,"cars")], [1.0]),
 ("Attack suite + evaluation (Ph E)", [(3,2,"eval")], [1.0]),
 ("Writing (skeleton -> chapters)", [(0,6,"write")], [1.0]),
 ("Polish + buffer + submit", [(5,1,"buf")], [1.0]),
]
h=0.62
yl=[]
for i,(name,bars,alphas) in enumerate(rows):
    y=len(rows)-i-1
    yl.append((y,name))
    for (start,dur,key),a in zip(bars,[0.55,1.0][:len(bars)] if len(bars)>1 else [1.0]):
        ax.broken_barh([(start,dur)],(y-h/2,h),facecolors=C[bars[bars.index((start,dur,key))][2]] if False else C[key],alpha=a,edgecolor="white")
# simpler: redo bars cleanly
ax.clear()
for i,(name,bars,_) in enumerate(rows):
    y=len(rows)-i-1
    for j,(start,dur,key) in enumerate(bars):
        a = 0.5 if (name.startswith("Reading") and j==1) else (0.55 if name.startswith("Writing") and start==0 else 1.0)
        # writing: light W1-4, heavy W4-6 -> draw two
    # custom per row below
# manual draw
def bar(y,s,d,key,a=1.0,label=None):
    ax.broken_barh([(s,d)],(y-h/2,h),facecolors=C[key],alpha=a,edgecolor="white")
    if label: ax.text(s+d/2,y,label,ha="center",va="center",color="white",fontsize=8,fontweight="bold")
names=["Reading (deep)","Testbed build (Ph A–C)","CARS contribution (Ph D)","Attack + evaluation (Ph E)","Writing","Polish + buffer"]
ys=list(range(len(names)-1,-1,-1))
bar(ys[0],0,2,"read",1.0,"Ph0–2"); bar(ys[0],2,2,"read",0.45,"safety")
bar(ys[1],0,4,"build",1.0,"A → B → C")
bar(ys[2],2,2,"cars",1.0,"engine")
bar(ys[3],3,2,"eval",1.0,"scenarios+metrics")
bar(ys[4],0,4,"write",0.45,"skeleton+lit"); bar(ys[4],4,2,"write",1.0,"chapters")
bar(ys[5],5,1,"buf",1.0,"submit")
# milestones
for x,txt,col in [(2,"Wk-2 checkpoint\n(de-scope fidelity if behind)","#C00000"),(4,"Wk-4 gate\n(writing underway)","#C00000"),(6,"Submit","#1E7145")]:
    ax.axvline(x,color=col,ls="--",lw=1.4,alpha=0.8)
    ax.text(x,len(names)-0.25,txt,ha="center",va="bottom",fontsize=7.5,color=col,fontweight="bold")
ax.set_yticks(ys); ax.set_yticklabels(names,fontsize=9)
ax.set_xticks(range(0,7)); ax.set_xticklabels(["W1","W2","W3","W4","W5","W6",""],fontsize=9)
ax.set_xlim(0,6.2); ax.set_ylim(-0.6,len(names)+0.2)
ax.set_xlabel("Week",fontsize=9)
ax.set_title("CARS — 6-Week Execution Plan (workstreams run in parallel; writing starts Week 1)",fontsize=11,fontweight="bold")
ax.grid(axis="x",ls=":",alpha=0.4)
for s in ["top","right","left"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("gantt.png",dpi=150,bbox_inches="tight")
print("gantt ok")
