# Figure 3.4 - a malicious write's path, armed vs disarmed (generic, no testbed names/cookie)
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig,ax=plt.subplots(figsize=(11,5.4),dpi=150); ax.set_xlim(0,100); ax.set_ylim(0,55); ax.axis("off")
TX="#1f2933"
RED_F="#f8d5cd"; RED_E="#c0392b"; AMB_F="#fde9c8"; AMB_E="#d79b00"
GRN_F="#d5e8d4"; GRN_E="#82b366"; BLU_F="#dae8fc"; BLU_E="#6c8ebf"
GRY_F="#eef0f2"; GRY_E="#b6bcc2"
def box(x,y,w,h,fc,ec,label,tcol=TX,lw=1.8,r=2.0,fs=11):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.02,rounding_size={r}",fc=fc,ec=ec,lw=lw,mutation_aspect=0.6))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=fs,color=tcol)
def arrow(x1,y,x2,color=RED_E,dashed=False,lw=2.4):
    ax.add_patch(FancyArrowPatch((x1,y),(x2,y),arrowstyle="-|>",mutation_scale=16,lw=lw,color=color,
                 linestyle=(0,(4,3)) if dashed else "solid"))
def alabel(xc,y,s,col=TX): ax.text(xc,y+2.4,s,ha="center",va="center",fontsize=9,color=col,style="italic")

# ---- Row 1: DISARMED ----
y=36; h=11
ax.text(4,50,"DISARMED (unprotected)",fontsize=12.5,weight="bold",color=RED_E,ha="left")
box(4,y,18,h,RED_F,RED_E,"Attacker")
arrow(22,y+h/2,30); alabel(26,y+h/2,"malicious write")
box(30,y,22,h,AMB_F,AMB_E,"CARS fabric\n(conduit passes)")
arrow(52,y+h/2,60)
box(60,y,16,h,BLU_F,BLU_E,"Critical PLC")
arrow(76,y+h/2,84)
box(84,y,14,h,RED_F,RED_E,"Process\nunsafe state",tcol=RED_E)

# ---- Row 2: ARMED ----
y=8
ax.text(4,22,"ARMED (CARS)",fontsize=12.5,weight="bold",color=GRN_E,ha="left")
box(4,y,18,h,RED_F,RED_E,"Attacker")
arrow(22,y+h/2,30); alabel(26,y+h/2,"malicious write")
box(30,y,22,h,GRN_F,GRN_E,"CARS fabric\nISOLATE (drop)")
# X + dropped
ax.text(55.5,y+h/2,"✗",ha="center",va="center",fontsize=20,color=RED_E,weight="bold")
ax.text(55.5,y-1.5,"dropped",ha="center",va="center",fontsize=9,color=RED_E,style="italic")
arrow(58,y+h/2,66,color=GRY_E,dashed=True,lw=1.8)
box(66,y,16,h,GRY_F,GRY_E,"Critical PLC",tcol="#8a9096")
box(84,y,14,h,GRN_F,GRN_E,"Process\nheld",tcol=GRN_E)

plt.tight_layout()
plt.savefig("flow_armed_vs_disarmed.png",dpi=150,bbox_inches="tight",facecolor="white")
print("saved flow_armed_vs_disarmed.png")
