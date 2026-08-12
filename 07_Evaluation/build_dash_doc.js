const fs = require('fs');
const d = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
        TableCell, WidthType, BorderStyle, ShadingType, ImageRun, Footer } = d;
const CW = 9360, ACCENT="1F4E79", GREY="595959", HEAD="D6E4F0", MONO="Consolas";
const H1=(t)=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:240,after:110},children:[new TextRun({text:t,bold:true,color:ACCENT,size:29})]});
const H2=(t)=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:160,after:80},children:[new TextRun({text:t,bold:true,color:"2E5E8C",size:24})]});
const P=(runs,opts={})=>new Paragraph({spacing:{after:120,line:276},...opts,children:Array.isArray(runs)?runs:[new TextRun({text:runs,size:21})]});
const T=(text,o={})=>new TextRun({text,size:21,...o});
const CODE=(text)=>new TextRun({text,font:MONO,size:19,color:"B03A2E"});
const bullet=(runs)=>new Paragraph({bullet:{level:0},spacing:{after:70,line:264},children:Array.isArray(runs)?runs:[new TextRun({text:runs,size:21})]});
function cell(text,{w,bold=false,shade=null,mono=false,color=null,size=19}={}) {
  const runs=(Array.isArray(text)?text:[text]).map((t,i)=>new TextRun({text:t,bold,size,font:mono?MONO:undefined,color:color||undefined,break:i>0?1:0}));
  return new TableCell({width:{size:w,type:WidthType.DXA},margins:{top:60,bottom:60,left:90,right:90},
    shading:shade?{type:ShadingType.CLEAR,fill:shade}:undefined,children:[new Paragraph({children:runs})]});
}
function table(widths,rows){return new Table({width:{size:CW,type:WidthType.DXA},columnWidths:widths,
  borders:{top:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"},bottom:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"},
   left:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"},right:{style:BorderStyle.SINGLE,size:4,color:"BFCEDD"},
   insideHorizontal:{style:BorderStyle.SINGLE,size:4,color:"D9E1EA"},insideVertical:{style:BorderStyle.SINGLE,size:4,color:"D9E1EA"}},
  rows:rows.map((r,ri)=>new TableRow({tableHeader:ri===0,children:r.map((c,ci)=>cell(c.t,{w:widths[ci],bold:ri===0||c.bold,shade:ri===0?HEAD:(c.shade||null),mono:c.mono,color:c.color}))}))});}
const kids=[];

