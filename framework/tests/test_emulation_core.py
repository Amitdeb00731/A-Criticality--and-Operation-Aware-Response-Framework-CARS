"""Headless integration test for the emulation's process core.

Runs without root, Mininet or Snort: it starts the software S7 PLC, exercises a
real S7comm round-trip, runs the tank co-simulation against it, and confirms an
attacker write reaches the actuator (the CONTROL op CARS would isolate). This is
the part of the emulation that can be validated in CI; the SDN fabric needs a
Linux+root host and is covered by emulation/topo.py.
"""
import os
import socket
import subprocess
import sys
import time

import pytest

snap7 = pytest.importorskip("snap7")  # skip cleanly if the native lib is absent

HERE = os.path.dirname(os.path.abspath(__file__))
PLC = os.path.join(os.path.dirname(HERE), "emulation", "plc")
HOST, PORT = "127.0.0.1", 11102

try:
    from snap7.type import Area
    PA = Area.PA
except Exception:
    PA = 0x82
RELAY = 0x08


def _wait_port(host, port, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


@pytest.fixture()
def plc_server():
    p = subprocess.Popen([sys.executable, os.path.join(PLC, "s7_server.py"), HOST, str(PORT)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if not _wait_port(HOST, PORT):
        p.kill()
        pytest.fail("s7_server did not come up")
    yield
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()


def _client():
    c = snap7.client.Client()
    c.connect(HOST, 0, 1, tcp_port=PORT)
    return c


def test_s7_roundtrip(plc_server):
    c = _client()
    assert c.get_connected()
    c.write_area(PA, 0, 0, bytearray([RELAY]))
    assert c.read_area(PA, 0, 0, 1)[0] & RELAY, "pump should read ON after write"
    c.write_area(PA, 0, 0, bytearray([0x00]))
    assert not c.read_area(PA, 0, 0, 1)[0] & RELAY, "pump should read off after write"
    c.disconnect()


def test_tank_loop_runs(plc_server):
    """The tank co-sim should drive the level and toggle the pump over a short run."""
    # run tank for ~3s then stop it
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(PLC, "tank.py"),
         "--host", HOST, "--tcp-port", str(PORT), "--dt", "0.2"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(3)
    p.terminate()
    out = p.stdout.read()
    assert "process online" in out, out
    lines = [l for l in out.splitlines() if "level=" in l]
    assert len(lines) >= 5, f"expected several control cycles, got:\n{out}"
    assert "pump=ON" in out and "pump=off" in out, "pump should toggle across the run"


def test_attacker_write_lands(plc_server):
    """A rogue S7 write reaches the relay — the CONTROL op CARS classifies FORBIDDEN."""
    c = _client()
    c.write_area(PA, 0, 0, bytearray([RELAY]))
    assert c.read_area(PA, 0, 0, 1)[0] & RELAY
    c.disconnect()
