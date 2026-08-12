const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageNumber, Header, Footer, Table, TableRow, TableCell, WidthType,
  BorderStyle, ShadingType, LevelFormat, ExternalHyperlink,
} = require("docx");

const ACCENT = "1F3864", ACCENT2 = "2E5496", GREY = "595959", GREEN = "1E7145", AMBER = "9C5700";

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 340, after: 130 },
    children: [new TextRun({ text, bold: true, color: ACCENT, size: 30 })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 90 },
    children: [new TextRun({ text, bold: true, color: ACCENT2, size: 25 })] });
}
function p(runs, opts = {}) {
  const children = Array.isArray(runs) ? runs : [new TextRun({ text: runs, size: 22 })];
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 130, line: 274 }, children, ...opts });
}
function t(text, o = {}) { return new TextRun({ text, size: 22, ...o }); }
function bullet(runs, level = 0) {
  const children = Array.isArray(runs) ? runs : [new TextRun({ text: runs, size: 22 })];
  return new Paragraph({ numbering: { reference: "b", level }, alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 80, line: 270 }, children });
}
function link(url, label) {
  return new ExternalHyperlink({ link: url, children: [new TextRun({ text: label || url, style: "Hyperlink", size: 19 })] });
}

// A single annotated paper entry
let PN = 0;
function paper({ title, meta, why, url, tag }) {
  PN += 1;
  const tagColor = tag === "Essential" ? GREEN : tag === "High" ? ACCENT2 : GREY;
  const out = [];
  out.push(new Paragraph({
    spacing: { before: 130, after: 30 },
    children: [
      new TextRun({ text: `${PN}.  `, bold: true, size: 22, color: ACCENT }),
      new TextRun({ text: title, bold: true, size: 22 }),
      new TextRun({ text: `   [${tag}]`, bold: true, size: 17, color: tagColor }),
    ],
  }));
  out.push(new Paragraph({ spacing: { after: 30 }, indent: { left: 300 },
    children: [new TextRun({ text: meta, italics: true, size: 20, color: GREY })] }));
  out.push(new Paragraph({ spacing: { after: 30 }, indent: { left: 300 }, alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text: "Why it matters: ", bold: true, size: 21, color: ACCENT2 }), new TextRun({ text: why, size: 21 })] }));
  out.push(new Paragraph({ spacing: { after: 120 }, indent: { left: 300 },
    children: [new TextRun({ text: "Link: ", size: 19, color: GREY }), link(url)] }));
  return out;
}

// ---------- Gap analysis table ----------
function gapTable() {
  const cols = [3050, 3550, 2100];
  const header = ["Well covered in the literature", "Under-served gap", "Opportunity for us"];
  function cell(text, { bold=false, fill, head=false } = {}, w) {
    return new TableCell({ width: { size: w, type: WidthType.DXA },
      shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
      margins: { top: 60, bottom: 60, left: 90, right: 90 },
      children: [new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text, bold, size: 18, color: head ? "FFFFFF" : "000000" })] })] });
  }
  const rows = [ new TableRow({ tableHeader: true, children: header.map((h,i)=>cell(h,{bold:true,fill:ACCENT,head:true},cols[i])) }) ];
  const data = [
    ["Detecting attacks (ML/DL/GNN IDS on SWaT/WADI); very high reported accuracy.", "Turning a detection into a SAFE, automated network action that respects the physical process.", "Safety-constrained response engine."],
    ["SDN blocking / redirection / honeypot primitives demonstrated individually.", "A unified controller that ingests events from ANY external source and selects device-aware responses.", "Source-agnostic event API + policy engine."],
    ["Honeypots & MTD as standalone tactics; LLM-enriched deception emerging.", "Orchestrating multiple responses (block, mirror, redirect, re-route, deceive) under one risk-aware policy.", "Response orchestration layer."],
    ["Control-plane logic and cloud/NFV analytics.", "Line-rate enforcement on the switch (P4) coupled to slower controller reasoning.", "Hybrid data-plane / control-plane loop."],
    ["Controller single-point-of-failure noted; BFT/multi-controller in generic SDN.", "Reactive ICS response that stays available and correct while the controller itself is attacked.", "Resilient reactive control plane."],
    ["High accuracy on offline datasets.", "Real-time closed-loop evaluation with detection-to-mitigation latency and safety metrics.", "Reproducible closed-loop testbed."],
  ];
  data.forEach((r,idx)=>{ const fill = idx%2 ? "EDF1F8" : "FFFFFF"; rows.push(new TableRow({ children: r.map((c,i)=>cell(c,{fill},cols[i])) })); });
  return new Table({ columnWidths: cols, width: { size: cols.reduce((a,b)=>a+b,0), type: WidthType.DXA },
    borders: { top:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"}, bottom:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},
      left:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"}, right:{style:BorderStyle.SINGLE,size:4,color:"AAB4C8"},
      insideHorizontal:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"}, insideVertical:{style:BorderStyle.SINGLE,size:2,color:"CCD4E2"} }, rows });
}

const c = [];

// Title
c.push(new Paragraph({ spacing: { before: 300 } }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: "Reactive SDN for Securing ICS Environments", bold: true, size: 36, color: ACCENT })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
  children: [new TextRun({ text: "Curated Reading List, Literature-Gap Analysis & Innovation Directions", size: 26, color: ACCENT2, italics: true })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 6, color: ACCENT } }, spacing: { after: 40 }, children: [new TextRun({ text: "" })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 260 },
  children: [new TextRun({ text: "Deep literature sweep across 10 sub-domains · 40+ sources · July 2026", size: 20, color: GREY, italics: true })] }));

