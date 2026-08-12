const fs = require('fs');
const d = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
        TableCell, WidthType, BorderStyle, ShadingType, ImageRun, PageBreak, TableOfContents, Footer } = d;

const CW = 9360;
const ACCENT = "1F4E79", GREY = "595959", HEAD = "D6E4F0";
const MONO = "Consolas";

const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 260, after: 120 },
  children: [new TextRun({ text: t, bold: true, color: ACCENT, size: 30 })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 180, after: 90 },
  children: [new TextRun({ text: t, bold: true, color: "2E5E8C", size: 25 })] });
const P = (runs, opts={}) => new Paragraph({ spacing: { after: 120, line: 276 }, ...opts,
  children: Array.isArray(runs) ? runs : [new TextRun({ text: runs, size: 21 })] });
const T = (text, o={}) => new TextRun({ text, size: 21, ...o });
const CODE = (text) => new TextRun({ text, font: MONO, size: 19, color: "B03A2E" });
const bullet = (runs) => new Paragraph({ bullet: { level: 0 }, spacing: { after: 60, line: 264 },
  children: Array.isArray(runs) ? runs : [new TextRun({ text: runs, size: 21 })] });

function cell(text, { w, bold=false, shade=null, mono=false, color=null, size=19, align=null } = {}) {
  const runs = (Array.isArray(text) ? text : [text]).map((t, i) =>
    new TextRun({ text: t, bold, size, font: mono ? MONO : undefined, color: color||undefined, break: i>0?1:0 }));
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    shading: shade ? { type: ShadingType.CLEAR, fill: shade } : undefined,
    children: [new Paragraph({ alignment: align||undefined, children: runs })],
  });
}
function table(widths, rows) {
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: widths,
    borders: {
      top:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"}, bottom:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"},
      left:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"}, right:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"},
      insideHorizontal:{style:BorderStyle.SINGLE,size:4,color:"D9E1EA"}, insideVertical:{style:BorderStyle.SINGLE,size:4,color:"D9E1EA"},
    },
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri===0,
      children: r.map((c, ci) => cell(c.t, { w: widths[ci], bold: ri===0 || c.bold, shade: ri===0 ? HEAD : (c.shade||null),
        mono: c.mono, color: c.color, align: c.align })),
    })),
  });
}
const spacer = () => new Paragraph({ spacing:{after:60}, children:[new TextRun({text:""})] });
const kids = [];

kids.push(new Paragraph({ spacing:{before:1400, after:60}, alignment: AlignmentType.CENTER,
  children:[new TextRun({ text:"Project CARS", bold:true, color:ACCENT, size:56 })]}));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:40},
  children:[new TextRun({ text:"Criticality-Aware Response System", color:"2E5E8C", size:30, italics:true })]}));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:300},
  children:[new TextRun({ text:"Reactive SDN for Securing ICS Environments", color:GREY, size:26 })]}));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, border:{top:{style:BorderStyle.SINGLE,size:6,color:ACCENT}}, spacing:{before:120}}));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{before:200, after:40},
  children:[new TextRun({ text:"Progress Report for Supervisor", bold:true, size:28 })]}));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:600},
  children:[new TextRun({ text:"Testbed · Implementation · Reactive Loop · Hardening · Evaluation", color:GREY, size:20 })]}));
const meta = (l,v)=> new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:40},
  children:[new TextRun({text:l+"  ",color:GREY,size:20}), new TextRun({text:v,bold:true,size:20})]});
kids.push(meta("Author:","Amit Kiran Deb"));
kids.push(meta("Programme:","MSc Cyber Security · University of Bristol"));
kids.push(meta("Group / Supervisor:","Bristol Cyber Security Group · Joe Gardiner"));
kids.push(meta("Status as of:","13 July 2026"));
kids.push(new Paragraph({ children:[new PageBreak()] }));

kids.push(H1("Contents"));
kids.push(new TableOfContents("Contents", { hyperlink:true, headingStyleRange:"1-2" }));
kids.push(new Paragraph({ children:[new PageBreak()] }));

kids.push(H1("Executive summary"));
kids.push(P([T("This report documents the current state of "), T("Project CARS",{bold:true}),
  T(" — a reactive Software-Defined Networking (SDN) defence for Industrial Control Systems (ICS). The system consumes intrusion-detection events and enforces "),
  T("criticality-aware network responses that are safe by construction",{bold:true}),
  T(" on a live testbed built around real Siemens hardware, so an operator could enable automated response without risking the physical process.")]));
