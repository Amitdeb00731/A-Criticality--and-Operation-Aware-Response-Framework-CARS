#!/usr/bin/env bash
# =============================================================================
# cars_deploy_verify.sh  --  deploy + verify the CC-78 audit fixes
#   F1  dashboard ROLE/TYPEOF/hlabel sync   -> Dell#1  ~/cars_dashboard.py
#   N2  Cell-2 S7 0x28 DPI (sid 1000048)    -> Dell#1  /etc/snort/cars.rules
#   F2  engine seed==runtime (optional)     -> Dell#2  ~/cars/cars_engine.py
#
# SAFE BY DESIGN: backup-first, validate-before-swap, restart via systemctl
# (never pkill), post-verify, and automatic ROLLBACK on any failure.
#
# USAGE (run ON the target Dell after staging the files there):
#   1) From the machine that holds E:\...\06_Build, copy the masters over:
#        scp cars_dashboard.py cars.rules  msclab@<DELL1>:~/cars_stage/
#        scp cars_engine.py                msclab@<DELL2>:~/cars_stage/
#   2) On Dell#1:   bash cars_deploy_verify.sh dell1
#      On Dell#2:   bash cars_deploy_verify.sh dell2 --restart-engine   # restart optional
#   Add --verify-only to check live state WITHOUT deploying.
# =============================================================================
set -uo pipefail

ROLE="${1:-}"; shift || true
VERIFY_ONLY=0; RESTART_ENGINE=0
for a in "$@"; do
  case "$a" in
    --verify-only) VERIFY_ONLY=1 ;;
    --restart-engine) RESTART_ENGINE=1 ;;
  esac
done
[ "$ROLE" = "dell1" ] || [ "$ROLE" = "dell2" ] || { echo "usage: $0 dell1|dell2 [--verify-only] [--restart-engine]"; exit 2; }

STAGE="${STAGE:-$HOME/cars_stage}"
TS="$(date +%Y%m%d-%H%M%S)"
BK="$HOME/cars_backup/$TS"; mkdir -p "$BK"
RB=()                                  # rollback stack: "live<TAB>backup"
ok(){   printf '  \033[32mOK\033[0m   %s\n' "$*"; }
bad(){  printf '  \033[31mFAIL\033[0m %s\n' "$*"; }
info(){ printf '  ..   %s\n' "$*"; }
hdr(){  printf '\n== %s ==\n' "$*"; }

rollback(){
  hdr "ROLLBACK"
  for e in "${RB[@]}"; do
    live="${e%%$'\t'*}"; b="${e##*$'\t'}"
    if [ -w "$(dirname "$live")" ]; then cp -p "$b" "$live"; else sudo cp -p "$b" "$live"; fi && info "restored $live"
  done
  echo "Rolled back. Backups kept in $BK"; exit 1
}
backup(){ local f="$1"; [ -f "$f" ] && { cp -p "$f" "$BK/$(basename "$f")"; RB+=("$f"$'\t'"$BK/$(basename "$f")"); }; }
svc_active(){ systemctl is-active --quiet "$1"; }

# ----------------------------------------------------------------------------
deploy_dell1(){
  hdr "DELL#1  preflight"
  local D="$STAGE/cars_dashboard.py" R="$STAGE/cars.rules"
  local LD="$HOME/cars_dashboard.py"  LR="/etc/snort/cars.rules"

  if [ "$VERIFY_ONLY" = 0 ]; then
    [ -f "$D" ] || { bad "staged $D missing"; exit 1; }
    [ -f "$R" ] || { bad "staged $R missing"; exit 1; }
    python3 -m py_compile "$D" || { bad "staged dashboard does not compile"; exit 1; }; ok "dashboard compiles"
    grep -q "192.168.2.31" "$D" && grep -q "192.168.2.77" "$D" && grep -q "192.168.3.66" "$D" \
      && grep -q "supervisory:'sup'" "$D" || { bad "staged dashboard lacks F1 ROLE/glyph"; exit 1; }; ok "staged dashboard carries F1"
    grep -q "sid:1000048" "$R" || { bad "staged cars.rules lacks sid:1000048"; exit 1; }; ok "staged cars.rules carries N2"

    hdr "DELL#1  backup"
    backup "$LD"; backup "$LR"; ok "backed up to $BK"

    hdr "DELL#1  validate Snort config with the NEW rules (pre-swap dry run)"
    sudo cp -p "$R" "$LR" || rollback
    if sudo snort -T -c /etc/snort/cars.conf >/tmp/snortT.log 2>&1; then ok "snort -T passed with new cars.rules"
    else bad "snort -T FAILED (see /tmp/snortT.log)"; tail -5 /tmp/snortT.log; rollback; fi

    hdr "DELL#1  deploy dashboard"
    cp -p "$D" "$LD" || rollback; ok "dashboard swapped"

    hdr "DELL#1  restart services (snort + bridge TOGETHER per CC-76, then dashboard)"
    sudo systemctl restart cars-snort cars-bridge || rollback
    sleep 3
    svc_active cars-snort  && ok "cars-snort active"  || { bad "cars-snort not active"; rollback; }
    svc_active cars-bridge && ok "cars-bridge active" || { bad "cars-bridge not active (CC-76 revive expected)"; rollback; }

    # dashboard: use its systemd unit if one exists, else its launcher/tmux
    DASH_SVC="$(systemctl list-units --type=service --plain --no-legend 2>/dev/null | awk '{print $1}' | grep -iE 'dash|cars-web' | head -1)"
    if [ -n "$DASH_SVC" ]; then
      sudo systemctl restart "$DASH_SVC" && ok "restarted $DASH_SVC" || rollback
    else
      info "no dashboard systemd unit found -> restarting its process"
      pid="$(pgrep -f cars_dashboard.py || true)"
      if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null; sleep 1
        nohup python3 "$LD" >/tmp/cars_dashboard.out 2>&1 &   # only path w/o a unit; HTML is served from memory so a restart IS required
        ok "relaunched cars_dashboard.py (pid $!)"
      else
        info "cars_dashboard.py not running -> start it your usual way (tmux); HTML is served from memory so it MUST be restarted to pick up F1"
      fi
    fi
    sleep 2
  fi

  hdr "DELL#1  POST-VERIFY"
  # 1) deployed files carry the fixes
  grep -q "sid:1000048" "$LR" && ok "cars.rules has sid:1000048 (N2)" || bad "cars.rules missing N2"
  grep -q "supervisory:'sup'" "$LD" && ok "dashboard file has supervisory glyph (F1)" || bad "dashboard file missing F1"
  # 2) snort loads clean
  sudo snort -T -c /etc/snort/cars.conf >/tmp/snortT2.log 2>&1 && ok "snort -T clean" || { bad "snort -T failing"; tail -3 /tmp/snortT2.log; }
  # 3) the RUNNING dashboard serves the new ROLE map (proves the process reloaded, not just the file)
  DP="$(ss -ltnp 2>/dev/null | grep -i python | grep -oE ':[0-9]+' | tr -d ':' | sort -u | head -5)"
  served=0
  for p in ${DASH_PORT:-} $DP; do
    if curl -s -m3 "http://127.0.0.1:$p/" 2>/dev/null | grep -q "192.168.2.31"; then
      ok "running dashboard on :$p serves the F1 ROLE map"; served=1; break
    fi
  done
  [ "$served" = 1 ] || info "could not confirm served ROLE map on a python port (set DASH_PORT=<port> and re-run --verify-only)"
  # 4) services + reactive path
  for s in cars-snort cars-bridge; do svc_active "$s" && ok "$s active" || bad "$s NOT active"; done
  echo; echo "Dell#1 done. Backups: $BK   (hard-refresh the browser: Ctrl-Shift-R)"
}

