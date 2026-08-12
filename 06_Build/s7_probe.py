#!/usr/bin/env python3
# CARS A3/P5 — SAFE S7CommPlus session probe (attacker vantage).
# Opens one TCP connection to the real PLC :102 and sends a single packet carrying the
# S7CommPlus signature (TPKT 03 00 .. + COTP DT 02 f0 80 + proto-id 0x72). It is an INVALID
# COTP DT (no CR/CC handshake), so the PLC's transport layer discards it — no S7 session, no
# reads, no writes: the physical process is never touched. Purpose = put the S7CommPlus
# signature on the wire so Snort detects an unauthorized S7 session to the PLC and CARS responds.
import socket, sys
host = sys.argv[1] if len(sys.argv) > 1 else "192.168.2.10"
# 03 00 00 12  02 f0 80  72  ...   -> "03 00" at offset 0, "72" (S7CommPlus) at offset 7
pdu = bytes.fromhex("0300001202f08072") + b"\x01\x00\x00\x00\x00\xcc\xcc"
s = socket.socket(); s.settimeout(2)
try:
    s.connect((host, 102))
    s.sendall(pdu)
    print("[s7_probe] sent S7CommPlus-signature packet to %s:102" % host)
    try:
        r = s.recv(64); print("[s7_probe] resp:", r[:16].hex() if r else "(none)")
    except Exception:
        print("[s7_probe] no response (blocked / discarded)")
except OSError as e:
    print("[s7_probe] connect/send FAILED (conduit blocked?):", e)
finally:
    s.close()
