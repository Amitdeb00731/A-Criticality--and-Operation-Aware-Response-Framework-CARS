const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageNumber,
  Header, Footer, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  LevelFormat, ImageRun,
} = require("docx");

const ACCENT="1F3864", ACCENT2="2E5496", GREY="595959", GREEN="1E7145", RED="9C1F2E", AMBER="9C5700";
const h1=(x)=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:320,after:120},children:[new TextRun({text:x,bold:true,color:ACCENT,size:30})]});
const h2=(x)=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:220,after:80},children:[new TextRun({text:x,bold:true,color:ACCENT2,size:25})]});
function p(runs,opts={}){const children=Array.isArray(runs)?runs:[new TextRun({text:runs,size:22})];return new Paragraph({alignment:AlignmentType.JUSTIFIED,spacing:{after:130,line:274},children,...opts});}
const t=(text,o={})=>new TextRun({text,size:22,...o});
function bullet(runs,level=0){const children=Array.isArray(runs)?runs:[new TextRun({text:runs,size:22})];return new Paragraph({numbering:{reference:"b",level},alignment:AlignmentType.JUSTIFIED,spacing:{after:70,line:268},children});}
function table(cols, header, data, headFill=ACCENT, fsz=17) {
  function cell(text,{bold=false,fill,head=false,color}={},w){
    const runs = Array.isArray(text) ? text : [new TextRun({text,bold,size:fsz,color:head?"FFFFFF":(color||"000000")})];
    return new TableCell({width:{size:w,type:WidthType.DXA},shading:fill?{type:ShadingType.CLEAR,fill}:undefined,
      margins:{top:52,bottom:52,left:80,right:80},children:[new Paragraph({spacing:{after:0},children:runs})]});
  }
  const rows=[new TableRow({tableHeader:true,children:header.map((h,i)=>cell(h,{bold:true,fill:headFill,head:true},cols[i]))})];
  data.forEach((r,idx)=>{const fill=idx%2?"EDF1F8":"FFFFFF";rows.push(new TableRow({children:r.map((cc,i)=>cell(cc,{fill},cols[i]))}));});
  return new Table({columnWidths:cols,width:{size:cols.reduce((a,b)=>a+b,0),type:WidthType.DXA},
    borders:{top:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},bottom:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},
      left:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},right:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},
      insideHorizontal:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"},insideVertical:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"}},rows});
}

const c=[];
c.push(new Paragraph({spacing:{before:240}}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:50},children:[new TextRun({text:"Tier 3 Finalized Testbed Architecture",bold:true,size:34,color:ACCENT})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},children:[new TextRun({text:"& Folded Build Plan · Project CARS (working title)",size:24,color:ACCENT2,italics:true})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,border:{top:{style:BorderStyle.SINGLE,size:6,color:ACCENT}},spacing:{after:40},children:[new TextRun({text:""})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:200},children:[new TextRun({text:"High-fidelity Purdue-zoned ICS · Factory I/O + real S7-1200/1500 · full IT→OT attack path · July 2026",size:19,color:GREY,italics:true})]}));

// Decisions locked
c.push(h1("1. Decisions locked in"));
c.push(p([t("Scope note: ",{bold:true,color:AMBER}),
  t("what is locked here is the "),
  t("testbed",{italics:true}),
  t(", not the research contribution. “CARS” (Criticality-Aware Response) is a working title / lead hypothesis — the final contribution is decided empirically as the testbed matures. The testbed is deliberately general-purpose and supports several candidate directions: (1) safety-constrained response [CARS], (2) source-agnostic event-to-action orchestration, (3) hybrid data-plane/control-plane enforcement, (4) twin-validated response, (5) a graduated deception ladder, (6) a resilient reactive control plane. Nothing below commits to one.")]));