// How to use
c.push(h1("How to use this document"));
c.push(p([
  t("This is a prioritized, annotated map of the research most relevant to building a reactive SDN system for ICS security. Each entry is tagged "),
  t("[Essential]", { bold: true, color: GREEN }), t(" (read first — foundational or closest to our objective), "),
  t("[High]", { bold: true, color: ACCENT2 }), t(" (strong, directly applicable), or "),
  t("[Reference]", { bold: true, color: GREY }),
  t(" (breadth, datasets, or context). Papers are grouped into ten themes. After the reading list, a gap analysis contrasts what the field already does well against the white space our project can own, followed by concrete innovation directions and a suggested reading order."),
]));
c.push(p([
  t("Bottom line up front: ", { bold: true }),
  t("the market and literature are saturated with ever-more-accurate "),
  t("detection", { italics: true }),
  t(", but thin on "),
  t("safe, automated, device-aware ", { italics: true }),
  t("network "),
  t("response", { italics: true }),
  t(" that provably does not endanger the physical process. That response gap — plus real-time closed-loop evaluation and controller resilience — is where an innovative, defensible contribution lies."),
]));

// THEME 1
c.push(h1("Theme 1 — Foundations & surveys (start here)"));
c.push(p("These frame the whole problem space and let you position the project quickly."));
paper({ tag:"Essential", title:"Software-Defined Networking approaches for intrusion response in Industrial Control Systems: A survey",
  meta:"X. Etxezarreta, I. Garitano, M. Iturbe, U. Zurutuza — Int. J. Critical Infrastructure Protection, 42:100615, 2023.",
  why:"The anchor reference. Provides the four-family taxonomy (dynamic filtering, survivability, MTD, honeypots), maps ICS security requirements to SDN, and lists open challenges — the exact scaffolding for our project.",
  url:"https://www.sciencedirect.com/science/article/pii/S1874548223000288" }).forEach(x=>c.push(x));
paper({ tag:"Essential", title:"Detection and mitigation of cyber-attacks in SDN using ML/DL: a systematic literature review, challenges and future directions",
  meta:"Springer, International Journal of Information Security, 2025.",
  why:"Current, systematic map of ML/DL for SDN security with an explicit future-directions section. Best single source for understanding where the AI-for-SDN field is and what remains unsolved.",
  url:"https://link.springer.com/article/10.1007/s10207-025-01114-z" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Machine learning in ICS security: current landscape, opportunities and challenges",
  meta:"Springer, Journal of Intelligent Information Systems, 2022.",
  why:"Grounds the ICS-specific constraints (data scarcity, safety, real-time) that make naive ML transplants fail. Good for motivating why response — not just detection — is the hard part.",
  url:"https://link.springer.com/article/10.1007/s10844-022-00753-1" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Guide to Industrial Control Systems (ICS) Security (NIST SP 800-82 Rev. 2)",
  meta:"K. Stouffer et al., NIST Special Publication 800-82 Rev. 2, 2015 (Rev. 3 draft newer).",
  why:"The canonical requirements document. Cite it for the availability/integrity-over-confidentiality priority and the mandate that controls must not disrupt the process.",
  url:"https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-82r2.pdf" }).forEach(x=>c.push(x));