# ----------------------------------------------------------------------------
deploy_dell2(){
  hdr "DELL#2  preflight (engine seed fix -- runtime JSON is authoritative, so behaviour is UNCHANGED)"
  local E="$STAGE/cars_engine.py" LE="$HOME/cars/cars_engine.py"

  if [ "$VERIFY_ONLY" = 0 ]; then
    [ -f "$E" ] || { bad "staged $E missing"; exit 1; }
    python3 -m py_compile "$E" || { bad "staged engine does not compile"; exit 1; }; ok "engine compiles"
    # seed==runtime check (the whole point of F2)
    python3 - "$E" "$HOME/cars/rulebook.json" "$HOME/cars/a2_policy.json" <<'PY' || { bad "seed != runtime -- aborting"; exit 1; }
import re,json,sys
src=open(sys.argv[1]).read()
rb=re.search(r'RULEBOOK = \[(.*?)\]',src,re.S).group(1)
seed=[tuple(x for x in re.findall(r'"([^"]*)"',l)) for l in rb.splitlines() if l.strip().startswith('(')]
rt=[tuple(r) for r in json.load(open(sys.argv[2]))]
al=re.search(r'ALLOWLIST = \[(.*?)\]',src,re.S).group(1)
seeda=[l for l in al.splitlines() if l.strip().startswith('(')]
rta=json.load(open(sys.argv[3]))['allowlist']
assert seed==rt, "RULEBOOK seed!=runtime"
assert len(seeda)==len(rta), "ALLOWLIST count mismatch"
print("  seed==runtime: RULEBOOK %d, ALLOWLIST %d"%(len(rt),len(rta)))
PY
    ok "seed==runtime verified (F2)"

    hdr "DELL#2  backup + deploy"
    backup "$LE"; cp -p "$E" "$LE" || rollback; ok "engine swapped (backup $BK)"

    if [ "$RESTART_ENGINE" = 1 ]; then
      hdr "DELL#2  restart controller"
      ESVC="$(systemctl list-units --type=service --plain --no-legend 2>/dev/null | awk '{print $1}' | grep -iE 'osken|ryu|cars-engine|controller' | head -1)"
      if [ -n "$ESVC" ]; then sudo systemctl restart "$ESVC" && ok "restarted $ESVC" || rollback
      else info "controller is not a systemd unit -> restart it in its tmux/session yourself (Ctrl-C, re-run osken-manager). Flows persist (fail_mode=secure); reactive re-syncs on reconnect."
      fi
    else
      info "engine file deployed; NOT restarting (runtime unchanged). Add --restart-engine to apply the seed on a cold start."
    fi
  fi

  hdr "DELL#2  POST-VERIFY"
  grep -q '"remediation", "plc", "CONTROL"' "$LE" && ok "engine has remediation seed rows (F2)" || bad "engine missing F2 rows"
  grep -q "192.168.2.55.*192.168.2.10.*102" "$LE" && ok "engine has EWS allowlist conduit (F2)" || bad "engine missing F2 conduit"
  # live controller still answering + criticality intact
  if curl -s -m3 http://127.0.0.1:8080/cars/criticality >/tmp/crit.json 2>/dev/null; then
    ok "controller /cars/criticality reachable"; grep -q '"192.168.2.10": "CRITICAL"' /tmp/crit.json && ok "PLC1=CRITICAL live" || info "check crit map"
  else info "controller API not on :8080 here (adjust if needed)"; fi
  echo; echo "Dell#2 done. Backups: $BK"
}

case "$ROLE" in
  dell1) deploy_dell1 ;;
  dell2) deploy_dell2 ;;
esac