kids.push(P([T("Research contribution, in one line:  ",{bold:true,color:ACCENT}),
  T("a "),T("safety-constrained, criticality-aware reactive response",{bold:true}),
  T(" — a network defence that mitigates threats automatically yet is "),
  T("structurally forbidden from severing the safety-critical control loop",{bold:true}),
  T(", so automated response can be trusted in a live process.")]));
kids.push(P([T("The testbed is fully built and operational: two real Siemens S7-1200 PLCs with HMI panels, a three-switch Open vSwitch SDN fabric, an out-of-band SDN controller running the CARS trust brain, a virtualised IT/DMZ periphery in GNS3, and a Snort IDS wired into the controller to form a closed detect-decide-enforce loop. The reactive loop has been demonstrated end-to-end against both an external (IT to OT) attacker and an on-plane insider.")]));
kids.push(P([T("Beyond the working prototype, the system has been "),T("security-hardened and independently audited",{bold:true}),
  T(", and its response latency has been "),T("quantitatively evaluated",{bold:true}),
  T(". Headline result: the CARS controller decides and enforces a mitigation in "),
  T("0.61 ms (sub-millisecond)",{bold:true,color:"1E7E34"}),
  T("; the end-to-end mean-time-to-mitigate of ~1.13 s is dominated (~99.95%) by the off-the-shelf detector, not the controller.")]));
kids.push(spacer());
kids.push(table([2600,6760],[
  [{t:"Dimension"},{t:"Where the project stands today"}],
  [{t:"Physical testbed",bold:true},{t:"Complete — 2x real Siemens S7-1200 + HMI, 3x Dell hosts, MikroTik control plane, USB-Ethernet OT links."}],
  [{t:"SDN fabric",bold:true},{t:"3x Open vSwitch (spine-leaf) under one os-ken/Ryu controller; out-of-band control plane."}],
  [{t:"Contribution",bold:true},{t:"Conduit-criticality trust brain — working autonomously; the safety invariant is demonstrated on hardware."}],
  [{t:"Reactive loop",bold:true},{t:"Closed for external + insider attacks (Snort to bridge to brain to block)."}],
  [{t:"Hardening",bold:true},{t:"Data-plane anti-spoofing (IP+ARP), fail-secure, live discovery; independent code audit passed."}],
  [{t:"Evaluation",bold:true},{t:"MTTM measured — CARS response sub-ms; end-to-end sensor-bounded."}],
]));

kids.push(H1("1. How the testbed was built"));
kids.push(P([T("The testbed follows a "),T("Purdue-model / IEC 62443 zones-and-conduits",{bold:true}),
  T(" architecture and was built incrementally, fidelity-first, on real hardware rather than pure simulation — a deliberate choice so findings reflect genuine ICS behaviour (e.g. PLC boot-time ARP probes, multi-homed-host ARP flux) that a simulator would never surface.")]));