// THEME 2
c.push(h1("Theme 2 — SDN dynamic response & incident handling for ICS"));
c.push(p("The core mechanism of the project: alert-to-action pipelines that preserve the process."));
paper({ tag:"Essential", title:"Leveraging Software-Defined Networking for Incident Response in Industrial Control Systems",
  meta:"A. F. M. Piedrahita, V. Gaur, J. Giraldo, Á. A. Cárdenas, S. J. Rueda — IEEE Software, 35(1):44–50, 2018.",
  why:"The closest prior work to our objective: IDS + SDN/NFV substitutes estimated values for anomalous sensor readings so the process keeps running safely. The template for safety-preserving response.",
  url:"https://www.scitepress.org/Papers/2019/73595/73595.pdf" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Enabling Dynamic Network Access Control with Anomaly-based IDS and SDN",
  meta:"ACM Int. Workshop on Security in SDN & NFV (SDN-NFV Sec), 2019.",
  why:"Clean formalization of the IDS→controller→flow-rule loop and the allow/block/mirror/redirect action set our system must implement.",
  url:"https://dl.acm.org/doi/10.1145/3309194.3309199" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Securing ICS networks: SDN-based Automated Traffic Control and MTD Defensive Framework against DDoS attacks",
  meta:"Computer Communications, Elsevier, 2025.",
  why:"Recent, combines automated SDN traffic control with MTD for ICS — a working example of orchestrating more than one response type, and a benchmark to beat.",
  url:"https://www.sciencedirect.com/science/article/pii/S0140366425002099" }).forEach(x=>c.push(x));

// THEME 3
c.push(h1("Theme 3 — AI-driven detection & autonomous response"));
c.push(p("Where the frontier (and most of the hype) sits: deep learning IDS, and — more relevant to us — learning-based automated response."));
paper({ tag:"High", title:"Deep reinforcement learning-based intrusion detection scheme for software-defined networking",
  meta:"Nature Scientific Reports, 2025.",
  why:"Representative of RL applied inside SDN. Read it for how the state/action/reward is framed — directly transferable if we make response (not detection) the RL agent's job.",
  url:"https://www.nature.com/articles/s41598-025-24869-w" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Optimal Security Response to Network Intrusions in IT Systems",
  meta:"K. Hammar (PhD work), arXiv:2502.02541, 2025.",
  why:"Rigorous decision-theoretic framing of automated response (when to block/redirect/isolate) using control theory and game theory — the theoretical backbone our safety-constrained response engine currently lacks in the ICS literature.",
  url:"https://arxiv.org/pdf/2502.02541" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Non-local attention enhanced deep learning for robust cyberattack detection in IIoT-based SCADA systems",
  meta:"Nature Scientific Reports, 2026.",
  why:"State-of-the-art SCADA detection (attention-based). Use as the detection front-end so the project can focus its novelty on response rather than re-inventing a classifier.",
  url:"https://www.nature.com/articles/s41598-026-37146-1" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Transformers and Large Language Models for Efficient Intrusion Detection Systems: A Comprehensive Survey",
  meta:"arXiv:2408.07583, 2024.",
  why:"Breadth on transformer/LLM IDS and their cost/latency trade-offs — important because heavyweight models clash with ICS real-time budgets.",
  url:"https://arxiv.org/pdf/2408.07583" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Design of an AI-driven secure 5G-SDN framework with federated reinforcement learning for anomaly detection, mitigation and forensics",
  meta:"PMC (open access), 2025.",
  why:"Shows the full detect-mitigate-forensics loop with federated RL over SDN — an architectural pattern to borrow, adapted to ICS constraints.",
  url:"https://pmc.ncbi.nlm.nih.gov/articles/PMC12929375/" }).forEach(x=>c.push(x));

