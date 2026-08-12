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

function table(cols, header, data, headFill=ACCENT, fs=17) {
  function cell(text,{bold=false,fill,head=false,color}={},w){
    const runs = Array.isArray(text) ? text : [new TextRun({text,bold,size:fs,color:head?"FFFFFF":(color||"000000")})];
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
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:50},children:[new TextRun({text:"ICS Testbed — Component Requirements",bold:true,size:36,color:ACCENT})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},children:[new TextRun({text:"& Fidelity Gap Analysis · Project CARS",size:24,color:ACCENT2,italics:true})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,border:{top:{style:BorderStyle.SINGLE,size:6,color:ACCENT}},spacing:{after:40},children:[new TextRun({text:""})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:220},children:[new TextRun({text:"What it takes to make the testbed a faithful ICS environment — and how to do it on your hardware · July 2026",size:19,color:GREY,italics:true})]}));

// Intro
c.push(h1("1. What makes a testbed a real ICS environment"));
c.push(p([t("A convincing ICS environment is not just “a PLC on a network.” The field measures realism against the "),
  t("Purdue reference model",{bold:true}),
  t(", which organizes an industrial system into layered zones from the physical process up to enterprise IT. A faithful testbed represents each relevant layer, uses real industrial protocols, drives a physical (or physically-modelled) process, and segments the network the way a plant would. Surveys classify testbeds as "),
  t("physical, software-simulated, semi-physical (hardware-in-the-loop), or virtualized",{italics:true}),
  t("; yours is naturally a semi-physical / hybrid testbed — a real Siemens PLC plus software for everything else, which is a strong, realistic sweet spot.")]));
c.push(p([t("Your goal is not maximum fidelity at any cost. ",{bold:true}),
  t("It is enough fidelity that a reactive-security contribution (CARS) is credible: multiple communicating devices, a live process that can visibly go unsafe, realistic protocols, and plant-like segmentation for the SDN fabric to act on.")]));
c.push(new Paragraph({spacing:{after:60}}));
const purdue = fs.readFileSync("purdue.png");
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:60},children:[new ImageRun({type:"png",data:purdue,transformation:{width:590,height:410}})]}));

// Component checklist by Purdue level
c.push(h1("2. Component checklist by Purdue level"));
c.push(p("For each layer: the real-world component, whether you need it for CARS, and the lowest-effort way to provide it on your kit."));
c.push(table([950,2400,1350,3900],
  ["Level","Real component","Need it?","How to provide it (your hardware)"],
  [
    ["L0 Process","Sensors, actuators, tank/motor","Yes","Software process sim — Factory I/O (visual, on Asus), Simulink, or a Python model via MiniCPS; plus a few safe real outputs (LEDs/relay) on the PLC."],
    ["L1 Control","PLC / RTU / SIS","Have + add","Real Siemens S7-1200/1500 (primary). Add a 2nd soft-PLC (OpenPLC) for multi-device realism. Add a simple safety interlock in ladder to represent an SIS."],
    ["L2 Supervisory","HMI, SCADA server, EWS","Yes","HMI/SCADA: Ignition Maker Edition (free) or ScadaBR or Node-RED dashboard on the Asus. EWS = TIA Portal. Optional OPC UA server here."],
    ["L3 Operations","Historian, MES","Recommended","Historian: InfluxDB + Grafana (time-series of tags) on Dell #1 or a VM. MES optional — skip."],
    ["L3.5 IDMZ","Historian replica, jump host","Optional","One VM acting as DMZ host (historian replica + jump box). Adds segmentation realism for the SDN policy; can defer."],
    ["L4/5 IT","Enterprise host, AD, email","Optional","A single “corporate” VM on Dell #2 as the attacker's pivot/entry point. Full AD not needed."],
    ["Network","Managed switch, firewalls","Yes","Open vSwitch (your OpenFlow switch) + Ryu. Emulate Purdue zones with VLANs/multiple bridges. Optional pfSense VM as IT/OT firewall."],
    ["Security","IDS/IPS, SIEM","Yes","Suricata + Zeek/ICSNPP on Dell #2 (the external event source for CARS). Logs/alerts = your dataset."],
  ], ACCENT, 16));