kids.push(H2("Build philosophy"));
kids.push(bullet([T("Real over simulated: ",{bold:true}), T("two physical Siemens S7-1200 PLCs, each driving a real SIMATIC HMI panel, provide authentic process behaviour; nothing about the control loop is emulated.")]));
kids.push(bullet([T("SDN as a zone-boundary overlay: ",{bold:true}), T("Open vSwitch is inserted as the controllable fabric between the process cells and the supervisory/IT world — brownfield-friendly, no change to the PLC programs.")]));
kids.push(bullet([T("Out-of-band control: ",{bold:true}), T("the SDN controller programs the switches over a separate management network, never sitting in the data path.")]));
kids.push(bullet([T("One role per machine: ",{bold:true}), T("clean separation of data plane, control plane, and virtual periphery for clarity and safety.")]));
kids.push(H2("Build stages (chronological)"));
kids.push(table([900,8460],[
  [{t:"Stage",w:900},{t:"What was done",w:8460}],
  [{t:"Base",w:900,bold:true},{t:"Ubuntu + Open vSwitch 3.3.4 on the OT host; os-ken 2.8.1 (maintained Ryu fork) controller in a Python venv on the pure controller host; static out-of-band management IPs (10.10.10.0/24) over a MikroTik hAP.",w:8460}],
  [{t:"Real OT",w:900,bold:true},{t:"Both teaching boxes (PLC+HMI) attached to OVS access ports via USB-Ethernet adapters; each PLC-HMI control loop verified through the switch.",w:8460}],
  [{t:"Fabric",w:900,bold:true},{t:"Three OVS bridges created — two cell leaf switches (ovs1, ovs2) and a gateway spine (ovsgw) — all pointed at the single controller; the gateway carries the supervisory host, the IDS mirror, the GNS3 seam, and the insider foothold.",w:8460}],
  [{t:"Periphery",w:900,bold:true},{t:"GNS3 project (cars-killchain) provides the virtual IT attacker, Enterprise firewall, DMZ/jump host and OT firewall (NAT), joined to the OT plane through an internal seam port; Docker hosts the SCADA (FUXA) and Historian (InfluxDB + Grafana).",w:8460}],
  [{t:"IDS",w:900,bold:true},{t:"An OVS mirror on the gateway copies all gateway traffic to a sink port where Snort listens; a bridge script forwards Snort alerts to the controller — closing the reactive loop.",w:8460}],
  [{t:"Harden",w:900,bold:true},{t:"Two-table data-plane source-guard, fail-secure switching, ARP-flux fix, clean-slate-on-connect discovery, and an independent code audit.",w:8460}],
  [{t:"Evaluate",w:900,bold:true},{t:"Instrumented the controller and built a measurement harness for mean-time-to-mitigate (MTTM).",w:8460}],
]));

kids.push(H1("2. How the equipment is connected"));
kids.push(P([T("Three physical planes are kept strictly separate: the "),T("OT data plane",{bold:true}),
  T(" (real process traffic through OVS), the "),T("SDN control plane",{bold:true}),
  T(" (out-of-band, controller to switches), and "),T("management / Internet",{bold:true}),T(".")]));
kids.push(H2("Physical links"));
kids.push(table([3400,3200,2760],[
  [{t:"Link",w:3400},{t:"From",w:3200},{t:"To",w:2760}],
  [{t:"OT data — Box1 PLC",w:3400},{t:"S7-1200 -> USB-Eth adapter",w:3200},{t:"Dell #1 -> ovs1 port 1",w:2760}],
  [{t:"OT data — Box1 HMI",w:3400},{t:"HMI panel -> USB-Eth adapter",w:3200},{t:"Dell #1 -> ovs1 port 2",w:2760}],
  [{t:"OT data — Box2 PLC",w:3400},{t:"S7-1200 -> USB-Eth adapter",w:3200},{t:"Dell #3 -> ovs2 port 1",w:2760}],
  [{t:"OT data — Box2 HMI",w:3400},{t:"HMI panel -> USB-Eth adapter",w:3200},{t:"Dell #3 -> ovs2 port 2",w:2760}],
  [{t:"Fabric (virtual)",w:3400},{t:"ovs1 port 3 (OVS patch)",w:3200},{t:"ovsgw port 1 (OVS patch)",w:2760}],
  [{t:"Control plane",w:3400},{t:"Dell #1 / #2 / #3 RJ45",w:3200},{t:"MikroTik hAP (VLAN1)",w:2760}],
]));
kids.push(P([T("Note: ovs1-ovsgw is an internal OVS "),T("patch",{italics:true}),
  T(" (virtual link inside Dell #1). Cell 2 (ovs2) is currently "),T("isolated",{bold:true}),
  T(" from the gateway fabric — the physical transit (P4) is deliberately deferred, see Section 12.")]));
kids.push(H2("Address plan"));
kids.push(table([2900,2900,3560],[
  [{t:"Plane / zone",w:2900},{t:"Subnet",w:2900},{t:"Key hosts",w:3560}],
  [{t:"OT data plane (L0-L2)",w:2900},{t:"192.168.2.0/24",w:2900,mono:true},{t:"PLC .10, HMI .9, Supervisory .30, Insider .66, OT-FW .1",w:3560}],
  [{t:"SDN control (out-of-band)",w:2900},{t:"10.10.10.0/24",w:2900,mono:true},{t:"Controller .1, Dell#1 .2, Dell#3 .3",w:3560}],
  [{t:"Enterprise IT (GNS3)",w:2900},{t:"10.0.40.0/24",w:2900,mono:true},{t:"IT attacker .66, corporate",w:3560}],
  [{t:"Industrial DMZ (GNS3)",w:2900},{t:"172.16.35.0/24",w:2900,mono:true},{t:"Jump / historian-replica .10",w:3560}],
]));

