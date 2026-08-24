#!/usr/bin/env python3
"""Mininet topology for the CARS emulation — the two-cell testbed in software.

Reproduces the testbed fabric: three Open vSwitch bridges (ovs1, ovsgw, ovs2)
under a single remote controller (the real os-ken CARS engine), OpenFlow 1.3,
with the same addressing as the hardware testbed so examples/site.testbed.yaml
applies unchanged. The gateway switch mirrors to a Snort host; the PLC hosts run
the software S7 and Modbus servers, the tank co-sim runs against PLC1.

REQUIRES a Linux host with root, Mininet and Open vSwitch. It cannot run in a
sandbox without kernel network namespaces. Bring the controller up first
(CARS_SITE=examples/site.testbed.yaml osken-manager ../06_Build/cars_engine.py),
then:  sudo python3 topo.py

Layout (see the report's Chapter 3 topology figure):
  ovs1 (Cell-1)  : PLC1 .2.10, HMI1 .2.9
  ovsgw (Gateway): SCADA .2.31, EWS .2.55, Historian .2.30, Modbus .2.20,
                   Snort mirror, attacker vantage .2.77
  ovs2 (Cell-2)  : PLC2 .3.10, HMI2 .3.9   (reached via the transit link)
"""
import os
import time

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

CONTROLLER = ("127.0.0.1", 6653)   # the os-ken CARS engine


def build():
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink, autoSetMacs=True)
    c0 = net.addController("c0", controller=RemoteController,
                           ip=CONTROLLER[0], port=CONTROLLER[1])

    ovs1 = net.addSwitch("ovs1", dpid="0000000000000001", protocols="OpenFlow13")
    ovsgw = net.addSwitch("ovsgw", dpid="0000000000000003", protocols="OpenFlow13")
    ovs2 = net.addSwitch("ovs2", dpid="0000000000000002", protocols="OpenFlow13")

    # Cell-1
    plc1 = net.addHost("plc1", ip="192.168.2.10/24")
    hmi1 = net.addHost("hmi1", ip="192.168.2.9/24")
    net.addLink(plc1, ovs1)
    net.addLink(hmi1, ovs1)

    # Gateway seams
    scada = net.addHost("scada", ip="192.168.2.31/24")
    ews = net.addHost("ews", ip="192.168.2.55/24")
    hist = net.addHost("hist", ip="192.168.2.30/24")
    mbplc = net.addHost("mbplc", ip="192.168.2.20/24")
    snort = net.addHost("snort", ip="192.168.2.250/24")
    atk = net.addHost("atk", ip="192.168.2.77/24")
    for h in (scada, ews, hist, mbplc, snort, atk):
        net.addLink(h, ovsgw)

    # Cell-2
    plc2 = net.addHost("plc2", ip="192.168.3.10/24")
    hmi2 = net.addHost("hmi2", ip="192.168.3.9/24")
    net.addLink(plc2, ovs2)
    net.addLink(hmi2, ovs2)

    # fabric: patch (ovs1<->ovsgw) and transit (ovsgw<->ovs2)
    net.addLink(ovs1, ovsgw)
    net.addLink(ovsgw, ovs2)

    net.build()
    c0.start()
    for s in (ovs1, ovsgw, ovs2):
        s.start([c0])

    # mirror all gateway traffic to the Snort host's port (SPAN), so the sensor
    # sees the same wire the testbed mirrored. (Adjust the mirror port to match
    # your snort interface; this is the OVS equivalent of the testbed p4 mirror.)
    snort_port = ovsgw.ports[[l for l in ovsgw.intfList() if l.link and snort in (l.link.intf1.node, l.link.intf2.node)][0]]
    ovsgw.cmd(f"ovs-vsctl -- --id=@p get port {snort.name}-eth0 "
              f"-- --id=@m create mirror name=carsmir select-all=true output-port=@p "
              f"-- set bridge ovsgw mirrors=@m")

    # auto-start the software PLCs and the tank co-sim on their hosts, so the
    # emulation is turnkey: the operator only has to launch an attack.
    #
    # CARS_SELF_PLANT: run the plant INSIDE the PLC (like a real CPU's ladder
    # logic) and do NOT start the external tank client. Then the only S7
    # write-var on the wire is an attack — required for the reactive DPI demo,
    # where an external legitimate control-write would itself trip the S7-CONTROL
    # rule. Default (unset) keeps the validated tank.py-driven proactive demo.
    self_plant = os.environ.get("CARS_SELF_PLANT", "") not in ("", "0", "false", "no")
    here = os.path.dirname(os.path.abspath(__file__))
    s7_env = "CARS_SELF_PLANT=1 " if self_plant else ""
    plc1.cmd(f"{s7_env}python3 {here}/plc/s7_server.py 192.168.2.10 > /tmp/cars_s7.log 2>&1 &")
    mbplc.cmd(f"python3 {here}/plc/modbus_server.py 192.168.2.20 > /tmp/cars_mb.log 2>&1 &")
    _wait = 2
    info(f"*** software PLCs launching (logs in /tmp/cars_*.log); waiting {_wait}s...\n")
    time.sleep(_wait)
    if self_plant:
        info("*** SELF-PLANT mode: the PLC runs the tank loop internally "
             "(process log: /tmp/cars_s7.log); no external tank client.\n")
    else:
        hist.cmd(f"python3 {here}/plc/tank.py --host 192.168.2.10 > /tmp/cars_tank.log 2>&1 &")

    info("*** CARS emulation up. The software PLCs and tank co-sim are running.\n")
    info("*** Confirm the controller is up (CARS_SITE=... osken-manager ../06_Build/cars_engine.py),\n")
    s7w = os.path.join(here, "..", "..", "06_Build", "s7_write.py")
    if self_plant:
        info("*** reactive DPI demo: start Snort + the bridge in a 2nd root terminal\n")
        info("      sudo -E env \"PATH=$PATH\" bash emulation/dpi.sh\n")
        info("*** then attack from an ALLOWLISTED host doing a FORBIDDEN op:\n")
        info(f"      scada python3 {s7w} --host 192.168.2.10 --count 5\n")
        info("*** first write leaks (allowlisted), then DPI -> 0x00ca ISOLATE on .2.31:\n")
        info("      sh ovs-ofctl -O OpenFlow13 dump-flows ovsgw | grep 0xca\n")
        info("*** and the process keeps running (see /tmp/cars_s7.log: interference stops).\n")
    else:
        info("*** then launch an attack from the Mininet CLI, e.g.:\n")
        info(f"      atk python3 {s7w} --host 192.168.2.10\n")
        info("*** the attacker is default-denied; see the drop:\n")
        info("      sh ovs-ofctl -O OpenFlow13 dump-flows ovs1 | grep 192.168.2.10   (priority=55 drop, n_packets>0)\n")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    build()
