const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageNumber,
  Header, Footer, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  LevelFormat, ImageRun,
} = require("docx");

const ACCENT="1F3864", ACCENT2="2E5496", GREY="595959", GREEN="1E7145", RED="C00000", AMBER="9C5700";
const h1=(x)=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:300,after:110},children:[new TextRun({text:x,bold:true,color:ACCENT,size:29})]});
const h2=(x)=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:200,after:70},children:[new TextRun({text:x,bold:true,color:ACCENT2,size:24})]});
function p(runs,opts={}){const ch=Array.isArray(runs)?runs:[new TextRun({text:runs,size:22})];return new Paragraph({alignment:AlignmentType.JUSTIFIED,spacing:{after:120,line:272},children:ch,...opts});}
const t=(x,o={})=>new TextRun({text:x,size:22,...o});
function bul(runs){const ch=Array.isArray(runs)?runs:[new TextRun({text:runs,size:22})];return new Paragraph({numbering:{reference:"b",level:0},alignment:AlignmentType.JUSTIFIED,spacing:{after:60,line:266},children:ch});}
function tbl(cols,header,data,fsz=16){
  function cell(x,{bold=false,fill,head=false,color}={},w){
    const r=Array.isArray(x)?x:[new TextRun({text:x,bold,size:fsz,color:head?"FFFFFF":(color||"000000")})];
    return new TableCell({width:{size:w,type:WidthType.DXA},shading:fill?{type:ShadingType.CLEAR,fill}:undefined,margins:{top:48,bottom:48,left:75,right:75},children:[new Paragraph({spacing:{after:0},children:r})]});
  }
  const rows=[new TableRow({tableHeader:true,children:header.map((h,i)=>cell(h,{bold:true,fill:ACCENT,head:true},cols[i]))})];
  data.forEach((row,idx)=>{const fill=idx%2?"EDF1F8":"FFFFFF";rows.push(new TableRow({children:row.map((cc,i)=>cell(cc,{fill},cols[i]))}));});
  return new Table({columnWidths:cols,width:{size:cols.reduce((a,b)=>a+b,0),type:WidthType.DXA},borders:{top:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},bottom:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},left:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},right:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},insideHorizontal:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"},insideVertical:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"}},rows});
}
const c=[];
c.push(new Paragraph({spacing:{before:220}}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:50},children:[new TextRun({text:"6-Week Execution Plan",bold:true,size:38,color:ACCENT})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},children:[new TextRun({text:"Project CARS — Reactive SDN for Securing ICS (working title)",size:23,color:ACCENT2,italics:true})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,border:{top:{style:BorderStyle.SINGLE,size:6,color:ACCENT}},spacing:{after:40},children:[new TextRun({text:""})]}));
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:180},children:[new TextRun({text:"Indicative dates Wk1 = Mon 6 Jul 2026 → submit ~16 Aug 2026 · anchor to your real deadline",size:19,color:GREY,italics:true})]}));

c.push(h1("1. Operating principles"));
c.push(bul([t("Parallel streams, not phases-in-series. ",{bold:true}),t("Build, read, and write run concurrently every week. Writing starts Week 1 — never left to the end.")]));
c.push(bul([t("De-scope fidelity, never the contribution. ",{bold:true}),t("If behind, cut testbed richness via the ladder in §6. The CARS engine, the evaluation, and the write-up are protected.")]));
c.push(bul([t("Resolve the crux early. ",{bold:true}),t("CC-1 (conduit vs intra-zone scope) and CC-3 (how safety is proven) are settled in Week 1, before the engine is coded. CC-4 (does CARS add latency) is measured in Week 2.")]));
c.push(bul([t("Build outward from a working core. ",{bold:true}),t("Minimal reactive loop first (Week 1–2); fidelity layered on only once it works.")]));