kids.push(H1("3. What the topology looks like"));
kids.push(P([T("The logical topology is a "),T("spine-leaf SDN fabric",{bold:true}),
  T(" mapped onto the Purdue model. Two process cells (each a PLC+HMI control loop) hang off leaf switches; a gateway switch is the OT boundary and the single enforcement point, carrying the supervisory host and the IDS mirror. Above the gateway sits the virtual IT/DMZ periphery (in GNS3). The SDN controller programs all three switches out-of-band.")]));
try {
  const img = fs.readFileSync('/sessions/great-jolly-pasteur/mnt/Dissertation/Reactive_SDN_ICS/06_Build/final_it_ot_subnet_topology.png');
  kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{before:80,after:60},
    children:[ new ImageRun({ type:"png", data: img, transformation:{ width:470, height:360 } }) ]}));
  kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:160},
    children:[new TextRun({ text:"Figure 1 — IT/OT topology, top-to-bottom, with subnets and the SDN enforcement point.", italics:true, color:GREY, size:18 })]}));
} catch(e) { kids.push(P("[topology figure unavailable]")); }
kids.push(H2("Discovered fabric (ground truth, from the live controller)"));
kids.push(table([1500,1500,6360],[
  [{t:"Switch",w:1500},{t:"dpid",w:1500},{t:"Ports -> what is attached",w:6360}],
  [{t:"ovs1 (Cell 1)",w:1500,bold:true},{t:"1",w:1500,mono:true},{t:"p1=PLC1, p2=HMI1, p3=uplink patch to ovsgw",w:6360}],
  [{t:"ovsgw (gateway/spine)",w:1500,bold:true},{t:"3",w:1500,mono:true},{t:"p1=patch to ovs1, p2=it0 (GNS3 seam), p3=sup0 (supervisory), p4=snort0 (IDS mirror sink), p5=att0 (insider)",w:6360}],
  [{t:"ovs2 (Cell 2)",w:1500,bold:true},{t:"2",w:1500,mono:true},{t:"p1=PLC2, p2=HMI2 (isolated — no fabric uplink yet)",w:6360}],
]));

kids.push(H1("4. Which component acts as what"));
kids.push(table([2350,3050,3960],[
  [{t:"Component",w:2350},{t:"Role",w:3050},{t:"Notes",w:3960}],
  [{t:"Dell #1",w:2350,bold:true},{t:"OT data plane + gateway + services",w:3050},{t:"Runs ovs1 + ovsgw, GNS3, Docker (SCADA/Historian), Snort, and the dashboard. Control IP .2.",w:3960}],
  [{t:"Dell #2",w:2350,bold:true},{t:"SDN controller (pure)",w:3050},{t:"os-ken/Ryu — the CARS brain. Nothing else runs here (isolated from attackers). Control IP .1; OpenFlow :6653, Event API :8080.",w:3960}],
  [{t:"Dell #3",w:2350,bold:true},{t:"OT Cell 2",w:3050},{t:"Runs ovs2 (PLC2 + HMI2). Control IP .3.",w:3960}],
  [{t:"2x S7-1200 + HMI",w:2350,bold:true},{t:"Real process (L0/L1/L2)",w:3050},{t:"The assets CARS protects; the PLC-HMI loop is the safety-critical conduit.",w:3960}],
  [{t:"MikroTik hAP",w:2350,bold:true},{t:"Control-plane switch",w:3050},{t:"Dumb L2 for the out-of-band management network; not the SDN fabric.",w:3960}],
  [{t:"sup0 (192.168.2.30)",w:2350,bold:true},{t:"Supervisory (Historian/SCADA)",w:3050},{t:"OVS internal port on the gateway; a trusted operational conduit to the PLCs.",w:3960}],
  [{t:"att0 (192.168.2.66)",w:2350,bold:true},{t:"Insider attacker",w:3050},{t:"On-plane foothold used to model a compromised OT host / insider.",w:3960}],
  [{t:"GNS3 periphery",w:2350,bold:true},{t:"IT attacker + firewalls + DMZ",w:3050},{t:"External IT-to-OT kill chain; OT-FW SNATs to .1 on the OT plane.",w:3960}],
  [{t:"Snort",w:2350,bold:true},{t:"Intrusion detection",w:3050},{t:"Off-the-shelf IDS on the gateway mirror; the detection source for CARS.",w:3960}],
]));