c.push(bullet([t("Fidelity: Tier 3 ",{bold:true}),t("— full Purdue stack (L0–L5) with Industrial DMZ, corporate/IT zone, and dual firewalls, so attacks can traverse a realistic IT→OT kill chain.")]));
c.push(bullet([t("Level 0 process: Factory I/O ",{bold:true}),t("(licensed on the university Dells) — 3D-visualized process driven by the real PLC via the Siemens S7 driver.")]));
c.push(bullet([t("Hardware: ",{bold:true}),t("2 Dell (full admin, 16GB+ each), 1 Asus (Win 11), real Siemens S7-1200/1500. MacBook M1 excluded.")]));
c.push(bullet([t("Protocols: ",{bold:true}),t("S7comm (process I/O + realism), Modbus TCP (primary CARS traffic), OPC UA (L2–L3), MQTT/Sparkplug (IIoT edge).")]));
c.push(bullet([t("Orchestration: GNS3 ",{bold:true}),t("as the virtual-network topology layer on Dell #1 — hosts the pfSense firewalls, DMZ, corporate/attacker and container nodes, with the CARS-controlled OVS as a GNS3 node under Ryu and a Cloud node bridging the real PLC / Factory I/O.")]));

// Host allocation
c.push(h1("2. Host allocation"));
c.push(p("Factory I/O is Windows-only and GPU-bound, so it runs bare-metal on Dell #2 (Windows). Dell #1 boots Ubuntu and becomes the SDN core plus the virtualization host for every Linux role. The Asus is the operator/engineering station."));
c.push(table([1800,3200,3550],
  ["Host / OS","Runs","Purdue zone"],
  [
    ["Dell #1 · Ubuntu","Ryu + CARS + Open vSwitch (fabric); GNS3 + Docker/KVM host for IDS, historian, DMZ, firewalls, soft-PLC, OPC UA/MQTT, attacker","Network fabric + L1/L3/L3.5/L4-5 (virtualized)"],
    ["Dell #2 · Windows","Factory I/O (3D process); optional offload of the Kali attacker VM","L0 Physical process (+ L4/5 option)"],
    ["Asus · Win 11","HMI/SCADA (Ignition Maker Edition); TIA Portal (EWS)","L2 Supervisory"],
    ["Siemens S7-1200/1500","Real control logic; Modbus server + S7comm; safe I/O; SIS interlock","L1 Basic Control + L0 real I/O"],
    ["MacBook Air M1","Writing / notes only","— excluded"],
  ], ACCENT, 16));

// Topology
c.push(h1("3. Zoned topology"));
c.push(p("Every device attaches to Open vSwitch on Dell #1. Purdue zones are realized as VLANs on OVS; two pfSense VMs enforce the IT↔DMZ↔OT boundaries with deny-by-default rules. The SDN controller (CARS) still mediates every flow and the IDS reads a mirror port — so the reactive loop operates across the whole zoned network."));
c.push(new Paragraph({spacing:{after:60}}));
const t3=fs.readFileSync("tier3.png");
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:60},children:[new ImageRun({type:"png",data:t3,transformation:{width:560,height:600}})]}));

// VLAN plan
c.push(h1("4. Network / VLAN plan"));
c.push(table([1500,2100,5000],
  ["VLAN","Zone","Members"],
  [
    ["10","Control (L1)","Real S7-1200/1500, OpenPLC soft-PLC, SIS interlock"],
    ["20","Supervisory (L2)","HMI/SCADA (Ignition), EWS (TIA Portal), OPC UA server, MQTT broker"],
    ["30","Operations (L3)","Historian (InfluxDB + Grafana)"],
    ["35","Industrial DMZ (L3.5)","Historian replica, jump host — between the two pfSense firewalls"],
    ["40","Enterprise IT (L4/5)","Corporate host + attacker pivot (Kali)"],
    ["—","Process (L0)","Factory I/O ↔ PLC over the S7 driver (rides VLAN 10 to the PLC)"],
    ["mgmt","SDN control","Ryu↔OVS OpenFlow channel; IDS mirror port (out-of-band)"],
  ], ACCENT, 16));
c.push(p([t("Firewall posture: ",{bold:true}),t("deny-by-default, allow-by-exception, fail-closed at each zone boundary — the standard OT segmentation model. CARS operates within and across these zones at the SDN layer, complementing (not replacing) the L3 firewalls.")]));

