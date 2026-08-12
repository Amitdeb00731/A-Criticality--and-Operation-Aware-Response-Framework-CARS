const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageNumber,
  Header, Footer, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  LevelFormat, ImageRun,
} = require("docx");

const ACCENT="1F3864", ACCENT2="2E5496", GREY="595959", GREEN="1E7145", RED="9C1F2E", AMBER="9C5700";

const h1=(t)=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:320,after:120},children:[new TextRun({text:t,bold:true,color:ACCENT,size:30})]});
const h2=(t)=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:220,after:80},children:[new TextRun({text:t,bold:true,color:ACCENT2,size:25})]});
function p(runs,opts={}){const children=Array.isArray(runs)?runs:[new TextRun({text:runs,size:22})];return new Paragraph({alignment:AlignmentType.JUSTIFIED,spacing:{after:130,line:274},children,...opts});}
const t=(text,o={})=>new TextRun({text,size:22,...o});
function bullet(runs,level=0){const children=Array.isArray(runs)?runs:[new TextRun({text:runs,size:22})];return new Paragraph({numbering:{reference:"b",level},alignment:AlignmentType.JUSTIFIED,spacing:{after:70,line:268},children});}

function table(cols, header, data, headFill=ACCENT) {
  function cell(text,{bold=false,fill,head=false,color}={},w){
    const runs = Array.isArray(text) ? text : [new TextRun({text,bold,size:18,color:head?"FFFFFF":(color||"000000")})];
    return new TableCell({width:{size:w,type:WidthType.DXA},shading:fill?{type:ShadingType.CLEAR,fill}:undefined,
      margins:{top:55,bottom:55,left:85,right:85},children:[new Paragraph({spacing:{after:0},children:runs})]});
  }
  const rows=[new TableRow({tableHeader:true,children:header.map((h,i)=>cell(h,{bold:true,fill:headFill,head:true},cols[i]))})];
  data.forEach((r,idx)=>{const fill=idx%2?"EDF1F8":"FFFFFF";rows.push(new TableRow({children:r.map((c,i)=>cell(c,{fill},cols[i]))}));});
  return new Table({columnWidths:cols,width:{size:cols.reduce((a,b)=>a+b,0),type:WidthType.DXA},
    borders:{top:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},bottom:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},
      left:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},right:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},
      insideHorizontal:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"},insideVertical:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"}},rows});
}

const c=[];

// Title
c.push(new Paragraph({spacing:{before:260}}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:50},children:[new TextRun({text:"Phased Testbed Build Plan",bold:true,size:38,color:ACCENT})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},children:[new TextRun({text:"Reactive SDN for Securing ICS Environments — Project CARS",size:24,color:ACCENT2,italics:true})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,border:{top:{style:BorderStyle.SINGLE,size:6,color:ACCENT}},spacing:{after:40},children:[new TextRun({text:""})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:220},children:[new TextRun({text:"Siemens S7-1200/1500 in-loop · Ryu + Open vSwitch · Modbus TCP + S7comm · July 2026",size:19,color:GREY,italics:true})]}));

// Safety notice
c.push(h1("0. Safety & isolation — read before powering anything"));
c.push(p([t("You are putting a real PLC in-loop, so the testbed must be treated as a physical process. ",{bold:true}),
  t("Three non-negotiables:")]));
c.push(bullet([t("Air-gap the lab. ",{bold:true}),t("Build on a dedicated, isolated LAN with no bridge to home/corporate networks or the internet. The S7-1200/1500 has known unauthenticated-write exposure; it must never be reachable from outside the bench.")]));
c.push(bullet([t("Use a harmless process. ",{bold:true}),t("Drive only safe I/O — LEDs, a small 24 V lamp/relay, or a simulated tank in the PLC program. No motors, heaters, or anything that can cause harm if a flow rule or attack misfires.")]));
c.push(bullet([t("Fail-safe defaults. ",{bold:true}),t("The controller's default action on uncertainty is mirror/allow, never block, so a bug in the response logic cannot itself trip the process (this is also the core CARS principle).")]));

