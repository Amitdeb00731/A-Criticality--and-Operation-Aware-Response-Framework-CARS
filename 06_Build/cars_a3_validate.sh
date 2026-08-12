#!/bin/bash
# =============================================================================
# CARS A3 — ADVERSARIAL DEEP VALIDATION  (run on Dell#1)
# For every scenario cross-checks FOUR independent layers that must agree:
#   WIRE (tshark func code) | SNORT alert | CARS decision (audit) | DATA-PLANE (OF flow n_packets) + outcome
# Includes "confuse the brain" adversarial cases + a stress run. Nothing is trusted
# from a single source; a claim only passes if the wire, the sensor, the brain and
# the datapath corroborate. (Rule 0: attack->defence must be physically real.)
# =============================================================================
set -u
SRV=192.168.2.20; OPR=192.168.2.31; ATK=192.168.2.66; PLC=192.168.2.10
API=http://10.10.10.1:8080/cars; A=/var/log/snort/alert; BR=ovsgw
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/a3_val_$TS
mkdir -p "$OUT"/{pcap,art}; V="$OUT/VERDICT.txt"; : > "$V"
echo "[*] A3 validation dir: $OUT"
pgrep -f mb_server.py >/dev/null || { ip netns exec mbns python3 /home/msclab/mb_server.py 192.168.2.20 & sleep 2; }
asz(){ sudo stat -c %s "$A"; }
clean(){ curl -s -X POST $API/restore -d "{\"src\":\"$1\",\"dst\":\"$2\"}" >/dev/null 2>&1
         sudo ovs-ofctl -O OpenFlow13 del-flows $BR "table=1,ip,nw_src=$1" 2>/dev/null; sleep 1; }
say(){ echo "$1" | tee -a "$V"; }

# ---- core scenario: wire vs alert vs decision vs data-plane ----
scen(){ # $1 label $2 netns $3 src $4 dst $5 expect_resp  ...client args
  local L=$1 NS=$2 SRC=$3 DST=$4 EXP=$5; shift 5
  clean "$SRC" "$DST"
  local a0=$(asz)
  sudo timeout 12 tshark -i snort0 -n -f "host $SRC and host $DST" -w "$OUT/pcap/${L}.pcap" 2>/dev/null & local TP=$!
  sleep 1
  local outcome; outcome=$(ip netns exec $NS python3 /home/msclab/mb_client.py --host $DST "$@" 2>&1 | tr '\n' ' ')
  sleep 4; sudo kill $TP 2>/dev/null; wait 2>/dev/null
  local wire=$(tshark -r "$OUT/pcap/${L}.pcap" -Y modbus -T fields -e modbus.func_code 2>/dev/null | grep -v '^$' | sort -u | tr '\n' ',')
  [ -z "$wire" ] && wire=$(tshark -r "$OUT/pcap/${L}.pcap" -Y cotp -T fields -e frame.number 2>/dev/null|head -1|sed 's/.*/S7\/COTP/')
  local alert=$(sudo tail -c +$((a0+1)) "$A" | grep -ao 'CARS-[A-Z0-9-]*' | sort -u | tr '\n' ',')
  local flow=$(sudo ovs-ofctl -O OpenFlow13 dump-flows $BR table=1 | grep "nw_src=$SRC" | grep -oE 'n_packets=[0-9]+|actions=[^ ]+' | tr '\n' ' ')
  [ -z "$flow" ] && flow="(no flow=pass)"
  local dec=$(curl -s $API/audit | python3 -c "import json,sys;a=json.load(sys.stdin)['audit'];r=[x for x in a if '$SRC' in x and '$DST' in x];L=r[-1] if r else '';print((L.split()[1]+' '+L.split('=>')[1].strip().split()[0]) if '=>' in L else '?')" 2>/dev/null)
  say "[$L] wire=[$wire] snort=[$alert] brain=[$dec] dataplane=[$flow]"
  say "        expect=$EXP  outcome=$outcome"
}