c.push(h1("2. Timeline at a glance"));
const g=fs.readFileSync("gantt.png");
c.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:80},children:[new ImageRun({type:"png",data:g,transformation:{width:610,height:256}})]}));
c.push(tbl([900,2500,2200,1900],
 ["Week","Build","Read / Decide","Write"],
 [
  ["W1","Devices ready; Phase A: Factory I/O + real PLC + Ignition HMI on flat OVS","Ph 0–2 deep; LOCK contribution; settle CC-1 & CC-3","Skeleton + Intro + start Background"],
  ["W2","Phase B (Ryu↔OVS; measure latency=CC-4); Ph C-lite (IDS→Event API; manual trigger→flow); historian+OPC UA","Safety cluster (Ph 8)","Methodology + Testbed chapter"],
  ["W3","Phase D: CARS engine — criticality model + safety-constrained response + audit log","Taper (policy-checker, twin-IR)","Finish Lit Review; Design chapter"],
  ["W4","Zones in GNS3 (pfSense×2, DMZ, corp) as time allows; Ph E attack suite; first metrics","—","GATE: Intro+Bg+Method drafted; Implementation ch."],
  ["W5","Ph E full run: scenario suite + operator metrics; analysis","—","Results + Analysis; Discussion"],
  ["W6","Code freeze (bugfix only)","Cite-time checks (CHAOS id, NIST r3)","Conclusion, Abstract, polish, SUBMIT"],
 ]));

c.push(h1("3. Week-by-week detail"));
c.push(h2("Week 1 — Foundations & the minimal loop"));
c.push(bul("Complete the pre-build checklist; Phase A: PLC controls the Factory I/O process (S7 driver), visible on the Ignition HMI, all traffic through Open vSwitch on a single flat network."));
c.push(bul([t("Decide & record: ",{bold:true}),t("lock the single contribution; resolve CC-1 (does CARS act only at conduits or also intra-zone?) and CC-3 (safety proven by envelope-invariant check and/or twin dry-run?). Confirm D4/D5.")]));
c.push(bul([t("Exit: ",{bold:true}),t("working process-under-PLC-control through OVS; contribution + safety method locked; dissertation skeleton + Intro drafted.")]));
c.push(h2("Week 2 — SDN baseline, detection & reactive skeleton"));
c.push(bul("Phase B: Ryu manages OVS; measure baseline control-loop latency/jitter (CC-4). Phase C-lite: Suricata/Zeek on an OVS mirror emit alerts to the Event API; a manual trigger makes Ryu install one block/redirect rule. Stand up historian + OPC UA."));
c.push(bul([t("CHECKPOINT (end W2): ",{bold:true,color:RED}),t("is the alert→controller→flow-change loop solid AND is the added latency acceptable? If no → trigger the de-scope ladder now.")]));
c.push(h2("Week 3 — CARS engine (the contribution)"));
c.push(bul("Phase D: criticality model (tag the PLC control loop vs unknown hosts); safety-constrained response (allow / block / mirror / redirect); safety guard (never hard-block the critical loop — mirror/redirect instead; policy/twin check before install); reversibility + machine-readable audit log."));
c.push(bul([t("Exit: ",{bold:true}),t("unseen device that alerts is auto-blocked; alert on the critical loop is redirected; Factory I/O process never interrupted; every action logged.")]));
c.push(h2("Week 4 — Zones, attack suite & first evaluation"));
c.push(bul("Build the virtual zones in GNS3 (two pfSense firewalls, DMZ, corporate/Kali) as far as time allows; implement the attack suite (recon, unauthorized Modbus/S7 write, false-data injection, DoS; full IT→OT kill chain if zones are ready); first metrics run."));
c.push(bul([t("GATE (end W4): ",{bold:true,color:RED}),t("writing must be underway — Introduction, Background and Methodology drafted. If not, stop building and write.")]));
c.push(h2("Week 5 — Full evaluation & results"));
c.push(bul("Phase E complete: run the full scenario suite; collect operator-relevant metrics — zero defence-induced process trips, false-block rate on critical flows, mean-time-to-mitigate, controller load, audit-trail completeness; analyse; sensitivity checks if time. Add Tier-3 fidelity only if ahead."));
c.push(bul([t("Exit: ",{bold:true}),t("complete, reproducible results table per scenario; analysis written.")]));
c.push(h2("Week 6 — Writing, polish, buffer, submit"));
c.push(bul("Freeze code (bugfixes only). Write Discussion (incl. deployability / product argument + limitations), Conclusion, Abstract. Final citation verification (CHAOS article ID; cite NIST SP 800-82 Rev. 3; confirm co-engineering survey authors). Diagrams, proofread, format; leave buffer for supervisor review. Submit."));