// THEME 4
c.push(h1("Theme 4 — In-network defense with programmable data planes (P4)"));
c.push(p("The route to line-rate enforcement that meets ICS latency budgets — a strong differentiator versus control-plane-only designs."));
paper({ tag:"High", title:"P4Control: Line-Rate Cross-Host Attack Prevention via In-Network Information Flow Control",
  meta:"IEEE Symposium on Security and Privacy (S&P), 2024 — arXiv:2405.14970.",
  why:"Top-tier venue proof that meaningful security policy can run at line rate on programmable switches + eBPF. Evidence that data-plane response is feasible, not just theoretical.",
  url:"https://arxiv.org/pdf/2405.14970" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Leveraging Data Plane Programmability to enhance service orchestration at the edge: a focus on industrial security",
  meta:"Computer Networks, Elsevier, 2024 — S1389128624002299.",
  why:"Directly ICS/industrial-focused P4 security. Bridges programmable data planes to OT protocols and orchestration — a near-neighbour to our hybrid enforcement idea.",
  url:"https://www.sciencedirect.com/science/article/pii/S1389128624002299" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"A Two-level Intrusion Detection System for ICS Networks using P4",
  meta:"G. K. Ndonda, R. Sadre — ICS-CSR, 2018.",
  why:"L1 P4 Modbus allowlist on the switch, L2 DPI feedback updates L1 — the reference design for closing the detect-to-block loop at line rate in ICS.",
  url:"https://www.scienceopen.com/hosted-document?doi=10.14236/ewic/ICS2018.4" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"A Protocol-Aware P4 Pipeline for MQTT Security and Anomaly Mitigation in Edge IoT Systems",
  meta:"arXiv:2601.07536, 2026.",
  why:"Shows protocol-aware P4 pipelines for an IIoT protocol — the pattern generalizes to Modbus/DNP3/OPC UA in our data-plane filter.",
  url:"https://arxiv.org/pdf/2601.07536" }).forEach(x=>c.push(x));

// THEME 5
c.push(h1("Theme 5 — Digital twins for ICS security"));
c.push(p("A fast-rising area: a safe virtual replica to test responses before applying them to the live process — a natural pairing with reactive SDN."));
paper({ tag:"High", title:"TwinSec-IDS: An Enhanced IDS in SDN-Digital-Twin-Based Industrial Cyber-Physical Systems",
  meta:"Krishnaveni et al. — Concurrency and Computation: Practice and Experience (Wiley), 2025.",
  why:"Explicitly fuses SDN + digital twin + hybrid deep learning for ICPS. The closest published system to a 'twin-validated reactive SDN', and therefore both inspiration and the state of the art to advance.",
  url:"https://onlinelibrary.wiley.com/doi/10.1002/cpe.8334" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"Digital Twin-Enhanced Incident Response for Cyber-Physical Systems",
  meta:"ACM ARES, 2023.",
  why:"Frames the twin as a sandbox for validating incident-response actions — directly supports our 'simulate the response before you commit it' safety mechanism.",
  url:"https://dl.acm.org/doi/10.1145/3600160.3600195" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Digital Twin-Driven Intrusion Detection for Industrial SCADA: A Cyber-Physical Case Study",
  meta:"MDPI Sensors, 25(16):4963, 2025.",
  why:"Concrete SCADA case study; useful methodology and metrics for a twin-in-the-loop evaluation.",
  url:"https://www.mdpi.com/1424-8220/25/16/4963" }).forEach(x=>c.push(x));

// THEME 6
c.push(h1("Theme 6 — Deception & honeypots (SDN-steered)"));
c.push(p("The 'redirect for deeper inspection' branch of the project, now being supercharged with AI-generated decoy content."));
paper({ tag:"High", title:"Reactive cyber deception: stealth-based adaptive redirection to on-demand honeypots with AI-driven data generation",
  meta:"Computer Networks / Computers & Security, Elsevier, 2026 — S138912862600215X.",
  why:"State of the art: SDN controller performs stealthy TCP redirection to on-demand honeypots, with LLM-generated decoy data. A vivid, recent instance of exactly the redirect response our system offers — raise our game to this level.",
  url:"https://www.sciencedirect.com/science/article/pii/S138912862600215X" }).forEach(x=>c.push(x));