kids.push(H1("5 & 6. Scripts — role, host, and what each creates"));
kids.push(P([T("Every piece of the system is a small, purpose-built script. The table gives the role; the paragraphs say where each runs and what it produces.")]));
kids.push(table([2350,1450,5560],[
  [{t:"Script / file",w:2350},{t:"Runs on",w:1450},{t:"Role",w:5560}],
  [{t:"cars_engine.py",w:2350,bold:true,mono:true},{t:"Dell #2",w:1450},{t:"The CARS controller — trust brain + data-plane source-guard + live discovery + Event API.",w:5560}],
  [{t:"snort_bridge.py",w:2350,bold:true,mono:true},{t:"Dell #1",w:1450},{t:"IDS-to-CARS bridge — tails Snort alerts and reports flows to the brain.",w:5560}],
  [{t:"cars_dashboard.py",w:2350,bold:true,mono:true},{t:"Dell #1",w:1450},{t:"Live NOC dashboard — discovered topology, link health, guard telemetry, decision feed.",w:5560}],
  [{t:"mttm.py",w:2350,bold:true,mono:true},{t:"Dell #1",w:1450},{t:"Evaluation harness — measures mean-time-to-mitigate over many trials.",w:5560}],
  [{t:"cars.conf + cars.rules",w:2350,bold:true,mono:true},{t:"Dell #1",w:1450},{t:"Snort configuration and the CARS detection signatures.",w:5560}],
  [{t:"cars-seams.service",w:2350,bold:true,mono:true},{t:"Dell #1",w:1450},{t:"systemd unit — restores the seam-port IPs (sup0/att0) at boot.",w:5560}],
  [{t:"99-cars-arp.conf",w:2350,bold:true,mono:true},{t:"Dell #1",w:1450},{t:"sysctl — stops multi-homed-host ARP flux (arp_ignore/announce).",w:5560}],
]));
kids.push(H2("cars_engine.py — the controller (Dell #2)"));
kids.push(P([T("Launched with "),CODE("osken-manager --observe-links ~/cars/cars_engine.py"),
  T(". An OpenFlow 1.3 application on os-ken (the maintained Ryu fork). It "),T("creates",{bold:true}),
  T(": (a) a two-table flow pipeline on every switch (Table 0 = source-guard, Table 1 = L2 switching + enforcement); (b) an HTTP "),T("Event API",{bold:true}),
  T(" on :8080 ("),CODE("/cars/respond, /status, /hosts, /ports, /links, /guard, /block, /unblock, /restore"),
  T("); (c) a passive host/link "),T("discovery",{bold:true}),T(" model; and (d) an append-only "),T("audit log",{bold:true}),T(" of every decision.")]));
kids.push(H2("snort_bridge.py — the detection coupling (Dell #1)"));
kids.push(P([T("Runs "),CODE("tail -F"),T(" on Snort's alert file, parses each alert into "),CODE("(src, dst, proto)"),
  T(", and HTTP-POSTs it to the controller's "),CODE("/cars/respond"),
  T(". It contains no policy of its own — the brain decides. It creates the live coupling that turns detections into decisions.")]));
kids.push(H2("cars_dashboard.py — the live NOC (Dell #1)"));
kids.push(P([T("A threaded HTTP server on :8090 that serves a single-page live view and proxies the controller's API (no CORS issues; the browser never touches the control plane). It "),
  T("creates",{bold:true}),T(" a force-directed, discovery-driven topology with per-link port bindings, real-time link-health (a link turns red the instant its port drops), a source-guard drop counter, and a dated decision feed — refreshed every 1.2 s.")]));
kids.push(H2("mttm.py — the evaluation harness (Dell #1)"));
kids.push(P([T("Repeats an attack-mitigate cycle (restore, launch attack, poll until the block appears), timing everything on one clock, and writes "),
  CODE("~/mttm_results.csv"),T(" plus summary statistics.")]));