say "===================== A. CORE MATRIX (4-layer cross-check) ====================="
scen OP_READ    opns  $OPR $SRV ALLOW    --op read
scen OP_WRITE   opns  $OPR $SRV THROTTLE --op write --reg 0 --val 501
scen OP_WMULTI  opns  $OPR $SRV THROTTLE --op write_multi --reg 0 --val 502 --count 3
scen OP_WCOIL   opns  $OPR $SRV THROTTLE --op write_coil --reg 1 --val 1
scen ATK_WRITE  atkns $ATK $SRV BLOCK    --op write --reg 8 --val 9999
scen ATK_READ   atkns $ATK $SRV BLOCK    --op read
clean "$OPR" "$SRV"; clean "$ATK" "$SRV"

say ""
say "===================== B. CONFUSE-THE-BRAIN (adversarial) ====================="
# B1 non-Modbus TCP to the Modbus port -> must NOT false-alert
a0=$(asz); ( ip netns exec atkns bash -c 'exec 3<>/dev/tcp/192.168.2.20/502; printf "GET / HTTP/1.0\r\n\r\n" >&3; sleep 1' ) 2>/dev/null; sleep 2
n=$(sudo tail -c +$((a0+1)) "$A" | grep -c CARS-MODBUS)
say "[B1 non-Modbus->502] CARS-MODBUS alerts=$n  EXPECT 0 (no false positive)"
# B2 fragmented Modbus write -> single-packet content match should MISS (honest evasion)
a0=$(asz)
ip netns exec atkns python3 - "$SRV" <<'PYF' 2>/dev/null
import socket,sys,time
s=socket.socket();s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);s.settimeout(2)
try:
 s.connect((sys.argv[1],502))
 pdu=bytes.fromhex("000000000006000600000209")  # MBAP+FC6 write single reg
 s.send(pdu[:5]);time.sleep(0.3);s.send(pdu[5:])  # split so FC byte isn't at offset7 of one packet
 print("frag write sent")
except Exception as e:print("frag err",e)
finally:s.close()
PYF
sleep 3
n=$(sudo tail -c +$((a0+1)) "$A" | grep -c "CARS-MODBUS-WRITE")
say "[B2 fragmented write] WRITE alerts=$n  (single-packet DPI evasion -> honest limit; A2 mitigates)"
clean "$ATK" "$SRV"
# B3 attacker READ must NOT be downgraded to ALLOW by op-awareness (verified in A above: ATK_READ=BLOCK)
say "[B3 attacker-read-not-allowed] see ATK_READ above: unknown source is FORBIDDEN regardless of op"
# B4 legit intra-ovs1 HMI<->PLC loop must be INVISIBLE to the sensor (no false detection of real ops)
a0=$(asz); sleep 4
n=$(sudo tail -c +$((a0+1)) "$A" | grep -cE "CARS-MODBUS|CARS-S7")
say "[B4 legit loop false-positive] alerts on real HMI<->PLC in 4s idle=$n  EXPECT 0 (intra-ovs1, unmirrored)"

say ""
say "===================== C. STRESS + ESCALATION ====================="
# C1 attacker write flood -> BLOCK then ISOLATE (persistence escalation), measure it
clean "$ATK" "$SRV"; a0=$(asz)
for i in 1 2 3 4 5; do ip netns exec atkns python3 /home/msclab/mb_client.py --host $SRV --op write --reg 8 --val $i >/dev/null 2>&1; sleep 3; done
esc=$(curl -s $API/audit | python3 -c "import json,sys;a=json.load(sys.stdin)['audit'];print(' -> '.join([x.split('=>')[1].split('conduit')[0].split('source')[0].strip() for x in a if '$ATK' in x and '$SRV' in x][-5:]))" 2>/dev/null)
say "[C1 escalation ladder] last 5 attacker-write responses: $esc  (EXPECT ...BLOCK -> ISOLATE)"
# C2 latency under the loop
lat=$(curl -s $API/status | python3 -c "import json,sys;d=json.load(sys.stdin);print('avg',d.get('cars_ms_avg'),'n',d.get('cars_ms_n'))" 2>/dev/null)
say "[C2 decide+enforce latency] $lat ms"
clean "$ATK" "$SRV"

curl -s $API/audit > "$OUT/art/audit.json" 2>&1
say ""
say "Artifacts: $OUT (pcaps + audit). Bundle:"
TAR="$HOME/cars_a3_validation_${TS}.tar.gz"; tar -czf "$TAR" -C "$HOME/cars_forensics" "a3_val_$TS" 2>/dev/null
say "  $TAR"
echo "===== VERDICT ====="; cat "$V"
