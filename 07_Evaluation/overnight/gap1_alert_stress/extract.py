import ast, types, sys
SRC="/sessions/great-jolly-pasteur/mnt/Dissertation/Reactive_SDN_ICS/06_Build/cars_engine.py"
tree=ast.parse(open(SRC).read())
ns={'time':__import__('time')}
WANT_ASSIGN={"REGISTRY","RULEBOOK","CRITICALITY","CW","ESCALATE","FLOOD_RATE",
             "FLOOD_EXEMPT","BLOCK_TIMEOUT","THROTTLE_RATE","THROTTLE_BURST"}
WANT_FUNC={"role_of","crit_of","classify"}
# module-level assigns + safe funcs
for node in tree.body:
    if isinstance(node,ast.Assign):
        names={t.id for t in node.targets if isinstance(t,ast.Name)}
        if names & WANT_ASSIGN:
            exec(compile(ast.Module([node],[]),SRC,'exec'),ns)
    elif isinstance(node,ast.FunctionDef) and node.name in WANT_FUNC:
        exec(compile(ast.Module([node],[]),SRC,'exec'),ns)
    elif isinstance(node,ast.ClassDef) and node.name=="CARSEngine":
        for m in node.body:
            if isinstance(m,ast.FunctionDef) and m.name=="select_response":
                exec(compile(ast.Module([m],[]),SRC,'exec'),ns)
# faithful respond() DECISION block (elevation + flood + timeout), copied verbatim in logic
def decide(src,dst,op,rate=0.0,src_count=0,cnt=1,maint_until=0.0):
    classify=ns['classify']; crit_of=ns['crit_of']; CW=ns['CW']
    FLOOD_RATE=ns['FLOOD_RATE']; FLOOD_EXEMPT=ns['FLOOD_EXEMPT']; BLOCK_TIMEOUT=ns['BLOCK_TIMEOUT']
    sr=ns['select_response']
    import time as _t
    tier,s_role,d_role=classify(src,dst,op)
    acl=crit_of(dst); dcw=CW.get(acl,0); in_window=_t.time()<maint_until
    elevated=(tier=="SENSITIVE" and dcw>=3 and not in_window)
    if elevated: tier="FORBIDDEN"
    maint=in_window and ((tier=="FORBIDDEN" and op in ("CONTROL","DIAG","PROGRAM")) or (tier=="SENSITIVE" and dcw>=3))
    if maint: tier="OPERATIONAL"
    try: rate_f=float(rate) if rate is not None else 0.0
    except: rate_f=0.0
    flood=rate_f>=FLOOD_RATE and src not in FLOOD_EXEMPT
    state={"count":cnt}
    action=sr(None,tier,s_role,d_role,state,src_count,flood,dcw)
    timeout=BLOCK_TIMEOUT+dcw*15
    return {"tier":tier,"response":action,"timeout":timeout,"flood":flood,"elevated":elevated,"crit":acl}
ns['decide']=decide
if __name__=="__main__":
    d=ns['decide']
    # fidelity spot-check vs report's stated verdicts
    checks=[
      ("192.168.2.66","192.168.2.10","CONTROL",0,"FORBIDDEN","ISOLATE",75),  # attacker CONTROL crit -> isolate 75
      ("192.168.2.77","192.168.2.10","READ",0,"FORBIDDEN","ISOLATE",75),     # unknown outsider read
      ("192.168.2.31","192.168.2.10","WRITE",0,"FORBIDDEN","ISOLATE",75),    # scada write CRITICAL elevated->isolate
      ("192.168.2.31","192.168.2.20","WRITE",0,"SENSITIVE","THROTTLE",30),   # scada write LOW modbus -> throttle 30
      ("192.168.2.30","192.168.2.9","WRITE",0,"SENSITIVE","THROTTLE",60),    # historian write HIGH hmi1 -> throttle 60
      ("192.168.2.55","192.168.2.10","READ",0,"OPERATIONAL","ALLOW",75),     # EWS read HIL allowed
      ("192.168.2.55","192.168.2.10","CONTROL",50,"OPERATIONAL","ALLOW",75), # EWS high-rate flood-exempt -> ALLOW
      ("192.168.2.30","192.168.2.10","READ",50,"OPERATIONAL","BLOCK",75),    # historian read flood crit -> BLOCK
      ("192.168.2.31","192.168.2.20","READ",50,"OPERATIONAL","THROTTLE",30), # scada read flood LOW -> THROTTLE
    ]
    ok=0
    for src,dst,op,rate,et,er,eto in checks:
        r=d(src,dst,op,rate=rate)
        good = (r['tier']==et and r['response']==er and r['timeout']==eto)
        ok+=good
        print(("OK " if good else "XX ")+f"{src}->{dst} {op} r={rate}: got tier={r['tier']} resp={r['response']} to={r['timeout']} | want {et}/{er}/{eto}")
    print(f"\nFIDELITY: {ok}/{len(checks)} match report verdicts")