// Hardware roles
c.push(h1("1. Hardware inventory & role assignment"));
c.push(table([1900,2300,4550],
  ["Device","Role","Notes"],
  [
    ["Dell #1 (Ubuntu)","Core SDN node","Ryu controller + Open vSwitch (br0) + CARS policy/Event API. The heart of the testbed. Needs 2–3 Ethernet ports → add USB-to-Ethernet adapters."],
    ["Dell #2 (Ubuntu)","IDS + attacker","Suricata and/or Zeek+ICSNPP as the external event source; also the attacker host for scenarios. Later: digital-twin host."],
    ["Asus Vivobook (Win 11)","HMI / engineering WS","SCADA HMI + Modbus master polling the PLC; runs TIA Portal to program the S7-1200/1500."],
    ["Siemens S7-1200/1500","Field device (crown jewel)","Real PLC. Enable Modbus TCP server (TCP/502) for experiments; S7comm (TCP/102) stays on for realism/attacks. Wired into an OVS port."],
    ["MacBook Air M1","Excluded / spare","ARM makes x86 SDN/Mininet tooling painful. Use for writing/notes only."],
  ]));

// Topology
c.push(h1("2. Network topology"));
c.push(p("All endpoints attach to Open vSwitch (br0) on Dell #1, so the controller mediates every flow. With limited built-in NICs, give Dell #1 extra physical ports via USB-to-Ethernet adapters and add each as an OVS port. The IDS receives a copy of traffic through an OVS mirror (SPAN) port; its alerts drive the reactive loop."));
c.push(new Paragraph({spacing:{after:60}}));
const img = fs.readFileSync("topo.png");
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:60},
  children:[new ImageRun({type:"png",data:img,transformation:{width:600,height:314}})]}));
c.push(p([t("Reactive loop (green/red in the diagram): ",{bold:true}),
  t("IDS detects an anomaly → sends an alert to the Event API on Dell #1 → the CARS policy engine picks a criticality-aware action → Ryu pushes a flow-mod (block / mirror / redirect) to OVS. The physical PLC and HMI keep talking through OVS the whole time.")]));

// Protocol
c.push(h1("3. Protocol strategy"));
c.push(p([t("Primary experimental protocol: Modbus TCP (port 502). ",{bold:true}),
  t("Enable a Modbus TCP server block on the S7-1200/1500 and use a Modbus master on the Asus as the HMI. Modbus is easy to allowlist and deep-inspect, and it lines up directly with your local literature (Ndonda & Sadre's P4 Modbus allowlist; Goldenberg & Wool's Modbus/TCP model). "),
  t("Secondary / realism: S7comm (port 102). ",{bold:true}),
  t("Keep S7comm enabled so you can run realistic Siemens-specific attacks (unauthorized start/stop, block download) and detect them with Zeek's ICSNPP s7comm analyzer. Design CARS to be protocol-agnostic at the policy layer so both map onto the same block/mirror/redirect actions.")]));

// Software stack
c.push(h1("4. Software stack"));
c.push(table([2400,4400,1950],
  ["Layer","Tool","Host"],
  [
    ["SDN controller","Ryu (Python OpenFlow 1.3 apps)","Dell #1"],
    ["Software switch","Open vSwitch (br0)","Dell #1"],
    ["Reactive logic","CARS app + Event API (Flask/REST or syslog listener)","Dell #1"],
    ["IDS / detection","Suricata (signatures) + Zeek + ICSNPP (Modbus/S7comm parsers)","Dell #2"],
    ["HMI / master","Modbus master (e.g. pymodbus/QModMaster) + TIA Portal","Asus"],
    ["Process logic","Ladder/SCL program with Modbus server + safe I/O","Siemens PLC"],
    ["Attacker","pymodbus, Snap7, nmap, scapy, hping3","Dell #2"],
    ["Capture / analysis","Wireshark, tcpdump, ovs-ofctl","Dell #1/#2"],
  ]));

// Phased plan
c.push(h1("5. Phased build plan"));
c.push(p("Six phases. Each lists its goal, key steps, the exit criterion (how you know it's done), and the papers from the master reading list to read alongside it. Phases A–B are the minimum viable testbed; C–D deliver the CARS contribution; E–F are evaluation and stretch."));