paper({ tag:"High", title:"D3O-IIoT: Deep reinforcement learning-driven dynamic deception orchestration for Industrial IoT security",
  meta:"PMC (open access), 2025.",
  why:"RL coordinates honeypots + MTD + fake telemetry + node isolation from real-time threat signals — the multi-response orchestration idea, applied to IIoT. Strong prior art for our orchestration layer.",
  url:"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12816736/" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"MimePot: a Model-based Honeypot for Industrial Control Networks",
  meta:"G. Bernieri, M. Conti, F. Pascucci — IEEE SMC, 2019.",
  why:"SDN redirects data-integrity attacks to a process-modelling honeypot — a concrete ICS honeypot design referenced by the anchor survey.",
  url:"https://www.sciencedirect.com/science/article/pii/S1874548223000288" }).forEach(x=>c.push(x));

// THEME 7
c.push(h1("Theme 7 — Moving Target Defense (MTD)"));
c.push(p("Proactive obfuscation that complements reactive filtering; strongest evidence base is in the smart-grid subdomain."));
paper({ tag:"High", title:"Survey of Moving Target Defense in Power Grids: Design Principles, Tradeoffs, and Future Directions",
  meta:"arXiv:2409.18317, 2024.",
  why:"The most complete recent MTD survey for critical infrastructure. Read for design principles and the cost/effectiveness trade-offs that any reactive-MTD trigger must respect.",
  url:"https://arxiv.org/pdf/2409.18317" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"CHAOS: An SDN-Based Moving Target Defense System",
  meta:"Y. Shi et al. — Security and Communication Networks, 2017.",
  why:"Widely cited SDN MTD implementation (host/port/path obfuscation) — the canonical mechanism reference.",
  url:"https://www.hindawi.com/journals/scn/2017/3659167/" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Leveraging Network Reconfiguration to Mitigate Stealthy FDI Attacks in Smart Grid SCADA Systems",
  meta:"Springer, 2025.",
  why:"Reactive reconfiguration that defeats a large share of stealthy false-data-injection attacks while preserving performance — a survivability response worth emulating.",
  url:"https://link.springer.com/chapter/10.1007/978-3-032-01904-2_19" }).forEach(x=>c.push(x));

// THEME 8
c.push(h1("Theme 8 — Zero Trust & micro-segmentation for OT"));
c.push(p("The dominant industry architecture direction; SDN is the natural enforcement substrate for dynamic, identity-aware segmentation."));
paper({ tag:"High", title:"The Journey to Zero Trust Microsegmentation (CISA guidance)",
  meta:"U.S. CISA, 2025.",
  why:"Authoritative professional/industry guidance. Grounds our device-aware policy in the zero-trust framing regulators and asset owners now expect — important for real-world relevance.",
  url:"https://www.cisa.gov/sites/default/files/2025-07/ZT-Microsegmentation-Guidance-Part-One_508c.pdf" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Zero Trust Architecture: A Systematic Literature Review",
  meta:"arXiv:2503.11659, 2025.",
  why:"Academic mapping of ZTA — positions dynamic, per-flow SDN enforcement within the broader zero-trust research landscape.",
  url:"https://arxiv.org/pdf/2503.11659" }).forEach(x=>c.push(x));

// THEME 9
c.push(h1("Theme 9 — Deterministic security & Time-Sensitive Networking"));
c.push(p("The constraint that separates ICS from IT security: responses must not break bounded latency. TSN + SDN is the emerging way to guarantee it."));
paper({ tag:"High", title:"Software-Defined Time-Sensitive Networking for Cross-Domain Deterministic Transmission",
  meta:"MDPI Electronics, 13(7):1246, 2024.",
  why:"Shows how SDN and TSN combine to keep latency bounded — essential if our reactive rule changes must not violate control-loop deadlines.",
  url:"https://www.mdpi.com/2079-9292/13/7/1246" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"Time-Sensitive Networking for Industrial Automation: Current Advances and Future Directions",
  meta:"ACM Computing Surveys, 2024 — doi:10.1145/3695248.",
  why:"Comprehensive TSN survey; use to argue and quantify the real-time envelope our security actions operate within.",
  url:"https://dl.acm.org/doi/10.1145/3695248" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"P4-PSFP: P4-Based Per-Stream Filtering and Policing for Time-Sensitive Networking",
  meta:"arXiv:2311.07385, 2023.",
  why:"Marries P4 data-plane enforcement with TSN policing — a template for security filtering that is deterministic by construction.",
  url:"https://arxiv.org/pdf/2311.07385" }).forEach(x=>c.push(x));