// Protocols
c.push(h1("3. Protocol realism"));
c.push(p([t("Real plants are multi-protocol. You already have Modbus TCP and S7comm; adding one or two modern protocols materially raises fidelity and widens the attack/response surface CARS can act on:")]));
c.push(bullet([t("Modbus TCP (have) ",{bold:true}),t("— primary experimental protocol; easy to allowlist/DPI.")]));
c.push(bullet([t("S7comm (have) ",{bold:true}),t("— native Siemens; realistic PLC attacks (start/stop, block download).")]));
c.push(bullet([t("OPC UA (add, recommended) ",{bold:true}),t("— the modern OT standard; provide via Ignition's OPC UA server or the open62541 / python-opcua (FreeOpcUa) stack. Bridges L2–L3.")]));
c.push(bullet([t("MQTT / Sparkplug (optional) ",{bold:true}),t("— IIoT telemetry; Mosquitto broker + Node-RED. Nice for a modern edge angle, not essential.")]));
c.push(bullet([t("DNP3 / EtherNet/IP (skip) ",{bold:true}),t("— valuable in power/discrete industries but out of scope unless your process demands them.")]));

// Fidelity tiers
c.push(h1("4. Fidelity tiers — choose your scope"));
c.push(p("Three coherent scopes. Pick one as the finalized target; you can grow from Tier 1 to Tier 2 without rework."));
c.push(table([1550,2400,4650],
  ["Tier","What it adds","Verdict for CARS"],
  [
    ["Tier 1 — Minimum viable","Real PLC + process sim + HMI + IDS + SDN fabric, single zone.","Enough to demonstrate the reactive loop. Good for the first milestone."],
    ["Tier 2 — Realistic (recommended)","+ 2nd soft-PLC, historian (InfluxDB/Grafana), OPC UA, Purdue VLAN segmentation, safety interlock.","The right target: multi-device, multi-zone, multi-protocol — makes CARS' criticality/safety story credible."],
    ["Tier 3 — High-fidelity","+ IDMZ + jump host + corporate/IT zone + dual firewalls + MQTT/Sparkplug + richer process (Tennessee Eastman via GRFICS).","Impressive but heavy. Add selectively only if time allows."],
  ], ACCENT, 17));

// Frameworks to borrow
c.push(h1("5. Frameworks worth borrowing from"));
c.push(p("Rather than build every piece by hand, lift components/ideas from established open frameworks:"));
c.push(bullet([t("MiniCPS ",{bold:true}),t("— your process/physics emulation backbone (already in your reading list; used by Piedrahita).")]));
c.push(bullet([t("GRFICS / GRFICSv2 ",{bold:true}),t("— full virtual ICS with a 3D-visualized Tennessee Eastman process, OpenPLC + ScadaBR; great for a compelling demo and attack visualization.")]));
c.push(bullet([t("ICSSIM & ICS-SimLab ",{bold:true}),t("— recent frameworks that containerize PLCs/HMIs/sensors via Docker + a JSON topology file; ideal for spinning up extra soft-devices cheaply and for dataset generation.")]));
c.push(bullet([t("OpenPLC ",{bold:true}),t("— soft-PLC for your 2nd controller and safe experimentation (you already have the OpenPLC Aqua paper).")]));
c.push(p([t("Recommendation: ",{bold:true}),
  t("use MiniCPS or a lightweight Python/OpenPLC model for the process, keep the real Siemens PLC as the star, and borrow ICSSIM/ICS-SimLab's containerized approach if you want several soft-devices without more machines.")]));