c.push(h2("Phase A — Bench prep & physical connectivity"));
c.push(bullet("Install Ubuntu, Ryu, Open vSwitch, Wireshark on Dell #1; create bridge br0; add physical ports (built-in + USB-Ethernet) as OVS ports."));
c.push(bullet("Program the S7-1200/1500 in TIA Portal: a simple safe process (e.g., simulated tank level or traffic-light) with a Modbus TCP server block; assign a static lab IP."));
c.push(bullet("Cable PLC, Asus (HMI) and Dell #2 (IDS/attacker) into OVS ports; set the whole bench on one isolated subnet."));
c.push(bullet([t("Exit criterion: ",{bold:true}),t("HMI on the Asus can read/write PLC registers over Modbus, with traffic physically passing through OVS (confirmed in Wireshark).")]));
c.push(bullet([t("Read alongside: ",{bold:true,color:GREEN}),t("MiniCPS; “Oops I Did It Again” ICS testbed survey; Goldenberg & Wool (Modbus modeling).")]));

c.push(h2("Phase B — SDN baseline"));
c.push(bullet("Run a Ryu learning-switch app (simple_switch_13); confirm OVS is controller-managed (ovs-vsctl show, ovs-ofctl dump-flows)."));
c.push(bullet("Verify the HMI↔PLC Modbus loop still works under controller-installed flows; measure baseline latency/jitter (important: control-loop deadlines)."));
c.push(bullet([t("Exit criterion: ",{bold:true}),t("You can add/remove a flow rule from Ryu and see the effect on PLC↔HMI traffic in real time.")]));
c.push(bullet([t("Read alongside: ",{bold:true,color:GREEN}),t("Piedrahita (IEEE Software + the Computer Networks extended version); Ndonda & Sadre P4 two-level IDS.")]));

c.push(h2("Phase C — Detection integration (external event source)"));
c.push(bullet("Deploy Suricata and Zeek+ICSNPP on Dell #2; feed them via an OVS mirror/SPAN port so detection is passive and never in the control path."));
c.push(bullet("Write/enable Modbus and S7comm rules (unauthorized write, function-code abuse, scanning); emit alerts as structured events (EVE JSON / syslog)."));
c.push(bullet("Stand up the Event API on Dell #1 that ingests those alerts in a normalized schema (source, device, flow, severity, suggested action)."));
c.push(bullet([t("Exit criterion: ",{bold:true}),t("An attacker action on Dell #2 produces an alert that arrives at the Event API within a bounded, logged time.")]));
c.push(bullet([t("Read alongside: ",{bold:true,color:GREEN}),t("Enabling Dynamic Network Access Control (anomaly IDS + SDN); DIDEROT (DNP3 IDPS pattern); DPI for software-defined industrial networks.")]));

c.push(h2("Phase D — CARS reactive response engine (the contribution)"));
c.push(bullet("Connect the Event API to a Ryu CARS app that can install block, mirror, and redirect flow rules on demand."));
c.push(bullet([t("Criticality model: ",{bold:true}),t("tag each device/flow (e.g., PLC↔HMI control loop = critical; unknown host = untrusted). Asset identity feeds the “unseen device” decision.")]));
c.push(bullet([t("Safety guard: ",{bold:true}),t("on a critical flow, never hard-block — mirror or redirect for inspection instead; only block untrusted/unseen devices. Validate rule changes with a policy check before install.")]));
c.push(bullet([t("Exit criterion: ",{bold:true}),t("An unseen device that alerts is blocked automatically, while an alert on the critical PLC loop is redirected for inspection — with the physical process never interrupted.")]));
c.push(bullet([t("Read alongside: ",{bold:true,color:GREEN}),t("Hammar (Optimal Security Response); SoK ICS Asset Discovery; A Policy Checker Approach for Secure Industrial SDN.")]));

c.push(h2("Phase E — Attack scenarios & evaluation"));
c.push(bullet("Run a scenario suite from Dell #2: network scan/recon, unauthorized Modbus/S7 writes, false-data injection, and a Modbus/DoS flood."));
c.push(bullet([t("Metrics: ",{bold:true}),t("detection-to-mitigation latency; process-safety preservation (did the loop stay in bounds?); false-positive rate; controller/switch load. Log everything for reproducibility.")]));
c.push(bullet("Benchmark methodology against SWaT/WADI/HAI conventions so results are comparable to the literature."));
c.push(bullet([t("Exit criterion: ",{bold:true}),t("A repeatable results table quantifying reaction latency and safety preservation per scenario — the core evaluation for the dissertation.")]));
c.push(bullet([t("Read alongside: ",{bold:true,color:GREEN}),t("Samanis (Bristol MTD thesis — method/eval template); Securing ICS networks: Automated Traffic Control + MTD; iTrust SWaT/WADI/HAI.")]));