// RAM budget
c.push(h1("5. Dell #1 RAM budget (fits in 16GB)"));
c.push(table([4300,1500,2800],
  ["Component","Est. RAM","Note"],
  [
    ["Ubuntu host + Open vSwitch + Ryu/CARS","2.5 GB","Core; always on"],
    ["IDS container (Suricata + Zeek/ICSNPP)","1.5 GB","Reads OVS mirror"],
    ["Historian (InfluxDB + Grafana) containers","1.0 GB","Time-series tag logging"],
    ["IT-side firewall (pfSense VM)","1.0 GB","Lightweight"],
    ["OT-side firewall (pfSense VM)","1.0 GB","Lightweight"],
    ["DMZ host (historian replica + jump)","1.0 GB","Container/VM"],
    ["OpenPLC soft-PLC + OPC UA/MQTT containers","1.0 GB","Light"],
    ["Kali attacker VM (during scenarios)","3.0 GB","Offload to Dell #2 to free RAM"],
    ["Headroom","~4 GB","OS cache / spikes"],
  ], ACCENT, 16));
c.push(p([t("Tip: ",{bold:true}),t("prefer Docker containers over full VMs for the soft-devices (the ICSSIM / ICS-SimLab approach) — much lighter than VM-per-device. Run the Kali attacker only during Phase E, or host it on Dell #2 alongside Factory I/O, to keep the OT host comfortable.")]));

// Folded build plan
c.push(h1("6. Folded phased build plan (Tier 3)"));
c.push(p("The six phases from the build plan, updated with the Tier 3 components. Exit criteria and reading mappings from the master list still apply."));
c.push(h2("Phase A — Bench, process & baseline HMI"));
c.push(bullet("Dell #1: install Ubuntu, Open vSwitch, Ryu, Docker, GNS3; create br0 with VLANs 10/20/30/35/40; add physical ports via USB-Ethernet."));
c.push(bullet("Dell #2 (Windows): install Factory I/O; build a simple scene (e.g., level/tank or sorting station); configure the Siemens S7 driver to the real PLC."));
c.push(bullet("PLC: TIA Portal program that reads Factory I/O sensors and drives actuators + a safe LED/relay; enable PUT/GET and a Modbus TCP server; add a basic SIS interlock."));
c.push(bullet("Asus: install Ignition Maker Edition (HMI) and confirm it can read PLC tags via OPC UA/Modbus."));
c.push(bullet([t("Exit: ",{bold:true}),t("Factory I/O process runs under real-PLC control, visible on the Ignition HMI, with all traffic through OVS.")]));
c.push(h2("Phase B — SDN baseline + historian + protocols"));
c.push(bullet("Ryu learning-switch app manages OVS; verify control-loop latency/jitter within budget."));
c.push(bullet("Stand up the historian (InfluxDB + Grafana container) logging PLC tags; add OPC UA server + Mosquitto MQTT broker."));
c.push(bullet([t("Exit: ",{bold:true}),t("Live process data flows PLC → historian and renders in Grafana; you can add/remove an OVS flow from Ryu.")]));
c.push(h2("Phase C — Zones, firewalls & detection"));
c.push(bullet("Build the virtual topology in GNS3: two pfSense firewalls + DMZ host (historian replica + jump); enforce deny-by-default between VLANs 40↔35↔30."));
c.push(bullet("Deploy IDS (Suricata + Zeek/ICSNPP) on an OVS mirror; write Modbus/S7comm/OPC UA rules; emit alerts to the CARS Event API."));
c.push(bullet([t("Exit: ",{bold:true}),t("An attacker in the enterprise zone is contained by the firewalls, and an OT-network anomaly reaches the Event API.")]));
c.push(h2("Phase D — Reactive engine (CARS lead hypothesis; contribution TBD)"));
c.push(bullet("Ryu app installs block / mirror / redirect flows on demand; criticality model tags the PLC control loop vs unknown hosts."));
c.push(bullet("Safety guard: never hard-block the critical loop — mirror/redirect for inspection; block only untrusted/unseen devices; policy-check before install."));
c.push(bullet([t("Exit: ",{bold:true}),t("Unseen device that alerts is auto-blocked; alert on the critical loop is redirected — Factory I/O process never interrupted.")]));
c.push(bullet([t("Note: ",{bold:true,color:AMBER}),t("this phase realizes the CARS lead hypothesis, but the platform equally supports the other candidate contributions — the final direction is chosen here based on what proves tractable and novel.")]));
c.push(h2("Phase E — Full IT→OT attack scenarios & evaluation"));
c.push(bullet("Kill chain from the enterprise zone: pivot → DMZ → OT; plus direct OT attacks (unauthorized Modbus/S7 writes, false-data injection, DoS)."));
c.push(bullet([t("Metrics: ",{bold:true}),t("detection-to-mitigation latency; process-safety preservation (watch the Factory I/O process); false positives; controller load. Log for reproducibility; benchmark vs SWaT/WADI/HAI conventions.")]));
c.push(bullet([t("Exit: ",{bold:true}),t("A repeatable results table per scenario — the dissertation's core evaluation.")]));
c.push(h2("Phase F — Stretch"));
c.push(bullet("P4 data-plane allowlist (bmv2); redirect-to-honeypot response; MiniCPS/digital-twin pre-validation of disruptive actions; MQTT/Sparkplug edge scenario."));

