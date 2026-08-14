import time, statistics, random, tempfile, os
import extract as E
d=E.ns['decide']
# re-validate with correct first-offence count=0
chk=d("192.168.2.30","192.168.2.9","WRITE",rate=0,cnt=0)
print("fidelity fix: historian->hmi1 WRITE first-offence =>",chk['tier'],chk['response'],chk['timeout'],"(expect SENSITIVE THROTTLE 60)")

# ---- diverse-flood corpus (defeats the 3s dedup: many distinct src/op) ----
srcs=[f"192.168.9.{i}" for i in range(1,201)]      # 200 distinct unregistered attackers
ops=["READ","WRITE","CONTROL","DIAG","PROGRAM","ILLEGAL"]
dsts=["192.168.2.10","192.168.2.9","192.168.2.20","192.168.3.10"]
def gen():
    return (random.choice(srcs),random.choice(dsts),random.choice(ops),random.choice([0,50]))

# ---- 1. pure decision compute latency ----
N=200000
lat=[]
for _ in range(N):
    s,ds,op,r=gen()
    t0=time.perf_counter(); d(s,ds,op,rate=r,cnt=0); lat.append((time.perf_counter()-t0)*1e6)
lat.sort()
def pc(p): return lat[int(p/100*(len(lat)-1))]
print("\n=== DECISION COMPUTE (per alert), N=%d ==="%N)
print("median %.2f us | p95 %.2f | p99 %.2f | max %.2f us"%(pc(50),pc(95),pc(99),pc(100)))
print("=> compute ceiling ~ %.0f k decisions/s on one core"%(1000/statistics.mean(lat)))

# ---- 2. decision + audit-log write (the real per-alert server cost) ----
tf=tempfile.NamedTemporaryFile('w',delete=False,dir='/sessions/great-jolly-pasteur/mnt/outputs/gap1_stress')
M=100000
t0=time.perf_counter()
for _ in range(M):
    s,ds,op,r=gen()
    res=d(s,ds,op,rate=r,cnt=0)
    tf.write("%s %s %s => %s\n"%(s,ds,op,res['response']))
tf.flush(); os.fsync(tf.fileno())
el=time.perf_counter()-t0
tf.close()
print("\n=== DECISION + AUDIT WRITE, M=%d ==="%M)
print("elapsed %.3fs | sustained %.0f alerts/s (one core, decision+log)"%(el, M/el))

# ---- 3. dedup bound + queueing model ----
print("\n=== WHAT AN ATTACKER CAN ACTUALLY OFFER ===")
print("identical-alert flood: capped by COOLDOWN=3s dedup -> <= 1 POST / (src,dst,op) / 3s")
svc=M/el
print("diverse-alert flood: offered load hits the decision+log stage; service rate ~%.0f/s"%svc)
for off in [100,1000,5000,10000,int(svc*0.9),int(svc*1.5)]:
    rho=off/svc
    if rho<1:
        wq=(rho/(1-rho))*(1e6/svc)   # M/M/1 mean wait, us
        print("  offered %6d/s: rho=%.2f -> mean added queue wait ~%.2f ms"%(off,rho,wq/1000))
    else:
        print("  offered %6d/s: rho=%.2f -> UNSTABLE (queue grows without bound; backlog)"%(off,rho))