c.push(h2("Phase F — Stretch: line-rate, deception, and twin validation"));
c.push(bullet("P4 data-plane path (bmv2/software P4 switch) for a line-rate Modbus allowlist that offloads the fast path from the controller."));
c.push(bullet("Redirect-to-honeypot response (extend CARS with an on-demand decoy) and/or a lightweight MiniCPS digital twin to pre-validate a disruptive action before applying it."));
c.push(bullet([t("Read alongside: ",{bold:true,color:GREEN}),t("P4Control; Programmable Data Planes for OT; Reactive cyber deception; TwinSec-IDS; Digital Twin-Enhanced Incident Response.")]));

// Minimal first milestone
c.push(h1("6. Start here — the minimal first milestone"));
c.push(p([t("Do not try to build all six phases before testing anything. ",{bold:true}),
  t("Your first concrete goal is a trivial end-to-end reactive loop that proves the plumbing:")]));
c.push(bullet("PLC running a safe Modbus process, HMI polling it, all traffic through OVS (Phase A)."));
c.push(bullet("Ryu managing OVS (Phase B)."));
c.push(bullet("A hand-crafted trigger (even a manual curl to the Event API, before the IDS is wired) that makes Ryu install one block/redirect rule and visibly change the traffic."));
c.push(p([t("Once that loop works end-to-end, everything else is incremental. ",{bold:true}),
  t("Getting this minimal loop running will teach you more about the stack than any amount of additional reading — which is exactly why the reading and the build run in parallel.")]));

// Risks
c.push(h1("7. Key risks & mitigations"));
c.push(table([3300,2650,2800],
  ["Risk","Impact","Mitigation"],
  [
    ["Not enough physical NICs on Dell #1","Can't attach all endpoints to OVS","2–3 USB-to-Ethernet adapters; or VLANs on a cheap managed switch."],
    ["Response logic disrupts the live PLC loop","Process/safety incident","Fail-safe default = mirror/allow; safety guard blocks only untrusted devices; policy check before install."],
    ["S7comm hard to deep-inspect","Weak detection on native protocol","Use Modbus TCP as primary experimental protocol; Zeek ICSNPP for S7comm signatures."],
    ["Controller/OVS latency breaks control-loop timing","PLC faults / instability","Measure baseline jitter (Phase B); pre-install rules for the critical loop; keep IDS off the control path (mirror only)."],
    ["Real PLC exposed beyond the bench","Serious security risk","Strict air-gap; static lab subnet; no internet/corporate bridge."],
  ]));

c.push(new Paragraph({spacing:{before:200},children:[new TextRun({text:"This plan maps directly onto MASTER_READING_LIST.md: Phases A–D correspond to reading Phases 0–3, and each build phase above names the exact papers to read alongside it. Tick reading and build items together.",size:18,italics:true,color:GREY})]}));

const doc=new Document({
  creator:"Reactive SDN for ICS — Project CARS",
  title:"Phased Testbed Build Plan — Reactive SDN for ICS (CARS)",
  styles:{default:{document:{run:{font:"Calibri",size:22,color:"1A1A1A"}}}},
  numbering:{config:[{reference:"b",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:460,hanging:260}}}}]}]},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1200,bottom:1200,left:1300,right:1300}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"C9D2E2"}},children:[new TextRun({text:"CARS · Phased Testbed Build Plan",size:16,color:GREY,italics:true})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:16,color:GREY}),new TextRun({children:[PageNumber.CURRENT," of ",PageNumber.TOTAL_PAGES],size:16,color:GREY})]})]})},
    children:c,
  }],
});
Packer.toBuffer(doc).then((buf)=>{fs.writeFileSync("Reactive_SDN_ICS_Testbed_Build_Plan.docx",buf);console.log("written",buf.length);});