// Prereqs
c.push(h1("7. Prerequisites & shopping list"));
c.push(bullet([t("Hardware: ",{bold:true}),t("2–3 USB-to-Ethernet adapters for Dell #1 (to attach PLC, Asus, and uplinks to OVS). This is the only purchase.")]));
c.push(bullet([t("Software (all free unless noted): ",{bold:true}),t("Open vSwitch, Ryu, Docker, GNS3, KVM (Ubuntu); pfSense; Suricata + Zeek/ICSNPP; InfluxDB + Grafana; OpenPLC; Mosquitto; open62541/python-opcua; Ignition Maker Edition; Kali. Factory I/O (already licensed) and TIA Portal on Windows.")]));
c.push(bullet([t("Verify on PLC: ",{bold:true}),t("PUT/GET enabled; “optimized block access” setting compatible with the Factory I/O S7 driver and Modbus server block configured.")]));

// Ready
c.push(h1("8. Ready to build — first move"));
c.push(p([t("Start with the Phase A minimal loop before wiring the zones: ",{bold:true}),
  t("get Factory I/O + real PLC + Ignition HMI working through OVS on a single flat network, then layer in the VLANs, firewalls, IDS, and CARS. Build the fidelity outward from a working core, exactly as the master reading list is ordered. Say the word and I'll write the concrete Phase A setup commands (OVS bridge + VLANs, Ryu install, Factory I/O S7 driver config, and the TIA Portal Modbus/PUT-GET settings).")]));

c.push(new Paragraph({spacing:{before:200},children:[new TextRun({text:"This supersedes the tier selection in the component analysis. CARS throughout is a working title for the lead hypothesis, not the finalized contribution. Diagram zones are logical VLANs on one OVS, not separate physical switches.",size:18,italics:true,color:GREY})]}));

const doc=new Document({
  creator:"Reactive SDN for ICS - Project CARS (working title)",
  title:"Tier 3 Finalized Testbed Architecture and Build Plan",
  styles:{default:{document:{run:{font:"Calibri",size:22,color:"1A1A1A"}}}},
  numbering:{config:[{reference:"b",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:460,hanging:260}}}}]}]},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1200,bottom:1200,left:1300,right:1300}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"C9D2E2"}},children:[new TextRun({text:"CARS (working title) · Tier 3 Finalized Architecture",size:16,color:GREY,italics:true})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:16,color:GREY}),new TextRun({children:[PageNumber.CURRENT," of ",PageNumber.TOTAL_PAGES],size:16,color:GREY})]})]})},
    children:c,
  }],
});
Packer.toBuffer(doc).then((buf)=>{fs.writeFileSync("Reactive_SDN_ICS_Tier3_Architecture.docx",buf);console.log("written",buf.length);});