c.push(h1("4. Checkpoints & gates"));
c.push(tbl([1500,3300,2700],
 ["When","Gate","If it fails"],
 [
  ["End W1","Minimal loop (PLC↔Factory I/O↔OVS) up; contribution locked","Extend into W2; cut nothing yet but flag risk"],
  ["End W2","Reactive loop solid + latency acceptable (CC-4)","Trigger de-scope ladder (§6) immediately"],
  ["End W4","Writing underway (Intro/Bg/Method drafted)","Pause building; writing takes priority"],
  ["End W5","Full results captured","Freeze scope; write up what exists honestly"],
  ["~W6","Submit","—"],
 ]));

c.push(h1("5. Definition of a strong submission"));
c.push(bul("A working CARS engine on the testbed (Tier 3 if achieved; Tier 2 acceptable) with a real S7-1200/1500 and a process that can visibly go unsafe."));
c.push(bul("≥4–5 attack scenarios evaluated with operator-relevant metrics — crucially, zero defence-induced process trips demonstrated."));
c.push(bul("Positioned against the key literature including the safety cluster (Piedrahita, process-aware review, TRITON, IEC 62443)."));
c.push(bul("An explicit deployability / product argument (zone-boundary overlay, brownfield-friendly)."));
c.push(bul("Verified citations; word count per your programme handbook (confirm the exact limit)."));

c.push(h1("6. De-scope ladder (cut in this order if behind)"));
c.push(p("Cut fidelity top-down until the schedule is recoverable. Each cut is honestly reported in the write-up as a scope decision + future work."));
c.push(bul("1. Corporate/IT zone + dual firewalls → single IT/OT boundary."));
c.push(bul("2. Industrial DMZ (historian replica + jump host)."));
c.push(bul("3. Second soft-PLC (OpenPLC)."));
c.push(bul("4. Extra protocols (OPC UA / MQTT) → keep Modbus + S7comm."));
c.push(bul("5. Full IT→OT kill chain → intra-OT attacks only."));
c.push(p([t("Core that must survive every cut: ",{bold:true}),t("real PLC + Factory I/O + OVS + Ryu + one IDS + the CARS engine + the evaluation + the written dissertation. "),t("Never cut: ",{bold:true,color:RED}),t("the contribution, the evaluation with metrics, or the writing.")]));

c.push(h1("7. Dependencies, assumptions & risks"));
c.push(bul([t("Assumption: ",{bold:true}),t("~35–40 h/week available (full-time dissertation). Scale the plan if less.")]));
c.push(bul([t("Dependency: ",{bold:true}),t("the pre-build checklist (devices, installs, USB-Ethernet adapters) is done before/at the start of Week 1, or Week 1 slips.")]));
c.push(bul([t("Risk — Ryu/Python: ",{bold:true}),t("use a Python 3.9/3.10 venv or the os-ken fork if eventlet errors appear.")]));
c.push(bul([t("Risk — Factory I/O S7 link: ",{bold:true}),t("verify PUT/GET + non-optimized block access on the PLC early (Week 1).")]));
c.push(bul([t("Risk — over-building: ",{bold:true}),t("the single biggest threat to marks. The gates and ladder exist to counter it; honour the Week-4 writing gate.")]));

c.push(new Paragraph({spacing:{before:180},children:[new TextRun({text:"Dates are indicative (Wk1 = 6 Jul 2026). Anchor to your actual submission date and confirm the word-count limit in your programme handbook. This plan operationalises the Decision Log; gates map to CC-1/CC-3/CC-4.",size:18,italics:true,color:GREY})]}));

const doc=new Document({creator:"Project CARS",title:"6-Week Execution Plan — CARS",
 styles:{default:{document:{run:{font:"Calibri",size:22,color:"1A1A1A"}}}},
 numbering:{config:[{reference:"b",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:460,hanging:260}}}}]}]},
 sections:[{properties:{page:{size:{width:12240,height:15840},margin:{top:1200,bottom:1200,left:1300,right:1300}}},
  headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"C9D2E2"}},children:[new TextRun({text:"CARS · 6-Week Execution Plan",size:16,color:GREY,italics:true})]})]})},
  footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:16,color:GREY}),new TextRun({children:[PageNumber.CURRENT," of ",PageNumber.TOTAL_PAGES],size:16,color:GREY})]})]})},
  children:c}]});
Packer.toBuffer(doc).then((b)=>{fs.writeFileSync("Reactive_SDN_ICS_6Week_Execution_Plan.docx",b);console.log("written",b.length);});