kids.push(H1("7. How the reactive loop was created"));
kids.push(P([T("The reactive loop was assembled from four decoupled stages, each independently testable, so detection, decision, and enforcement are cleanly separated (deliberate, so any detector can be swapped in).")]));
kids.push(bullet([T("1. Sense. ",{bold:true}), T("An OVS mirror on the gateway (ovsgw) copies all boundary traffic to a sink port (snort0); Snort listens there and raises an alert when a suspicious flow to a protected asset is seen.")]));
kids.push(bullet([T("2. Report. ",{bold:true}), T("snort_bridge.py tails the alert file and POSTs the offending flow to the controller's Event API — turning a text alert into a structured event.")]));
kids.push(bullet([T("3. Decide. ",{bold:true}), T("The controller's trust brain classifies the flow by its conduit criticality (Section 8) and chooses an action — block, allow, or refuse-to-block.")]));
kids.push(bullet([T("4. Enforce. ",{bold:true}), T("If block, the controller installs a drop rule on every switch so the offending conduit is severed wherever it lives; if allow, nothing changes; if the flow is the safety-critical loop, the block is refused.")]));
kids.push(P([T("The loop runs "),T("autonomously — no human in the path",{bold:true}),
  T(". A parallel, always-on "),T("data-plane source-guard",{bold:true}),
  T(" sits in front of the brain and drops spoofed traffic before it can ever be classified, so an attacker cannot impersonate a trusted host to fool the decision.")]));

kids.push(H1("8. Mitigation flow and current rules"));
kids.push(H2("The trust brain — conduit-criticality policy"));
kids.push(P([T("Criticality is a property of the "),T("conduit",{bold:true}),
  T(" (source-role to destination-role to service), not of a device. The brain maps each flow to one of four tiers and acts accordingly:")]));
kids.push(table([1900,4260,3200],[
  [{t:"Tier",w:1900},{t:"When",w:4260},{t:"Action",w:3200}],
  [{t:"CRITICAL",w:1900,bold:true,color:"9C6500"},{t:"The real PLC-HMI control loop",w:4260},{t:"REFUSE to block (safety invariant) — mirror/alert only",w:3200,shade:"FFF6E5"}],
  [{t:"FORBIDDEN",w:1900,bold:true,color:"B03A2E"},{t:"Unknown / external / gateway to PLC or HMI",w:4260},{t:"BLOCK on sight",w:3200,shade:"FDECEA"}],
  [{t:"SENSITIVE",w:1900,bold:true,color:"9C6500"},{t:"Engineering station (EWS) to PLC/HMI",w:4260},{t:"Block on anomaly (designed; no EWS deployed yet)",w:3200,shade:"FFF6E5"}],
  [{t:"OPERATIONAL",w:1900,bold:true,color:"1E7E34"},{t:"Supervisory (Historian/SCADA) to PLC/HMI",w:4260},{t:"ALLOW — monitor only",w:3200,shade:"EAF6EC"}],
]));
kids.push(P([T("The "),T("safety invariant",{bold:true}),
  T(" is the heart of the contribution: CARS is structurally "),T("incapable",{italics:true}),
  T(" of severing the legitimate control loop — verified on hardware (a block request for the loop returns refused).")]));
kids.push(H2("The source-guard — data-plane anti-spoofing (Table 0)"));
kids.push(P([T("Before traffic reaches the switching/decision logic, Table 0 validates its identity against a fixed binding table (verified from the live switches):")]));
kids.push(bullet([T("Each protected host is bound to an exact "),CODE("(switch, port, MAC, IP)"),T(" tuple; matching IP "),T("and",{italics:true}),T(" ARP traffic is allowed through.")]));
kids.push(bullet([T("Any packet claiming a protected IP (.10 / .9 / .30) from the wrong port or MAC — an "),T("impersonation attempt",{italics:true}),T(" — is dropped at ingress, at both L3 (IP) and L2 (ARP).")]));
kids.push(P([T("So an attacker cannot forge the supervisor's address to be waved through, nor forge the HMI's address to steal the CRITICAL never-block shield — both were tested and dropped.")]));
kids.push(H2("Current detection rules (Snort)"));
kids.push(table([5400,1800,2160],[
  [{t:"Signature",w:5400},{t:"Protocol",w:1800},{t:"SID",w:2160}],
  [{t:"Any to PLC1 (192.168.2.10)",w:5400},{t:"ICMP",w:1800,mono:true},{t:"1000001",w:2160,mono:true}],
  [{t:"Any to HMI1 (192.168.2.9)",w:5400},{t:"ICMP",w:1800,mono:true},{t:"1000002",w:2160,mono:true}],
  [{t:"Any to PLC1 (TCP SYN)",w:5400},{t:"TCP",w:1800,mono:true},{t:"1000003",w:2160,mono:true}],
  [{t:"Any to HMI1 (TCP SYN)",w:5400},{t:"TCP",w:1800,mono:true},{t:"1000004",w:2160,mono:true}],
]));
kids.push(P([T("Snort casts a wide net (any source to a protected asset); the "),T("brain",{bold:true}),
  T(" does the intelligent filtering — e.g. it "),T("allows",{italics:true}),
  T(" the supervisor to the same PLC while "),T("blocking",{italics:true}),T(" an unknown host, from identical detections.")]));