// header band
kids.push(new Paragraph({spacing:{before:200,after:20},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Project CARS — Technical Note",color:GREY,size:20})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:8},children:[new TextRun({text:"The CARS Live Console",bold:true,color:ACCENT,size:40})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:60},children:[new TextRun({text:"A discovery-driven, live-sync NOC for the IT/OT fabric",italics:true,color:"2E5E8C",size:24})]}));
kids.push(new Paragraph({alignment:AlignmentType.CENTER,border:{bottom:{style:BorderStyle.SINGLE,size:6,color:ACCENT}},spacing:{after:160}}));

// differentiator callout
kids.push(new Paragraph({shading:{type:ShadingType.CLEAR,fill:"EAF1F8"},spacing:{before:40,after:40},
  border:{left:{style:BorderStyle.SINGLE,size:18,color:ACCENT},top:{style:BorderStyle.SINGLE,size:4,color:"C9D9EA"},bottom:{style:BorderStyle.SINGLE,size:4,color:"C9D9EA"},right:{style:BorderStyle.SINGLE,size:4,color:"C9D9EA"}},
  children:[new TextRun({text:"The differentiator, in one line:  ",bold:true,size:22,color:ACCENT}),
    new TextRun({text:"most ICS/SDN demonstrations show a hand-drawn network diagram beside a live system. The CARS console instead renders the controller’s ",size:22}),
    new TextRun({text:"own live model",bold:true,size:22}),
    new TextRun({text:" — every node, wire, port, and state is discovered, so the picture physically cannot disagree with the network.",size:22})]}));
kids.push(new Paragraph({spacing:{after:120},children:[new TextRun({text:"",size:8})]}));

kids.push(H1("1. Why this is a genuine differentiator"));
kids.push(P([T("A hand-drawn topology is an "),T("assertion",{italics:true}),
  T(" — it says what the author believes the network is. It cannot catch a mis-cabling, a silent device, a spoofed identity, or a link that just failed. The CARS console is the opposite: it is a "),
  T("projection of ground truth",{bold:true}),
  T(". Every element on screen is derived, live, from the SDN controller’s own view of the data plane — the same view it uses to make security decisions. If the console shows it, the controller believes it; if the controller is wrong, the console shows the network’s reality anyway (a link goes red, a host vanishes, a spoof counter climbs).")]));
kids.push(P([T("This makes the console three things at once: an "),T("operator’s situational-awareness tool",{bold:true}),
  T(", a "),T("live proof",{bold:true}),T(" that CARS’s internal model matches the physical fabric, and a "),
  T("debugging instrument",{bold:true}),T(" that has already surfaced real faults a static diagram would have hidden (Section 5).")]));

kids.push(H1("2. How it works — one source of truth to the screen"));
kids.push(P([T("The console has no topology of its own and stores no state. It is a thin renderer over the controller’s read-only feeds. The pipeline is five stages:")]));
try {
  const img=fs.readFileSync('/sessions/great-jolly-pasteur/mnt/Dissertation/Reactive_SDN_ICS/06_Build/dashboard_sync.png');
  kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:60,after:50},children:[new ImageRun({type:"png",data:img,transformation:{width:640,height:414}})]}));
  kids.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:150},children:[new TextRun({text:"Figure 1 — the sync pipeline: the OT fabric feeds the controller’s live model; six JSON feeds drive six parts of the live view.",italics:true,color:GREY,size:18})]}));
} catch(e){kids.push(P("[sync diagram]"));}
kids.push(bullet([T("The ",),T("OT fabric",{bold:true}),T(" (Open vSwitch) emits OpenFlow events, LLDP, and packet-ins to the controller.")]));
kids.push(bullet([T("The ",),T("CARS controller",{bold:true}),T(" builds a live model from them — switch sessions, discovered hosts, LLDP links with ports, port up/down, source-guard drop counters, and a decision audit.")]));
kids.push(bullet([T("It exposes that model as ",),T("six read-only JSON feeds",{bold:true}),T(" on its Event API (:8080).")]));
kids.push(bullet([T("A ",),T("threaded proxy",{bold:true}),T(" on the OT host (Dell #1) serves the single-page console and relays the feeds — so the browser never talks to the control plane directly (no cross-origin exposure).")]));
kids.push(bullet([T("The ",),T("browser",{bold:true}),T(" renders a force-directed SVG and re-polls all six feeds every 1.2 s, reconciling the picture to whatever the controller now believes.")]));

kids.push(H1("3. How every process is kept in sync"));
kids.push(P([T("Each feed owns one part of the picture. Nothing is hardcoded; add a host or pull a cable and the corresponding element changes on the next 1.2 s tick.")]));
kids.push(table([1900,3000,4460],[
  [{t:"Live feed"},{t:"Syncs"},{t:"What you see"}],
  [{t:"/cars/status",mono:true},{t:"Switches, guard, blocks",bold:true},{t:"Switch nodes go grey when a dpid drops; src-guard / arp-guard armed badges; the active-enforcement list; the green/red controller-live dot."}],
  [{t:"/cars/hosts",mono:true},{t:"Nodes",bold:true},{t:"PLC/HMI/supervisory/attacker nodes appear and vanish as the controller learns them — deduped by MAC and auto-placed at their real access switch."}],
  [{t:"/cars/links",mono:true},{t:"Wirings",bold:true},{t:"Switch-to-switch links drawn from LLDP, each end labelled with its real discovered port (e.g. p3 ↔ p1); host links show the access port. Hovering a link reveals the full binding."}],
  [{t:"/cars/ports",mono:true},{t:"Link health",bold:true},{t:"A link turns red/broken the instant its port drops, and the device node greys — physical faults appear within ~1 s."}],
  [{t:"/cars/guard",mono:true},{t:"Anti-spoof telemetry",bold:true},{t:"A running count of spoofed IP/ARP packets dropped at ingress, per protected identity — the guard’s work made visible as numbers."}],
  [{t:"/cars/audit",mono:true},{t:"Decisions + attacks",bold:true},{t:"A dated feed of every brain decision (FORBIDDEN/OPERATIONAL/CRITICAL); a blocked conduit pulses its attacker node red with a glowing block-line to the victim."}],
]));