// Host allocation
c.push(h1("6. Finalized component list & host allocation (Tier 2 target)"));
c.push(table([1850,3050,3700],
  ["Host","Runs","Purdue role"],
  [
    ["Dell #1 (Ubuntu)","Ryu + CARS + Open vSwitch; InfluxDB + Grafana historian; Event API","Network fabric + L3 Operations"],
    ["Dell #2 (Ubuntu)","Suricata + Zeek/ICSNPP IDS; attacker (pymodbus, snap7, nmap); optional IT/DMZ VMs","Security + L4/5 + L3.5"],
    ["Asus (Win 11)","HMI/SCADA (Ignition Maker / ScadaBR / Node-RED); TIA Portal EWS; Factory I/O process sim","L2 Supervisory + L0 visualization"],
    ["Siemens S7-1200/1500","Real control logic; Modbus TCP server + S7comm; safe I/O; SIS interlock","L1 Basic Control + L0 real I/O"],
    ["(soft) OpenPLC","2nd PLC in a container/VM on a Dell","L1 (multi-device realism)"],
    ["MacBook Air M1","Writing / notes only","— (excluded)"],
  ], ACCENT, 16));

// What you don't need
c.push(h1("7. What you do NOT need (scope control)"));
c.push(p("To avoid over-building, explicitly out of scope unless a specific experiment demands it: full MES/ERP, Active Directory forest, redundant/HA controllers, real physical actuators beyond safe demo I/O, DNP3/EtherNet/IP/PROFIsafe, and a hardware managed switch (OVS replaces it). Tier 3 items (IDMZ, dual firewalls, corporate zone) are optional polish, not prerequisites."));

// Decision / next
c.push(h1("8. Recommendation & decision point"));
c.push(p([t("Adopt Tier 2 as the finalized target. ",{bold:true}),
  t("Concretely, add to the current plan: (1) a software process simulation at L0 (Factory I/O on the Asus, or a Python/MiniCPS model); (2) a proper HMI/SCADA at L2 (Ignition Maker Edition recommended — free, OPC UA native, professional); (3) a historian at L3 (InfluxDB + Grafana); (4) a 2nd soft-PLC (OpenPLC) and a simple SIS interlock; (5) OPC UA as a third protocol; and (6) Purdue-style VLAN segmentation on OVS. Everything else stays as in the testbed build plan.")]));
c.push(p([t("Cost check: ",{bold:true}),
  t("all recommended additions are free/open-source except Factory I/O (which has a free trial; a Python/MiniCPS process is the zero-cost substitute). The only hardware you still need is the 2–3 USB-to-Ethernet adapters already noted in the build plan.")]));
c.push(p([t("Once you confirm Tier 2, ",{bold:true}),
  t("we fold these components into the phased build plan (L0 process sim and HMI land in Phase A; historian and OPC UA in Phase B–C; segmentation and 2nd PLC in Phase C–D) and start building from scratch.")]));

c.push(new Paragraph({spacing:{before:200},children:[new TextRun({text:"Sources: Purdue model (SANS, Inductive Automation); ICS testbed surveys and frameworks (GRFICS, ICSSIM, ICS-SimLab, MiniCPS); OT segmentation and IDMZ guidance; open-source SCADA/historian stacks (Ignition Maker, ScadaBR, Node-RED + InfluxDB + Grafana). Full links in the chat response.",size:18,italics:true,color:GREY})]}));

const doc=new Document({
  creator:"Reactive SDN for ICS — Project CARS",
  title:"ICS Testbed Component Requirements & Fidelity Gap Analysis",
  styles:{default:{document:{run:{font:"Calibri",size:22,color:"1A1A1A"}}}},
  numbering:{config:[{reference:"b",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:460,hanging:260}}}}]}]},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1200,bottom:1200,left:1300,right:1300}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"C9D2E2"}},children:[new TextRun({text:"CARS · ICS Testbed Component Requirements",size:16,color:GREY,italics:true})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:16,color:GREY}),new TextRun({children:[PageNumber.CURRENT," of ",PageNumber.TOTAL_PAGES],size:16,color:GREY})]})]})},
    children:c,
  }],
});
Packer.toBuffer(doc).then((buf)=>{fs.writeFileSync("Reactive_SDN_ICS_Testbed_Components.docx",buf);console.log