kids.push(H1("9. Security hardening (a major achievement block)"));
kids.push(P([T("After the prototype worked, a dedicated hardening pass made it defensible. Each item was staged carefully, verified on hardware, and recorded in the decision log.")]));
kids.push(table([2650,6710],[
  [{t:"Hardening",w:2650},{t:"What it does / result",w:6710}],
  [{t:"Anti-spoofing (IP + ARP)",w:2650,bold:true},{t:"Two-table source-guard drops forged identities at ingress — verified: forged .30 and .9 dropped.",w:6710}],
  [{t:"Safety-invariant hardening",w:2650,bold:true},{t:"The CRITICAL never-block shield can no longer be stolen by impersonating the loop.",w:6710}],
  [{t:"Fail-secure",w:2650,bold:true},{t:"On controller loss the fabric keeps its rules (no fail-open); a broadcast-flood rule keeps ARP/loops alive during an outage — verified with the controller killed.",w:6710}],
  [{t:"Clean discovery",w:2650,bold:true},{t:"Fixed ARP-flux; clean-slate-on-reconnect so discovery re-learns hosts after a restart.",w:6710}],
  [{t:"Per-cell enforcement",w:2650,bold:true},{t:"Blocks install on every switch, so they reach an isolated Cell 2, not just the gateway.",w:6710}],
  [{t:"Independent audit",w:2650,bold:true},{t:"A skeptical code review validated the core design; findings were fixed or explicitly scoped as documented limitations.",w:6710}],
]));

kids.push(H1("10. Evaluation — mitigation latency (MTTM)"));
kids.push(P([T("Mean-time-to-mitigate was measured on the insider path over 20 attack-block cycles, timed on a single clock to avoid cross-machine skew. The controller was also instrumented to time its own decide-and-enforce path.")]));
kids.push(table([4680,2340,2340],[
  [{t:"Metric",w:4680},{t:"Value",w:2340},{t:"Detail",w:2340}],
  [{t:"CARS decide + enforce (controller)",w:4680,bold:true},{t:"0.613 ms",w:2340,bold:true,color:"1E7E34"},{t:"sub-ms · n=21",w:2340}],
  [{t:"End-to-end MTTM (mean)",w:4680},{t:"1.132 s",w:2340,mono:true},{t:"median 1.127 s",w:2340}],
  [{t:"End-to-end MTTM (best case)",w:4680},{t:"0.139 s",w:2340,mono:true},{t:"min over 20",w:2340}],
  [{t:"CARS share of end-to-end",w:4680,bold:true},{t:"~0.05 %",w:2340,bold:true},{t:"~99.95% is the IDS",w:2340}],
]));
kids.push(P([T("Interpretation: ",{bold:true}),
  T("the reactive SDN response layer is effectively instantaneous; the end-to-end mitigation time is bounded by the off-the-shelf detector (Snort's internal buffering), not by CARS. This was proven by tightening the bridge poll — which moved the best case to 48 ms but left the mean unchanged, pinning the residual latency upstream in the sensor. Paired with a faster detector, the sub-millisecond controller keeps up.")]));