kids.push(H1("4. The engineering that makes the sync live and trustworthy"));
kids.push(bullet([T("Discovery, not configuration. ",{bold:true}),T("Hosts come from passive ARP/IPv4 snooping (keyed by switch + MAC, so identical-IP cells stay distinct); links come from LLDP with port numbers; liveness comes from OpenFlow port-status. The console reads all of this — it declares none of it.")]));
kids.push(bullet([T("Node placement is inferred, not fixed. ",{bold:true}),T("Each device is placed at its true access switch using an edge-port heuristic (an access port carries one MAC; an uplink carries many), then a small force simulation lays the graph out and lets the operator drag/pin nodes.")]));
kids.push(bullet([T("Reconciliation each tick. ",{bold:true}),T("On every poll the renderer diffs the discovered set against what is drawn — adding new nodes, removing departed ones, and recolouring links/nodes from the latest port and block state — so the view converges to ground truth without a reload.")]));
kids.push(bullet([T("Safe by construction. ",{bold:true}),T("The browser only ever reads; the proxy is threaded (concurrent polls never block) and tolerates client disconnects; and it isolates the browser from the control plane. When the controller is unreachable the console flips to an explicit ‘controller DOWN’ state rather than showing stale green.")]));

kids.push(H1("5. Proof it mirrors reality — faults a static diagram would hide"));
kids.push(P([T("Because the console shows discovered truth, it has repeatedly caught things that a drawn diagram never could — each became a documented finding:")]));
kids.push(bullet([T("Cell 2 isolation: ",{bold:true}),T("LLDP found the ovs1↔gateway link but ")," ",T("no link to ovs2",{bold:true}),T(" — the map correctly showed Cell 2 unlinked, exactly matching the deferred physical transit.")]));
kids.push(bullet([T("ARP flux: ",{bold:true}),T("discovery flagged the insider’s MAC presenting the supervisor’s IP — a real multi-homed-host misconfiguration, fixed once seen.")]));
kids.push(bullet([T("Clone-IP collision: ",{bold:true}),T("both PLCs share an IP; the console’s MAC+switch keying kept them as two distinct nodes where an IP-keyed view would have merged them.")]));
kids.push(bullet([T("Boot-time ARP probes: ",{bold:true}),T("a rebooting PLC briefly announced 0.0.0.0; the console exposed it overwriting a real address, prompting a hardening fix.")]));
kids.push(bullet([T("Restart blindness: ",{bold:true}),T("after a controller restart the console’s empty host list revealed that persistent flows were suppressing re-discovery — driving the clean-slate-on-reconnect fix.")]));

kids.push(H1("6. What it demonstrates, live"));
kids.push(P([T("The console turns the whole thesis into something an examiner can watch happen in real time:")]));
kids.push(bullet([T("Pull an OT cable (or admin-down a port) ",{bold:true}),T("→ that link turns red and the device greys, within ~1 s.")]));
kids.push(bullet([T("Send a spoofed packet ",{bold:true}),T("→ the source-guard drop counter ticks up — the anti-spoofing defence, visible.")]));
kids.push(bullet([T("Launch an attack ",{bold:true}),T("→ the offending node pulses red, a glowing block-line snaps to the victim, and the decision feed logs FORBIDDEN — the reactive loop, on screen.")]));
kids.push(bullet([T("Ping from the supervisor to the same PLC ",{bold:true}),T("→ logged OPERATIONAL and left flowing — the criticality-aware policy, demonstrated side by side.")]));
kids.push(new Paragraph({spacing:{before:120},children:[new TextRun({text:"In short: the console is not a picture of the system — it is the system, watching itself.",italics:true,bold:true,color:ACCENT,size:22})]}));

const doc=new Document({creator:"Amit Kiran Deb",title:"CARS Live Console — Technical Note",
  styles:{default:{document:{run:{font:"Calibri",size:21}}}},
  sections:[{properties:{page:{size:{width:12240,height:15840},margin:{top:1200,bottom:1100,left:1200,right:1200}}},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Project CARS — The Live Console · Technical Note · Amit Kiran Deb",size:16,color:GREY})]})]})},
    children:kids}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync('/sessions/great-jolly-pasteur/mnt/Dissertation/Reactive_SDN_ICS/07_Evaluation/CARS_Live_Console.docx',b);console.log('written bytes:',b.length);});