// THEME 10
c.push(h1("Theme 10 — Resilient control plane, datasets & testbeds"));
c.push(p("Making the controller trustworthy under attack, and evaluating the whole system credibly."));
paper({ tag:"High", title:"Intrusion Tolerance for Networked Systems through Two-Level Feedback Control",
  meta:"K. Hammar, R. Stadler — arXiv:2404.01741, 2024.",
  why:"Principled intrusion-tolerant control that keeps a system operating while compromised — directly relevant to keeping our reactive controller available and correct under attack.",
  url:"https://arxiv.org/pdf/2404.01741" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"ITC: Intrusion Tolerant Controller for multicontroller SDN architecture",
  meta:"Computers & Security, Elsevier, 2023 — S0167404823002614.",
  why:"Concrete intrusion-tolerant SDN controller design; the resilience building block for a reactive control plane.",
  url:"https://www.sciencedirect.com/science/article/abs/pii/S0167404823002614" }).forEach(x=>c.push(x));
paper({ tag:"Essential", title:"SWaT, WADI and HAI ICS security datasets / testbeds (iTrust, Singapore)",
  meta:"Secure Water Treatment (SWaT), Water Distribution (WADI), HIL-Augmented ICS (HAI).",
  why:"The de-facto benchmarks for ICS security. Use for repeatable, comparable evaluation; note their limitation (offline, detection-oriented) which motivates our closed-loop testbed.",
  url:"https://itrust.sutd.edu.sg/itrust-labs_datasets/" }).forEach(x=>c.push(x));
paper({ tag:"Reference", title:"MiniCPS: A Toolkit for Security Research on CPS Networks",
  meta:"D. Antonioli, N. O. Tippenhauer — ACM CPS-SPC, 2015.",
  why:"The emulation backbone (used by Piedrahita et al.) for building a Ryu + Mininet + Modbus reactive testbed with realistic physical-process behaviour.",
  url:"https://dl.acm.org/doi/10.1145/2808705.2808715" }).forEach(x=>c.push(x));

// GAP ANALYSIS
c.push(h1("Literature & market gap analysis"));
c.push(p([
  t("Across all ten themes a consistent asymmetry appears. An enormous, still-growing body of work — much of it reporting near-perfect accuracy on SWaT/WADI/HAI — is devoted to "),
  t("detecting", { italics: true }),
  t(" attacks. Far less work addresses the harder, higher-value question our project targets: given a detection, what network action should the controller take, and how do we guarantee that action does not itself harm the physical process? The professional/industry signal points the same way — OT ransomware rose ~87% in 2024 and internet-exposed ICS devices keep climbing, so asset owners increasingly need automated "),
  t("response", { italics: true }),
  t(", not more alerts. The table below summarizes the white space."),
]));
c.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
c.push(gapTable());
c.push(new Paragraph({ spacing: { after: 140 }, children: [] }));
c.push(p("Five gaps stand out as genuinely under-served and defensible:"));
c.push(bullet([t("The response gap. ", { bold: true }), t("Detection is commoditized; safe, automated, reversible response in ICS is not. Only Piedrahita et al. and a handful of others treat process safety as a first-class constraint on the action.")]));
c.push(bullet([t("Source-agnostic orchestration. ", { bold: true }), t("Systems bind to one detector and one response. A controller that ingests standardized events from any external service and orchestrates block / mirror / redirect / re-route / deceive under one risk-aware policy does not yet exist for ICS.")]));
c.push(bullet([t("Hybrid data-plane / control-plane loops. ", { bold: true }), t("P4 line-rate enforcement and controller-level reasoning are studied separately; coupling fast in-network mitigation to slower, smarter controller decisions is largely open.")]));
c.push(bullet([t("Twin-validated, safety-constrained automation. ", { bold: true }), t("Digital twins are used for detection, rarely to pre-validate a response before it touches the live process — a concrete way to make automation trustworthy.")]));
c.push(bullet([t("Closed-loop, real-time evaluation. ", { bold: true }), t("The field evaluates on offline datasets; detection-to-mitigation latency, process-safety preservation, and controller resilience under attack are seldom measured together.")]));