kids.push(H1("11. Impactful goals achieved to date"));
kids.push(bullet([T("A working real-hardware ICS testbed ",{bold:true}), T("(2x Siemens S7-1200 + HMI) with a 3-switch SDN fabric and out-of-band control.")]));
kids.push(bullet([T("The core contribution is implemented and works autonomously ",{bold:true}), T("— a conduit-criticality trust brain that makes intelligent, role-aware decisions with no human in the loop.")]));
kids.push(bullet([T("The safety property is demonstrated on hardware (safe by construction) ",{bold:true}), T("— CARS refuses to sever the legitimate PLC-HMI control loop; the one residual (the brain trusts detector-reported identities) is documented in Section 12.")]));
kids.push(bullet([T("The reactive loop is closed end-to-end ",{bold:true}), T("for both an external (IT-to-OT) attacker and an on-plane insider — attacks are detected, decided, and blocked automatically, with no human in the loop.")]));
kids.push(bullet([T("True data-plane defence ",{bold:true}), T("— IP + ARP source-guard makes host impersonation infeasible for on-plane (access-port) attackers; forged identities are dropped at ingress.")]));
kids.push(bullet([T("Real hardware earned its keep ",{bold:true}), T("— genuine ICS faults a simulator would never show (multi-homed ARP flux, PLC boot-time ARP probes, identical-cell clone IPs) surfaced during the build, and each became a hardening improvement.")]));
kids.push(bullet([T("Resilience ",{bold:true}), T("— the system fails secure and keeps the process running through a controller outage.")]));
kids.push(bullet([T("Independently audited ",{bold:true}), T("— the design survived a skeptical review; issues were fixed or honestly scoped.")]));
kids.push(bullet([T("Live discovery + NOC dashboard ",{bold:true}), T("— the whole IT/OT space is visualised in real time from the controller's own view.")]));
kids.push(bullet([T("Quantitative evaluation ",{bold:true}), T("— sub-millisecond controller response, with a clean CARS-vs-sensor latency breakdown.")]));

kids.push(H1("12. Remaining work — what to know"));
kids.push(H2("Planned next steps"));
kids.push(bullet([T("P4 transit: ",{bold:true}), T("wire Cell 2 (ovs2) into the gateway fabric — but harden the uplink source-guard first (see limitation below), so joining Cell 2 does not open a spoofing path.")]));
kids.push(bullet([T("Cell-2 detection: ",{bold:true}), T("add a mirror/sensor for Cell 2 so it is detected, not just enforceable (the IDS mirror currently covers only the gateway).")]));
kids.push(bullet([T("External-path MTTM: ",{bold:true}), T("script the GNS3 attacker to measure the IT-to-OT path over many trials for a like-for-like latency figure.")]));
kids.push(bullet([T("Sensor tuning: ",{bold:true}), T("tune Snort's buffering to lower the end-to-end MTTM for a CARS-plus-tuned-sensor figure.")]));
kids.push(bullet([T("Write-up: ",{bold:true}), T("the contribution, hardening, and evaluation chapters assemble from the decision log (28 recorded decisions).")]));
kids.push(H2("Known limitations (documented honestly, not defects)"));
kids.push(bullet([T("Anti-spoofing is scoped to access-port attackers: ",{bold:true}), T("the uplink-trust must be hardened before the physical Cell-2 transit is added.")]));
kids.push(bullet([T("SENSITIVE/EWS tier is designed but not deployed ",{bold:true}), T("(no engineering station on the plane yet).")]));
kids.push(bullet([T("The brain trusts detector-reported IPs; ",{bold:true}), T("a cross-check against the binding table is future work.")]));
kids.push(bullet([T("A controller restart momentarily lifts active blocks ",{bold:true}), T("(the reactive loop re-establishes them); persisting blocks is future work.")]));
kids.push(bullet([T("The external NAT makes an IT-origin block coarse ",{bold:true}), T("(all IT-to-PLC traffic arrives as .1); acceptable in this testbed.")]));
kids.push(spacer());
kids.push(P([T("All decisions, numbers, and rationale are locked in the project's decision log ("),
  CODE("DECISION_LOG.md"),T(", entries CC-1 to CC-28), build log, refreshed cold-start runbook, and the MTTM evaluation record — the record is complete and reproducible.")]));

const doc = new Document({
  creator: "Amit Kiran Deb",
  title: "Project CARS — Progress Report",
  styles: { default: { document: { run: { font: "Calibri", size: 21 } } } },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1200, bottom: 1100, left: 1200, right: 1200 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ text: "Project CARS — Reactive SDN for ICS · Progress Report · Amit Kiran Deb", size: 16, color: GREY }) ] }) ] }) },
    children: kids,
  }],
});
Packer.toBuffer(doc).then(b => {
  fs.writeFileSync('/sessions/great-jolly-pasteur/mnt/Dissertation/Reactive_SDN_ICS/07_Evaluation/CARS_Progress_Report.docx', b);
  console.log('written bytes:', b.length);
});