// INNOVATION
c.push(h1("Where we can innovate — differentiated directions"));
c.push(p("Synthesizing the gaps into buildable, publishable contributions for this project:"));
c.push(bullet([t("A safety-constrained reactive response engine. ", { bold: true }), t("Formalize response selection (à la Hammar's optimal-response work) with an explicit ICS safety envelope, so an automated action is only applied if it provably keeps the process within safe bounds — otherwise it degrades gracefully (mirror/redirect instead of block).")]));
c.push(bullet([t("A source-agnostic event-to-action API + policy engine on Ryu. ", { bold: true }), t("Standardize the interface so any IDS/asset-discovery/anomaly service can drive the controller, and make responses device-aware (block an unseen device; redirect a critical service) — the exact behaviour in the project's problem statement, generalized.")]));
c.push(bullet([t("A hybrid enforcement loop. ", { bold: true }), t("Push allowlist/rate-limit filtering to a P4 data plane for line-rate, deterministic mitigation, while the Ryu controller performs slower risk-aware reasoning and updates the fast path — meeting TSN-style latency budgets.")]));
c.push(bullet([t("Twin-in-the-loop response validation. ", { bold: true }), t("Before committing a disruptive action, simulate it on a lightweight digital twin/MiniCPS model and apply only if the predicted process state stays safe — turning digital twins from a detection aid into a safety gate.")]));
c.push(bullet([t("Orchestrated, escalating deception. ", { bold: true }), t("Extend redirect-to-honeypot with on-demand, LLM-enriched decoys, escalated by policy — combining Themes 3 and 6 into a graduated response ladder rather than a binary allow/block.")]));
c.push(bullet([t("A resilient reactive control plane + a closed-loop benchmark. ", { bold: true }), t("Pair the reactive logic with intrusion-tolerant control so it survives attacks on the controller itself, and publish a reproducible testbed that measures detection-to-mitigation latency, safety preservation, and resilience together — a contribution the community currently lacks.")]));
c.push(p([
  t("Highest-leverage single thesis: ", { bold: true }),
  t("a safety-constrained, source-agnostic reactive SDN controller on Ryu that validates each response against a digital twin and enforces at the P4 data plane. It sits precisely in the intersection of the five gaps above — novel, feasible on the existing Ryu/Mininet/MiniCPS toolchain, and directly aligned with the project's stated objective."),
]));

// Suggested order
c.push(h1("Suggested reading order"));
c.push(p("If time is limited, read in this sequence: (1) the Etxezarreta survey for the map; (2) Piedrahita et al. for the closest prior system; (3) the 2025 ML/DL-for-SDN systematic review for the AI frontier; (4) Hammar's optimal-response work for the theory of safe response; (5) P4Control and the industrial-P4 paper for line-rate enforcement; (6) TwinSec-IDS and the ARES digital-twin incident-response paper for twin-in-the-loop; (7) the reactive-deception paper for the redirect branch; then skim the remaining themes as needed. Everything above is captured in the project README status so you can track what you have read."));

c.push(new Paragraph({ spacing: { before: 220 }, children: [
  new TextRun({ text: "Sourcing note: entries were gathered via a structured web sweep across ten sub-domains (July 2026). Venue/year are given as found; verify exact bibliographic details against the publisher of record before formal citation. A few items are attributed via the Etxezarreta et al. (2023) survey where the original is paywalled.", size: 18, italics: true, color: GREY }),
] }));

const doc = new Document({
  creator: "Reactive SDN for ICS — Research Project",
  title: "Reactive SDN for ICS — Curated Reading List & Gap Analysis",
  styles: { default: { document: { run: { font: "Calibri", size: 22, color: "1A1A1A" } } } },
  numbering: { config: [{ reference: "b", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 260 } } } } ] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1200, bottom: 1200, left: 1300, right: 1300 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "C9D2E2" } },
      children: [new TextRun({ text: "Reactive SDN for ICS · Reading List & Gap Analysis", size: 16, color: GREY, italics: true })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ text: "Page ", size: 16, color: GREY }),
        new TextRun({ children: [PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 16, color: GREY }) ] })] }) },
    children: c,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync("Reactive_SDN_ICS_Reading_List_and_Gap_Analysis.docx", buf); console.log("written", buf.length, "papers", PN); });
