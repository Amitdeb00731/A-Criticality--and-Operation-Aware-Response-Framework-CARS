# CARS v0.7 - brain + discovery + data-plane source-guard (two-table) + ASSET CRITICALITY (decision+response).
import json, time, os, secrets
import eventlet
from eventlet import wsgi
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ether_types, arp, ipv4
from os_ken.lib import hub
from os_ken.topology import event as topoev

REGISTRY = {
    "192.168.2.10": {"role": "plc",       "cell": 1, "name": "PLC1"},
    "192.168.2.9":  {"role": "hmi",       "cell": 1, "name": "HMI1"},
    "192.168.3.10": {"role": "plc",       "cell": 2, "name": "PLC2 (via Dell#3 NAT)"},
    "192.168.3.9":  {"role": "hmi",       "cell": 2, "name": "HMI2 (via Dell#3 NAT)"},
    "192.168.2.30": {"role": "historian", "name": "Historian / Node-RED collector (Cell-1)"},
    "192.168.2.1":  {"role": "gateway",   "name": "OT-FW (IT/DMZ boundary)"},
    "192.168.2.20": {"role": "plc",         "name": "PLC-MB (Modbus sim)"},   # A3
    "192.168.2.31": {"role": "scada",       "name": "SCADA / Operator (Modbus master)"},  # role FIXED: scada (was supervisory) - activates scada rulebook rows
    "192.168.2.66": {"role": "unknown",     "name": "Attacker (Modbus)"},     # A3
    "192.168.2.55": {"role": "ews", "name": "Engineering workstation (TIA, Windows)"},
    "192.168.2.45": {"role": "remediation", "name": "CARS state-maintenance agent"},
    # PEN-TEST (black-box): .2.77 UNREGISTERED entirely -> genuine default-unknown. Restore this line to re-enable the trusted-insider scenario:
    # "192.168.2.77": {"role": "supervisory", "name": "Insider workstation (Kali VM, OT segment)"},
    "192.168.3.66": {"role": "historian",   "name": "Historian / Node-RED collector (Cell-2 face, ins2 seam)"},  # role FIXED: historian (was supervisory) - same collector as .2.30
}
# ROLE MODEL (fixed, one role per IP; everything unregistered => 'unknown' => strict default-deny + dangerous ops FORBIDDEN):
#   plc: .2.10/.3.10/.2.20 | hmi: .2.9/.3.9 | historian: .2.30/.3.66 (the collector) | ews: .2.55 | scada: .2.31
#   remediation: .2.45 | gateway: .2.1 | unknown: .2.66/.2.67/.2.77 + all else
AUDIT = "/home/msclab/cars/cars_audit.log"

GUARD_ENABLED = True
ARP_GUARD_ENABLED = True
BINDINGS = [
    (1, 1, "e0:dc:a0:63:98:09", "192.168.2.10"),
    (1, 2, "e0:dc:a0:62:b7:4c", "192.168.2.9"),
    (2, 1, "e0:dc:a0:46:ff:ce", "192.168.2.10"),
    (2, 2, "e0:dc:a0:5c:60:44", "192.168.2.9"),
    (3, 3, "de:5a:28:ae:96:03", "192.168.2.30"),
    # #26 RETROFIT (CC-92, 2026-07-29): anti-spoof the TRUSTED SEAMS whose identities carry elevated conduit privileges,
    # so an attacker cannot steal allowlisted PLC-write access by spoofing them. All on ovsgw (dpid 3). Transit-safe:
    # cross-switch traffic arrives on ovs1 via the uplink (prio-150 GOTO) above the prio-100 spoof-drop — same path .2.30
    # already uses and works. Attacker seams / honeypot / mirror / IT uplinks deliberately left UNBOUND (untrusted).
    (3, 10, "02:00:00:00:02:31", "192.168.2.31"),  # scada (opns / opr)
    (3, 14, "92:b7:80:63:54:56", "192.168.2.45"),  # remediation (remns / rem0)
    (3,  7, "02:00:00:00:02:20", "192.168.2.20"),  # modbus server (mbns / mbplc)
    (3, 12, "b4:e9:b8:a4:ce:46", "192.168.2.55"),  # CC-98: EWS/Factory-IO host (enx00e04c680018 port) - anti-spoof the
                                                   # trusted process-I/O identity so the operational grant can't be stolen.
]
UPLINKS = {1: [3], 3: [1], 2: []}
PROTECTED_IPS = sorted({b[3] for b in BINDINGS})

BLOCK_TIMEOUT = 30          # A1/P1: conduit blocks auto-expire (self-heal); renewed while the attack persists

THROTTLE_RATE = 20
THROTTLE_BURST = 10
RESPONSES = ("ALLOW", "MONITOR", "THROTTLE", "DEFLECT", "ISOLATE", "BLOCK", "REFUSE")
SHARED_ROLES = {"gateway"}   # Gap-2: NAT/collapse points -> conduit BLOCK, never whole-source ISOLATE
ESCALATE = 3
RATE_WINDOW = 3.0           # A5: sensor-side window (s) over which an op's burst is counted (in snort_bridge)
FLOOD_RATE  = 5.0           # A5: op rate (ops/s) above which a source is treated as FLOODING -> graded/accelerated response
FLOOD_EXEMPT = {"192.168.2.55"}   # CC-98: legit high-rate process-I/O hosts (Factory IO HIL sim) - fast cyclic polling is
                                  # normal operation, not a volumetric DoS. Anti-spoof-bound so the exemption can't be stolen.
HONEYPOT_IP = "192.168.3.99"
HONEYPOT_MAC = "02:00:00:00:03:99"
# ---- SDN Phase 1: STATEFUL (conntrack) reply-aware A2 policy ----
# False = classic L3/L4 default-deny (unchanged, proven). True = ct()-based: default-deny protects an asset
# from UNSOLICITED new connections while STILL passing the return traffic of its OWN sessions (+est) -> lets us
# shield CLIENTS like HMIs. Install is fail-safe (falls back to classic on any error) so the process is never at risk.
STATEFUL = True    # Phase-1 ENABLED (CC-89): conntrack reply-aware A2. Set False to revert to classic L3/L4 default-deny.
CT_UNTRK = (0x00, 0x20)   # -trk  (untracked)
CT_NEW   = (0x21, 0x21)   # +trk +new
CT_EST   = (0x22, 0x22)   # +trk +est (established / reply direction of an allowed conn)
# ---- A2/P1: proactive default-deny + declarative allowlist (conduit/port level, L3/L4) ----
ALLOWLIST = [
    ("192.168.2.31", "192.168.2.20", 6, 502),   # operator -> Modbus PLC (TCP 502)
    ("192.168.2.9",  "192.168.2.10", 6, 102),   # A2-P2: HMI1 -> real PLC1 S7CommPlus (only legit source, observed)
    ("192.168.2.31", "192.168.2.10", 6, 102),   # PD-5: eng station -> PLC1 S7
    ("192.168.3.66", "192.168.3.10", 6, 102),   # PLC2-2: Cell-2 eng station -> PLC2 S7
    # F2: 4 conduits present in runtime a2_policy.json but absent from this seed - added so a cold re-seed == runtime.
    # PEN-TEST (black-box): .2.77 test conduits removed so the Kali is an UNTRUSTED attacker (matches runtime a2_policy allow=8). Restore to re-enable trusted-insider scenario:
    # ("192.168.2.77", "192.168.2.10", 6, 102),   # insider (Kali) -> PLC1 S7   (TEST conduit, VD-1; A3+criticality still gate ops)
    # ("192.168.2.77", "192.168.2.20", 6, 502),   # insider (Kali) -> Modbus PLC (TEST conduit)
    ("192.168.2.55", "192.168.2.10", 6, 102),   # EWS -> PLC1 S7 (engineering)
    ("192.168.2.55", "192.168.2.9",  6, 102),   # CC-98c: EWS -> HMI1 (KTP700) engineering download conduit (TIA -> panel)
    ("192.168.2.45", "192.168.2.10", 6, 102),   # remediation agent -> PLC1 S7 (restores)
    # Node-RED historian-collector (.2.30, sources from sup0) -> READ-only telemetry conduits (writes still CONTROL->FORBIDDEN + criticality-elevated).
    ("192.168.2.30", "192.168.2.10", 6, 102),   # Historian/Node-RED -> PLC1 S7 READ (telemetry poll)
    ("192.168.2.30", "192.168.2.20", 6, 502),   # Historian/Node-RED -> Modbus PLC READ (telemetry poll)
]
DEFAULT_DENY = [
    (None, "192.168.2.20"),   # Modbus PLC - all switches
    (1,    "192.168.2.10"),   # real PLC1 - Cell-1 (dpid 1) ONLY (A2/CC-43: .2.10 shared IP + NAT on ovs2)
    # HMI shield RESTORED under STATEFUL (CC-89): default-deny on the HMI is now SAFE because ct() +est passes the
    # HMI's own replies. (Under classic/STATEFUL=False these would blank the HMI -> keep them only with STATEFUL=True.)
    (1,    "192.168.2.9"),    # HMI1 shielded from recon (Cell-1) - safe under stateful (+est replies pass)
    (2,    "192.168.2.9"),    # HMI (Cell-2 clone on ovs2) shielded - safe under stateful
]

def role_of(ip):
    return REGISTRY.get(ip, {}).get("role", "unknown")

# ---- ASSET CRITICALITY (see CRITICALITY_FRAMEWORK.md) - CCE consequence + CISA taxonomy + attack-path centrality ----
# ACL of the PROTECTED (destination) asset. Modulates BOTH the decision (grey-zone SENSITIVE->FORBIDDEN on CRITICAL,
# bounded by the maintenance window + the safety cap) and the response (escalation speed, floor, flood, block duration).
CRITICALITY = {
    "192.168.2.10": "CRITICAL",   # PLC1 - primary tank, overflow / safety hazard
    "192.168.3.10": "HIGH",       # PLC2 - downstream buffer, production impact
    "192.168.2.9":  "HIGH",       # HMI1 - operator visibility on the critical tank
    "192.168.3.9":  "MEDIUM",     # HMI2
    "192.168.2.30": "MEDIUM",     # Historian/SCADA (pivot chokepoint - centrality bump)
    "192.168.2.20": "LOW",        # Modbus sim (test asset)
}
CW = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
def crit_of(ip): return CRITICALITY.get(ip, "LOW")     # unset -> LOW -> behaves exactly as pre-criticality (backward-compatible)

RULEBOOK = [
    ("hmi",         "plc", "any",   "CRITICAL"),
    ("plc",         "hmi", "any",   "CRITICAL"),
    # F2: authorise the CARS remediation agent (.2.45) BEFORE the dangerous-ops block (first-match-wins),
    # so its last-good CONTROL restores classify OPERATIONAL, not FORBIDDEN. Mirrors runtime rulebook.json.
    ("remediation", "plc", "CONTROL", "OPERATIONAL"),
    ("remediation", "plc", "any",     "OPERATIONAL"),
    # CC-98: EWS/Factory-IO host (.2.55) authorised as a TRUSTED high-rate process-I/O source (Approach A) BEFORE the
    # dangerous-ops block, so Factory IO's input-image writes (classified CONTROL) + output reads pass OPERATIONAL and its
    # fast polling isn't flood-cut. PROGRAM/DIAG/ILLEGAL stay FORBIDDEN below (engineering downloads still need authorisation).
    # Anti-spoof-bound (GUARD) + flood-exempt. Trade: a compromised .2.55 endpoint is the documented G1 boundary; the demo
    # attack comes from a DIFFERENT untrusted source forcing the actuator, which stays FORBIDDEN.
    ("ews", "plc", "READ",    "OPERATIONAL"),
    ("ews", "plc", "WRITE",   "OPERATIONAL"),
    ("ews", "plc", "CONTROL", "OPERATIONAL"),
    # CC-51: DANGEROUS operations FORBIDDEN regardless of source
    ("any", "plc", "CONTROL", "FORBIDDEN"),
    ("any", "hmi", "CONTROL", "FORBIDDEN"),
    ("any", "plc", "DIAG",    "FORBIDDEN"),
    ("any", "hmi", "DIAG",    "FORBIDDEN"),
    ("any", "plc", "PROGRAM", "FORBIDDEN"),
    ("any", "hmi", "PROGRAM", "FORBIDDEN"),
    ("any", "plc", "ILLEGAL", "FORBIDDEN"),
    ("any", "hmi", "ILLEGAL", "FORBIDDEN"),
    ("ews",         "plc", "any",   "OPERATIONAL"),   # CC-98b: covers the TCP/COTP connection op too (Factory IO reconnects);
                                                     # PROGRAM/DIAG/ILLEGAL/CONTROL still hit the FORBIDDEN rules above first.
    ("ews",         "hmi", "any",   "SENSITIVE"),
    ("supervisory", "plc", "WRITE", "SENSITIVE"),
    ("historian",   "plc", "WRITE", "SENSITIVE"),
    ("scada",       "plc", "WRITE", "SENSITIVE"),
    ("supervisory", "hmi", "WRITE", "SENSITIVE"),
    ("historian",   "hmi", "WRITE", "SENSITIVE"),
    ("scada",       "hmi", "WRITE", "SENSITIVE"),
    ("supervisory", "plc", "any",   "OPERATIONAL"),
    ("historian",   "plc", "any",   "OPERATIONAL"),
    ("scada",       "plc", "any",   "OPERATIONAL"),
    ("supervisory", "hmi", "any",   "OPERATIONAL"),
    ("historian",   "hmi", "any",   "OPERATIONAL"),
    ("scada",       "hmi", "any",   "OPERATIONAL"),
    ("any",         "plc", "any",   "FORBIDDEN"),
    ("any",         "hmi", "any",   "FORBIDDEN"),
    ("any",         "any", "any",   "FORBIDDEN"),
]
RULEBOOK_FILE = "/home/msclab/cars/rulebook.json"

def load_rulebook(seed=True):
    import json as _j, os as _os
    try:
        if not _os.path.exists(RULEBOOK_FILE):
            if seed:
                with open(RULEBOOK_FILE, "w") as _f:
                    _j.dump([list(r) for r in RULEBOOK], _f, indent=2)
            return "built-in default", len(RULEBOOK)
        with open(RULEBOOK_FILE) as _f:
            rules = _j.load(_f)
        RULEBOOK[:] = [tuple(r) for r in rules]
        return RULEBOOK_FILE, len(RULEBOOK)
    except Exception as e:
        return "error: %s (kept previous)" % e, len(RULEBOOK)
A2_FILE = "/home/msclab/cars/a2_policy.json"
A2_COOKIE = 0x00A2
REACTIVE_COOKIE = 0x00CA   # CC-95: stamp CARS reactive isolate/block/throttle/deflect rules with a DISTINCT cookie so the
                           # flow-integrity checker identifies them by cookie (not by guessing from the priority band) -
                           # closes the reactive-envelope evasion blind spot (a bogus cookie-0x0 rule at prio100-110 is now
                           # NOT mistaken for a reactive rule and gets flagged as EXTRA).
def load_a2(seed=True):
    import json as _j, os as _os
    try:
        if not _os.path.exists(A2_FILE):
            if seed:
                with open(A2_FILE, "w") as _f:
                    _j.dump({"allowlist": [list(r) for r in ALLOWLIST], "default_deny": [list(r) for r in DEFAULT_DENY]}, _f, indent=2)
            return "built-in default", len(ALLOWLIST), len(DEFAULT_DENY)
        with open(A2_FILE) as _f:
            d = _j.load(_f)
        ALLOWLIST[:] = [tuple(r) for r in d.get("allowlist", [])]
        DEFAULT_DENY[:] = [tuple(r) for r in d.get("default_deny", [])]
        return A2_FILE, len(ALLOWLIST), len(DEFAULT_DENY)
    except Exception as e:
        return "error: %s (kept previous)" % e, len(ALLOWLIST), len(DEFAULT_DENY)

def classify(src_ip, dst_ip, op=None):
    s, d = role_of(src_ip), role_of(dst_ip)
    for rsrc, rdst, rop, tier in RULEBOOK:
        if (rsrc == "any" or rsrc == s or rsrc == src_ip) and \
           (rdst == "any" or rdst == d or rdst == dst_ip) and \
           (rop  == "any" or rop  == op):
            return tier, s, d
    return "FORBIDDEN", s, d


# ===================================================================================
# CARS framework: optional site-config overlay (non-destructive, opt-in).
# If the environment variable CARS_SITE points to a site.yaml, the policy constants
# above are overlaid from it. With CARS_SITE unset this block is a no-op, so default
# behaviour is identical to before it existed. The overlay is fully guarded: any
# failure logs a warning and keeps the built-in defaults. Parity of the shipped
# examples/site.testbed.yaml with these defaults is proven by
# framework/tests/test_config_parity.py. See framework/README.md.
# ===================================================================================
_CARS_SITE = os.environ.get("CARS_SITE")
if _CARS_SITE:
    try:
        try:
            from cars.config import load as _cars_load
        except ImportError:
            import sys as _sys
            _fw = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "framework"))
            if _fw not in _sys.path:
                _sys.path.insert(0, _fw)
            from cars.config import load as _cars_load
        _sc = _cars_load(_CARS_SITE)
        REGISTRY = {ip: {k: v for k, v in (("role", d["role"]), ("name", d.get("name")),
                                           ("cell", d.get("cell"))) if v is not None}
                    for ip, d in _sc.registry.items()}
        CRITICALITY = {ip: d["tier"] for ip, d in _sc.registry.items() if d.get("tier")}
        CW = dict(_sc.weights)
        BLOCK_TIMEOUT = _sc.timeout_base_s
        BINDINGS = [(b["dpid"], b["ofport"], b["mac"], b["ip"]) for b in _sc.bindings]
        UPLINKS = dict(_sc.uplinks)
        PROTECTED_IPS = sorted({b[3] for b in BINDINGS})
        ALLOWLIST = [tuple(c) for c in _sc.conduits]
        DEFAULT_DENY = [tuple(d) for d in _sc.default_deny]
        RULEBOOK = [tuple(r) for r in _sc.rulebook]
        _r = _sc.response or {}
        THROTTLE_RATE = _r.get("throttle_rate", THROTTLE_RATE)
        THROTTLE_BURST = _r.get("throttle_burst", THROTTLE_BURST)
        SHARED_ROLES = set(_r.get("shared_roles", SHARED_ROLES))
        FLOOD_EXEMPT = {str(x) for x in _r.get("flood_exempt", FLOOD_EXEMPT)}
        HONEYPOT_IP = str(_r.get("honeypot_ip", HONEYPOT_IP))
        print("[CARS] site config overlaid from %s (assets=%d conduits=%d rulebook=%d)"
              % (_CARS_SITE, len(REGISTRY), len(ALLOWLIST), len(RULEBOOK)))
    except Exception as _e:
        print("[CARS] site-config overlay FAILED (%s); using built-in defaults" % _e)
# ===================================================================================


class CARSEngine(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.blocks = set()
        self.conduit_blocks = set()
        self.hosts = {}
        self.port_state = {}
        self.links = set()
        self.guard_stats = {}
        self.guard_prev = {}   # CC-92b: last-seen drop count per guard key -> emit a decision-log alert when it climbs (spoof visibility)
        self.resp_ms = []
        self.conduit_state = {}
        self.source_state = {}        # A3/CC-38 source-level offense (scanner + persistence)
        self._meters = set()
        self.enforce_enabled = True   # PD-1: reactive enforcement ARMED
        self.maint_until = 0.0        # FEAT-3: maintenance-window expiry (epoch)
        self.api_token = os.environ.get("CARS_API_TOKEN") or self._load_api_token()  # P0-4: control-API auth
        _rsrc, _rn = load_rulebook()
        self.logger.info("A4 rulebook: %s (%d rules)", _rsrc, _rn)
        _asrc, _na, _nd = load_a2()   # FEAT-1: load proactive A2 policy
        self.logger.info("A2 policy: %s (%d allow, %d deny)", _asrc, _na, _nd)
        self.logger.info("Asset criticality: %d assets tiered (CRITICAL..LOW)", len(CRITICALITY))
        hub.spawn(self._serve_api)
        hub.spawn(self._poll_stats)

    def _load_api_token(self):
        # P0-4 fix: control-API token. Prefer an existing token file; else generate one (0600) so the
        # unauthenticated-API gap is closed on first run. Operator reads it from the control plane.
        f = "/home/msclab/cars/api_token"
        try:
            if os.path.exists(f):
                t = open(f).read().strip()
                if t:
                    return t
        except Exception:
            pass
        t = secrets.token_hex(16)
        try:
            with open(f, "w") as fh:
                fh.write(t + "\n")
            os.chmod(f, 0o600)
        except Exception:
            pass
        self.logger.warning("CARS control-API token GENERATED at %s (operator: cat this file)", f)
        return t

    def _serve_api(self):
        self.logger.info("CARS v0.7 (guard=%s) Event API on :8080", "ARMED" if GUARD_ENABLED else "off")
        wsgi.server(eventlet.listen(('0.0.0.0', 8080)), self._app, log_output=False)

    def _app(self, environ, start_response):
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '')
        def reply(obj, code='200 OK'):
            body = json.dumps(obj).encode()
            start_response(code, [('Content-Type', 'application/json'),
                                  ('Content-Length', str(len(body)))])
            return [body]
        # ---- P0-4 fix: authenticate + AUDIT the control (state-changing) endpoints ----
        # An unauthenticated control API let any host with a control-plane path silently DISARM CARS.
        # Now every arm/disarm/restore/reload/maintenance/block requires X-CARS-Token and is logged.
        # /cars/respond (Snort->brain detection feed) is intentionally excluded so the bridge is unchanged.
        _CONTROL = ('/cars/defense', '/cars/maintenance', '/cars/reload', '/cars/reload-a2',
                    '/cars/block', '/cars/unblock', '/cars/restore')
        if method == 'POST' and path in _CONTROL:
            _src = environ.get('REMOTE_ADDR', '?')
            if environ.get('HTTP_X_CARS_TOKEN', '') != self.api_token:
                self._audit({"tier": "CONTROL", "src": _src, "src_role": "api", "dst": "10.10.10.1",
                             "dst_role": "controller", "proto": "HTTP", "op": path, "action": "DENIED (bad/missing token)"})
                return reply({"error": "unauthorized - X-CARS-Token required"}, '401 Unauthorized')
            self._audit({"tier": "CONTROL", "src": _src, "src_role": "api", "dst": "10.10.10.1",
                         "dst_role": "controller", "proto": "HTTP", "op": path, "action": "AUTHORISED"})
        if method == 'GET' and path == '/cars/status':
            return reply({"switches": list(self.datapaths.keys()), "guard": GUARD_ENABLED, "arp_guard": ARP_GUARD_ENABLED,
                          "cars_ms_avg": (round(sum(self.resp_ms)/len(self.resp_ms),3) if self.resp_ms else None), "cars_ms_n": len(self.resp_ms),
                          "mac_blocks": ["dpid%s:%s->%s" % b for b in self.blocks],
                          "conduit_blocks": ["dpid%s:%s->%s" % b for b in self.conduit_blocks]})
        if method == 'GET' and path == '/cars/audit':
            try:
                lines = open(AUDIT).read().splitlines()[-60:]
            except Exception:
                lines = []
            return reply({"audit": lines})
        if method == 'GET' and path == '/cars/hosts':
            now = time.time()
            return reply({"hosts": [dict(ip=h.get("ip"), mac=h["mac"], dpid=h["dpid"], port=h["port"],
                                         age=round(now - h["last"], 1)) for h in list(self.hosts.values())]})
        if method == 'GET' and path == '/cars/ports':
            return reply({"ports": {str(d): st for d, st in list(self.port_state.items())}})
        if method == 'GET' and path == '/cars/links':
            return reply({"links": [dict(src_dpid=a, src_port=b, dst_dpid=c, dst_port=d)
                                    for (a, b, c, d) in self.links]})
        if method == 'GET' and path == '/cars/guard':
            return reply({"drops": self.guard_stats})
        if method == 'GET' and path == '/cars/criticality':
            # roles/names come straight from the (site-config-overlaid) REGISTRY, so
            # the dashboard reflects the controller's real assignments, not a static map.
            return reply({"criticality": CRITICALITY, "weights": CW,
                          "roles": {ip: d.get("role") for ip, d in REGISTRY.items()},
                          "names": {ip: d.get("name") for ip, d in REGISTRY.items()}})
        if method == 'GET' and path == '/cars/defense':
            return reply({"enforce_enabled": self.enforce_enabled})
        if method == 'POST' and path == '/cars/defense':
            try:
                n = int(environ.get('CONTENT_LENGTH') or 0)
                b = json.loads(environ['wsgi.input'].read(n).decode() if n else '{}')
            except Exception:
                b = {}
            self.enforce_enabled = bool(b.get('on', True))
            self.logger.info("*** DEFENSE %s ***", "ARMED" if self.enforce_enabled else "DISARMED")
            return reply({"enforce_enabled": self.enforce_enabled})
        if method == 'GET' and path == '/cars/maintenance':
            rem = max(0, int(self.maint_until - time.time()))
            return reply({"active": rem > 0, "remaining_s": rem})
        if method == 'POST' and path == '/cars/maintenance':
            try:
                n = int(environ.get('CONTENT_LENGTH') or 0)
                b = json.loads(environ['wsgi.input'].read(n).decode() if n else '{}')
            except Exception:
                b = {}
            mins = float(b.get('minutes', 0))
            self.maint_until = (time.time() + mins * 60) if mins > 0 else 0.0
            self.logger.info("*** MAINTENANCE WINDOW %s ***", ("OPEN %g min" % mins) if mins > 0 else "CLOSED")
            return reply({"active": mins > 0, "remaining_s": max(0, int(self.maint_until - time.time()))})
        if method == 'GET' and path == '/cars/rules':
            return reply({"file": RULEBOOK_FILE, "count": len(RULEBOOK), "rules": [list(r) for r in RULEBOOK]})
        if method == 'POST' and path == '/cars/reload':
            src, n = load_rulebook(seed=False)
            self.logger.info("A4 rulebook RELOADED: %s (%d rules)", src, n)
            return reply({"reloaded_from": src, "count": n})
        if method == 'GET' and path == '/cars/allowlist':
            return reply({"file": A2_FILE, "allowlist": [list(r) for r in ALLOWLIST], "default_deny": [list(r) for r in DEFAULT_DENY]})
        if method == 'POST' and path == '/cars/reload-a2':
            src, na, nd = self.reload_a2()
            return reply({"reloaded_from": src, "allow": na, "deny": nd})
        if method == 'POST' and path == '/cars/flowaudit':
            # #28: flow-integrity checker drift feed (trusted local sensor, like /cars/respond -> auth-excluded).
            # Surfaces control-plane flow-rule tampering (bogus-injected / removed / action-modified) into the decision log.
            try:
                n = int(environ.get('CONTENT_LENGTH') or 0)
                b = json.loads(environ['wsgi.input'].read(n).decode() if n else '{}')
            except Exception as e:
                return reply({"error": "bad JSON", "detail": str(e)}, '400 Bad Request')
            self._audit({"tier": b.get("tier", "FORBIDDEN"), "src": b.get("src", "0.0.0.0"),
                         "src_role": b.get("src_role", "flowaudit"), "dst": b.get("dst", "0.0.0.0"),
                         "dst_role": b.get("dst_role", "policy"), "proto": b.get("proto", "OF"),
                         "op": b.get("op", "DRIFT"), "action": b.get("action", "FLOW-INTEGRITY DRIFT")})
            return reply({"logged": True})
        if method == 'POST' and path in ('/cars/block', '/cars/unblock', '/cars/respond', '/cars/restore'):
            try:
                n = int(environ.get('CONTENT_LENGTH') or 0)
                b = json.loads(environ['wsgi.input'].read(n).decode() if n else '{}')
            except Exception as e:
                return reply({"error": "bad JSON", "detail": str(e)}, '400 Bad Request')
            if path == '/cars/respond':
                return reply(self.respond(b.get('src'), b.get('dst'),
                                          b.get('proto', 'IP'), int(b.get('dpid', 3)),
                                          b.get('force'), b.get('op'), b.get('rate')))
            if path == '/cars/restore':
                self.unblock_conduit(int(b.get('dpid', 3)), b.get('src'), b.get('dst'))
                return reply({"restored": True, "src": b.get('src'), "dst": b.get('dst')})
            try:
                dpid, src, dst = int(b['dpid']), b['src'], b['dst']
            except Exception as e:
                return reply({"error": "need {dpid,src,dst}", "detail": str(e)}, '400 Bad Request')
            fn = self.unblock if path.endswith('unblock') else self.block
            ok, msg = fn(dpid, src, dst)
            return reply({"ok": ok, "msg": msg, "dpid": dpid, "src": src, "dst": dst})
        return reply({"error": "not found"}, '404 Not Found')

    # ---- A1 response repertoire: DECISION (tier) is decoupled from RESPONSE (action) ----
    # ALLOW . MONITOR . THROTTLE . DEFLECT . ISOLATE . BLOCK . REFUSE
    def select_response(self, tier, s_role, d_role, state, src_count=0, flood=False, dcw=0):
        # A1/P4: criticality-graded, safety-capped, persistence-escalating response selection.
        # A5: rate/behavioral overlay - flood = the source is issuing THIS op faster than FLOOD_RATE.
        # ASSET CRITICALITY (dcw = destination asset weight 3..0): escalate faster + skip rungs on higher-consequence assets.
        if tier == "CRITICAL":    return "REFUSE"                 # safety invariant - never enforce the loop (even under flood)
        esc = max(1, ESCALATE - dcw)                             # criticality: higher-crit assets escalate sooner
        c = state.get("count", 1)
        if tier == "OPERATIONAL":
            # A5: a PERMITTED op (read/poll) at flood rate is a VOLUMETRIC DoS though each op is individually legal.
            if flood:
                if dcw >= 3: return "BLOCK"                       # CRITICAL asset: cut a flood, don't just rate-limit
                return "THROTTLE" if c < esc else "BLOCK"
            return "ALLOW"                                        # trusted conduit, normal rate
        if tier == "SENSITIVE":                                   # elevated-but-known (ews->plc): permit-with-limit
            if flood:
                return "BLOCK"                                    # A5: elevated AND flooding -> cut now
            if dcw >= 3: return "BLOCK"                           # CRITICAL asset: skip THROTTLE, cut now
            return "THROTTLE" if c < esc else "BLOCK"             #   -> cut on sustained abuse
        # FORBIDDEN: one command can harm -> block now; isolate the source on persistence.
        # Gap-2: a SHARED / NAT-collapsed identity (the IT gateway) must NOT be
        # source-isolated -- that quarantines every host behind the NAT. Cut only
        # the offending conduit (BLOCK); a true single host still gets ISOLATE.
        shared = s_role in SHARED_ROLES
        if flood:
            return "BLOCK" if shared else "ISOLATE"
        if dcw >= 3:
            return "BLOCK" if shared else "ISOLATE"               # CRITICAL asset
        if shared:
            return "BLOCK"
        return "BLOCK" if src_count < esc else "ISOLATE"

    def enforce_response(self, action, dpid, src_ip, dst_ip, timeout=BLOCK_TIMEOUT):
        # Perform the OpenFlow enforcement for a chosen response. Returns (human_str, decision).
        # ASSET CRITICALITY: `timeout` is criticality-scaled (BLOCK_TIMEOUT + cw*15) so critical-asset blocks are stickier.
        if action == "BLOCK":
            self.block_conduit(dpid, src_ip, dst_ip, timeout)
            return "BLOCK conduit %ds (all switches: %s)" % (timeout, sorted(self.datapaths)), "blocked"
        if action == "REFUSE":
            return "REFUSED (safety invariant) - mirror/alert only", "refused"
        if action in ("ALLOW", "MONITOR"):
            return "ALLOW (operational) - monitor only", "allowed"
        if action == "THROTTLE":
            self.throttle_conduit(dpid, src_ip, dst_ip, timeout)
            return "THROTTLE conduit @%dpps %ds (meter, self-healing)" % (THROTTLE_RATE, timeout), "throttled"
        if action == "ISOLATE":
            self.isolate_source(src_ip, timeout)
            return "ISOLATE source %s %ds (quarantine all conduits, self-healing)" % (src_ip, timeout), "isolated"
        if action == "DEFLECT":
            self.deflect_conduit(dpid, src_ip, dst_ip, timeout)
            return "DEFLECT conduit -> honeypot %s (deception, self-healing)" % HONEYPOT_IP, "deflected"
        self.logger.warning("response %s not implemented yet -> BLOCK", action)
        self.block_conduit(dpid, src_ip, dst_ip, timeout)
        return "BLOCK (fallback for %s)" % action, "blocked"

    def respond(self, src_ip, dst_ip, proto, dpid, force=None, op=None, rate=None):
        _t0 = time.perf_counter()
        tier, s_role, d_role = classify(src_ip, dst_ip, op)                       # DECISION (operation/role based)
        # ---- ASSET CRITICALITY, decision side (sec 6): grey-zone elevation, bounded by the maintenance window + I1/I2 ----
        acl = crit_of(dst_ip); dcw = CW.get(acl, 0); in_window = time.time() < self.maint_until
        # a trusted actuating WRITE (SENSITIVE) to a CRITICAL asset is elevated to FORBIDDEN (nothing but the control loop
        # + an authorised maintenance window may write the safety-critical process). READs/loop are never elevated.
        elevated = (tier == "SENSITIVE" and dcw >= 3 and not in_window)
        if elevated:
            tier = "FORBIDDEN"
        # FEAT-3 + criticality: inside an authorised window, permit-with-monitoring (a) the recognised dangerous eng ops
        # AND (b) a would-be-elevated trusted op to a CRITICAL asset (so legit EWS/eng access to the critical PLC works in a window).
        maint = in_window and ((tier == "FORBIDDEN" and op in ("CONTROL", "DIAG", "PROGRAM")) or (tier == "SENSITIVE" and dcw >= 3))
        if maint:
            tier = "OPERATIONAL"      # permitted-with-monitoring during maintenance
        st = self.conduit_state.setdefault((src_ip, dst_ip),
                                           {"count": 0, "first": time.time(), "last": 0.0})
        ss = self.source_state.setdefault(src_ip, {"count": 0, "first": time.time(), "last": 0.0})
        st["last"] = ss["last"] = time.time()
        # A5: behavioral rate intelligence - sensor reports how fast THIS op arrives; >= FLOOD_RATE = flood.
        try:    rate_f = float(rate) if rate is not None else 0.0
        except (TypeError, ValueError): rate_f = 0.0
        flood = rate_f >= FLOOD_RATE and src_ip not in FLOOD_EXEMPT   # CC-98: legit high-rate process-I/O is not a DoS
        # ---- ASSET CRITICALITY, response side (sec 7): dcw drives escalation speed/floor/flood + block duration ----
        action = force if force in RESPONSES else self.select_response(tier, s_role, d_role, st, ss["count"], flood, dcw)
        if action not in ("ALLOW", "MONITOR"):     # A3: benign permits (e.g. reads) don't drive persistence escalation
            st["count"] += 1; ss["count"] += 1
        timeout = BLOCK_TIMEOUT + dcw * 15         # CRITICAL 75 . HIGH 60 . MED 45 . LOW 30 s
        if self.enforce_enabled:
            action_str, decision = self.enforce_response(action, dpid, src_ip, dst_ip, timeout)
        else:
            action_str, decision = ("DEFENSE DISARMED - would %s (monitor only)" % action, "monitored")
        if maint:
            action_str = "MAINTENANCE-AUTHORISED (window) - " + action_str; decision = "maint-authorised"
        if flood:
            action_str = "[FLOOD %.0f ops/s] " % rate_f + action_str
        action_str = action_str + " [CRIT:%s%s]" % (acl, ",elevated" if elevated else "")
        ms = round((time.perf_counter() - _t0) * 1000, 3)
        self.resp_ms.append(ms)
        out = {"src": src_ip, "src_role": s_role, "dst": dst_ip, "dst_role": d_role,
               "proto": proto, "op": op, "tier": tier, "response": action, "decision": decision,
               "action": action_str, "cars_ms": ms, "offense": st["count"], "rate": rate_f, "flood": flood,
               "crit": acl, "elevated": elevated}
        self._audit(out)
        self.logger.info("CARS decide+enforce: %.3f ms", ms)
        return out

    def _audit(self, o):
        opseg = (" %s" % o["op"]) if o.get("op") else ""
        line = "%s  %-11s %s(%s) -> %s(%s) %-5s%s =>  %s" % (
            time.strftime("%m-%dT%H:%M:%S"), o["tier"], o["src"], o["src_role"],
            o["dst"], o["dst_role"], o["proto"], opseg, o["action"])
        self.logger.info("BRAIN: %s", line)
        try:
            with open(AUDIT, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def block_conduit(self, dpid, src_ip, dst_ip, timeout=BLOCK_TIMEOUT):
        # P1: hard_timeout -> block auto-expires (self-heals) if the attack stops; SEND_FLOW_REM lets
        # the controller learn of the expiry and clear its state. Continued detection renews the timer.
        for d, dp in list(self.datapaths.items()):
            ofp, psr = dp.ofproto, dp.ofproto_parser
            m = psr.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=REACTIVE_COOKIE, table_id=1, priority=100, match=m, instructions=[],
                                       hard_timeout=timeout, flags=ofp.OFPFF_SEND_FLOW_REM))
            self.conduit_blocks.add((d, src_ip, dst_ip))

    def _ensure_meter(self, dp):
        # A1/P2: one shared drop-meter per switch (id 1), rate = THROTTLE_RATE pkts/s.
        if dp.id not in self._meters:
            ofp, psr = dp.ofproto, dp.ofproto_parser
            band = psr.OFPMeterBandDrop(rate=THROTTLE_RATE, burst_size=THROTTLE_BURST)
            dp.send_msg(psr.OFPMeterMod(datapath=dp, command=ofp.OFPMC_ADD,
                                        flags=ofp.OFPMF_PKTPS | ofp.OFPMF_BURST, meter_id=1, bands=[band]))
            self._meters.add(dp.id)
        return 1

    def throttle_conduit(self, dpid, src_ip, dst_ip, timeout=BLOCK_TIMEOUT):
        # A1/P2: rate-limit (not drop) - Table 1 policy flow applies the meter then goto switch table.
        for d, dp in list(self.datapaths.items()):
            ofp, psr = dp.ofproto, dp.ofproto_parser
            mid = self._ensure_meter(dp)
            m = psr.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            inst = [psr.OFPInstructionMeter(mid), psr.OFPInstructionGotoTable(2)]
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=REACTIVE_COOKIE, table_id=1, priority=100, match=m, instructions=inst,
                                       hard_timeout=timeout, flags=ofp.OFPFF_SEND_FLOW_REM))
            self.conduit_blocks.add((d, src_ip, dst_ip))

    def isolate_source(self, src_ip, timeout=BLOCK_TIMEOUT):
        # A1/P4: quarantine a persistent source - drop ALL its IP traffic (any dst), above conduit rules.
        for d, dp in list(self.datapaths.items()):
            ofp, psr = dp.ofproto, dp.ofproto_parser
            m = psr.OFPMatch(eth_type=0x0800, ipv4_src=src_ip)
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=REACTIVE_COOKIE, table_id=1, priority=110, match=m, instructions=[],
                                       hard_timeout=timeout, flags=ofp.OFPFF_SEND_FLOW_REM))
            self.conduit_blocks.add((d, src_ip, "*"))

    def _host_on(self, dpid, ip):
        # CC-45: host record (port + mac) for an IP on a switch - DEFLECT direct-output return path.
        for h in self.hosts.values():
            if h.get("dpid") == dpid and h.get("ip") == ip:
                return h
        return None

    def deflect_conduit(self, dpid, src_ip, dst_ip, timeout=BLOCK_TIMEOUT):
        # A1/P3: redirect the conduit to a honeypot (deception) instead of dropping - real target untouched.
        for d, dp in list(self.datapaths.items()):
            ofp, psr = dp.ofproto, dp.ofproto_parser
            fset = [psr.OFPActionSetField(eth_dst=HONEYPOT_MAC), psr.OFPActionSetField(ipv4_dst=HONEYPOT_IP)]
            fm = psr.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            fi = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, fset), psr.OFPInstructionGotoTable(2)]
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=REACTIVE_COOKIE, table_id=1, priority=105, match=fm, instructions=fi,
                                       hard_timeout=timeout, flags=ofp.OFPFF_SEND_FLOW_REM))
            rset = [psr.OFPActionSetField(ipv4_src=dst_ip)]
            rm = psr.OFPMatch(eth_type=0x0800, ipv4_src=HONEYPOT_IP, ipv4_dst=src_ip)
            ah = self._host_on(d, src_ip)
            if ah and ah.get("port") is not None and ah.get("mac"):
                racts = rset + [psr.OFPActionSetField(eth_dst=ah["mac"]), psr.OFPActionOutput(ah["port"])]
                ri = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, racts)]
            else:
                ri = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, rset), psr.OFPInstructionGotoTable(2)]
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=REACTIVE_COOKIE, table_id=1, priority=105, match=rm, instructions=ri,
                                       hard_timeout=timeout, flags=ofp.OFPFF_SEND_FLOW_REM))
            self.conduit_blocks.add((d, src_ip, dst_ip))

    def unblock_conduit(self, dpid, src_ip, dst_ip):
        for d, dp in list(self.datapaths.items()):
            ofp, psr = dp.ofproto, dp.ofproto_parser
            m = psr.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            dp.send_msg(psr.OFPFlowMod(datapath=dp, table_id=1, command=ofp.OFPFC_DELETE_STRICT,
                                       out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                                       priority=100, match=m))
            self.conduit_blocks.discard((d, src_ip, dst_ip))

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _flow_removed(self, ev):
        # P1/P4: a response flow was removed. If it auto-expired (self-heal), clear state + forgive offense.
        msg = ev.msg; ofp = msg.datapath.ofproto; dpid = msg.datapath.id
        m = dict(msg.match.items())
        src, dst = m.get('ipv4_src'), m.get('ipv4_dst')
        if msg.table_id != 1 or not src:
            return
        self.conduit_blocks.discard((dpid, src, dst if dst else "*"))
        if msg.reason == ofp.OFPRR_HARD_TIMEOUT:
            self.logger.info("CARS: %s AUTO-HEALED (timeout) dpid=%s %s -> %s",
                             "block/throttle" if dst else "ISOLATE", dpid, src, dst or "*")
            if dst:
                if (src, dst) in self.conduit_state: self.conduit_state[(src, dst)]["count"] = 0
            else:
                for k in list(self.conduit_state):
                    if k[0] == src: self.conduit_state[k]["count"] = 0
                if src in self.source_state: self.source_state[src]["count"] = 0

    def install_guard(self, dp):
        dpid = dp.id
        psr = dp.ofproto_parser
        GOTO = [psr.OFPInstructionGotoTable(1)]
        def add(prio, match, inst):
            dp.send_msg(psr.OFPFlowMod(datapath=dp, table_id=0, priority=prio, match=match, instructions=inst))
        for (d, port, mac, ip) in BINDINGS:
            if d == dpid:
                add(200, psr.OFPMatch(in_port=port, eth_type=0x0800, eth_src=mac, ipv4_src=ip), GOTO)
                add(200, psr.OFPMatch(in_port=port, eth_type=0x0806, arp_spa=ip, arp_sha=mac), GOTO)
        for port in UPLINKS.get(dpid, []):
            add(150, psr.OFPMatch(in_port=port), GOTO)
        if GUARD_ENABLED:
            for ip in PROTECTED_IPS:
                add(100, psr.OFPMatch(eth_type=0x0800, ipv4_src=ip), [])
        if ARP_GUARD_ENABLED:
            for ip in PROTECTED_IPS:
                add(100, psr.OFPMatch(eth_type=0x0806, arp_spa=ip), [])
        add(50, psr.OFPMatch(eth_type=0x0800), GOTO)
        add(0, psr.OFPMatch(), GOTO)
        self.logger.info("GUARD installed on dpid=%s (armed=%s)", dpid, GUARD_ENABLED)

    def install_allowlist(self, dp):
        # FAIL-SAFE dispatcher: if STATEFUL is on, try the conntrack path; on ANY error fall back to the
        # classic path so a switch is never left without policy (fail_mode=secure => no flows = process halt).
        if STATEFUL:
            try:
                self._install_allowlist_stateful(dp)
                return
            except Exception as e:
                self.logger.error("STATEFUL A2 install FAILED (%s) - falling back to CLASSIC (process-safe)", e)
        self._install_allowlist_classic(dp)

    def _install_allowlist_classic(self, dp):
        ofp, psr = dp.ofproto, dp.ofproto_parser
        for (s, d, proto, dport) in ALLOWLIST:
            m = psr.OFPMatch(eth_type=0x0800, ipv4_src=s, ipv4_dst=d, ip_proto=proto, tcp_dst=dport)
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=A2_COOKIE, table_id=1, priority=60, match=m,
                                       instructions=[psr.OFPInstructionGotoTable(2)]))
        for (dpid, d) in DEFAULT_DENY:
            if dpid is not None and dpid != dp.id:
                continue
            m = psr.OFPMatch(eth_type=0x0800, ipv4_dst=d)
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=A2_COOKIE, table_id=1, priority=55, match=m, instructions=[]))
        self.logger.info("A2 allowlist installed (CLASSIC) on dpid=%s (%d allow, %d deny rules)",
                         dp.id, len(ALLOWLIST), len(DEFAULT_DENY))

    def _install_allowlist_stateful(self, dp):
        # Conntrack reply-aware A2 (SDN Phase 1). Table 1: untracked IP -> ct() recirc; then decide on ct_state.
        # +est (return traffic of an allowed session) -> pass; +new & allowlisted -> commit+pass; +new & protected
        # dst -> drop; other +new -> commit+pass. Shields CLIENTS (HMI) from scans yet keeps their own replies.
        ofp, psr = dp.ofproto, dp.ofproto_parser
        GOTO2 = [psr.OFPInstructionGotoTable(2)]
        disp   = psr.NXActionCT(flags=0, zone_src="", zone_ofs_nbits=0, recirc_table=1, alg=0, actions=[])   # track + recirc to t1
        commit = psr.NXActionCT(flags=1, zone_src="", zone_ofs_nbits=0, recirc_table=255, alg=0, actions=[]) # commit (no recirc)
        def send(prio, match, inst):
            dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=A2_COOKIE, table_id=1, priority=prio, match=match, instructions=inst))
        # 90: untracked IP -> conntrack (populates ct_state, recirculates to table 1)
        send(90, psr.OFPMatch(eth_type=0x0800, ct_state=CT_UNTRK),
             [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [disp])])
        # 85: established -> allow (the return path; this is what lets a shielded client still work)
        send(85, psr.OFPMatch(eth_type=0x0800, ct_state=CT_EST), GOTO2)
        # 80: new + allowlisted conduit -> commit + allow
        for (s, d, proto, dport) in ALLOWLIST:
            m = psr.OFPMatch(eth_type=0x0800, ct_state=CT_NEW, ipv4_src=s, ipv4_dst=d, ip_proto=proto, tcp_dst=dport)
            send(80, m, [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [commit]), psr.OFPInstructionGotoTable(2)])
        # 55: new + protected dst (default-deny) -> drop (unsolicited only; replies already passed at 85)
        for (dpid, d) in DEFAULT_DENY:
            if dpid is not None and dpid != dp.id:
                continue
            send(55, psr.OFPMatch(eth_type=0x0800, ct_state=CT_NEW, ipv4_dst=d), [])
        # 10: any other new IP -> commit + allow (track so its replies pass)
        send(10, psr.OFPMatch(eth_type=0x0800, ct_state=CT_NEW),
             [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [commit]), psr.OFPInstructionGotoTable(2)])
        self.logger.info("A2 allowlist installed (STATEFUL/conntrack) on dpid=%s (%d allow, %d deny rules)",
                         dp.id, len(ALLOWLIST), len(DEFAULT_DENY))

    def reload_a2(self):
        src, na, nd = load_a2(seed=False)
        for _d, dp in list(self.datapaths.items()):
            ofp, psr = dp.ofproto, dp.ofproto_parser
            dp.send_msg(psr.OFPFlowMod(datapath=dp, table_id=1, command=ofp.OFPFC_DELETE,
                                       cookie=A2_COOKIE, cookie_mask=0xFFFFFFFFFFFFFFFF,
                                       out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY, match=psr.OFPMatch()))
            self.install_allowlist(dp)
        self.logger.info("*** A2 POLICY RELOADED: %s (%d allow, %d deny) on %d switches ***", src, na, nd, len(self.datapaths))
        return src, na, nd

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        ofp, psr = dp.ofproto, dp.ofproto_parser
        dp.send_msg(psr.OFPFlowMod(datapath=dp, command=ofp.OFPFC_DELETE, table_id=ofp.OFPTT_ALL,
                                   out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY, match=psr.OFPMatch()))
        dp.send_msg(psr.OFPFlowMod(datapath=dp, table_id=1, priority=0, match=psr.OFPMatch(),
                                   instructions=[psr.OFPInstructionGotoTable(2)]))
        self.add_flow(dp, 0, psr.OFPMatch(),
                      [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)], table_id=2)
        self.add_flow(dp, 2, psr.OFPMatch(eth_dst='ff:ff:ff:ff:ff:ff'),
                      [psr.OFPActionOutput(ofp.OFPP_FLOOD)], table_id=2)
        self.install_guard(dp)
        self.install_allowlist(dp)
        dp.send_msg(psr.OFPPortDescStatsRequest(dp, 0))
        self.logger.info(">>> switch UP dpid=%s (total=%d)", dp.id, len(self.datapaths))

    def add_flow(self, dp, priority, match, actions, table_id=1):
        ofp, psr = dp.ofproto, dp.ofproto_parser
        inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(psr.OFPFlowMod(datapath=dp, table_id=table_id, priority=priority, match=match, instructions=inst))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg; dp = msg.datapath
        ofp, psr = dp.ofproto, dp.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eths = pkt.get_protocols(ethernet.ethernet)
        if not eths:
            return
        eth = eths[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        ip = None
        ar = pkt.get_protocol(arp.arp)
        if ar:
            ip = ar.src_ip
        else:
            i4 = pkt.get_protocol(ipv4.ipv4)
            if i4:
                ip = i4.src
        if ip in ("0.0.0.0", "255.255.255.255"):
            ip = None
        hk = "%s:%s" % (dp.id, eth.src)
        prev = self.hosts.get(hk, {})
        self.hosts[hk] = {"ip": ip or prev.get("ip"), "mac": eth.src,
                          "dpid": dp.id, "port": in_port, "last": time.time()}
        self.mac_to_port.setdefault(dp.id, {})[eth.src] = in_port
        out_port = self.mac_to_port[dp.id].get(eth.dst, ofp.OFPP_FLOOD)
        actions = [psr.OFPActionOutput(out_port)]
        if out_port != ofp.OFPP_FLOOD:
            self.add_flow(dp, 1, psr.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src), actions, table_id=2)
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                     in_port=in_port, actions=actions, data=data))

    @set_ev_cls(ofp_event.EventOFPStateChange, DEAD_DISPATCHER)
    def _sw_dead(self, ev):
        dp = ev.datapath
        if dp is not None and dp.id in self.datapaths:
            del self.datapaths[dp.id]
            self.mac_to_port.pop(dp.id, None)
            self.port_state.pop(dp.id, None)
            self.hosts = {k: v for k, v in self.hosts.items() if v.get("dpid") != dp.id}
            self.logger.info("<<< switch DOWN dpid=%s (total=%d)", dp.id, len(self.datapaths))

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def _port_desc(self, ev):
        dp = ev.msg.datapath; ofp = dp.ofproto
        d = self.port_state.setdefault(dp.id, {})
        for p in ev.msg.body:
            if p.port_no <= ofp.OFPP_MAX:
                d[p.port_no] = "down" if (p.state & ofp.OFPPS_LINK_DOWN) else "up"

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status(self, ev):
        msg = ev.msg; dp = msg.datapath; ofp = dp.ofproto; p = msg.desc
        up = not (p.state & ofp.OFPPS_LINK_DOWN)
        self.port_state.setdefault(dp.id, {})[p.port_no] = "up" if up else "down"
        self.logger.info("PORT %s dpid=%s port=%s", "UP" if up else "DOWN", dp.id, p.port_no)

    @set_ev_cls(topoev.EventLinkAdd)
    def _link_add(self, ev):
        l = ev.link
        self.links.add((l.src.dpid, l.src.port_no, l.dst.dpid, l.dst.port_no))

    @set_ev_cls(topoev.EventLinkDelete)
    def _link_del(self, ev):
        l = ev.link
        self.links.discard((l.src.dpid, l.src.port_no, l.dst.dpid, l.dst.port_no))

    def _poll_stats(self):
        hub.sleep(2)
        while True:
            for dp in list(self.datapaths.values()):
                ofp, psr = dp.ofproto, dp.ofproto_parser
                dp.send_msg(psr.OFPFlowStatsRequest(dp, 0, 0, ofp.OFPP_ANY, ofp.OFPG_ANY, 0, 0, psr.OFPMatch()))
            hub.sleep(3)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats(self, ev):
        dpid = ev.msg.datapath.id
        for st in ev.msg.body:
            if st.priority == 100 and not st.instructions:
                d = dict(st.match.items())
                if 'ipv4_src' in d:
                    self._guard_seen(dpid, "ip",  d['ipv4_src'], st.packet_count)
                elif 'arp_spa' in d:
                    self._guard_seen(dpid, "arp", d['arp_spa'],  st.packet_count)

    def _guard_seen(self, dpid, proto, ip, cnt):
        # CC-92b: record the count AND, when it climbs, surface the blocked source-identity spoof as a decision-log event
        # (the drop itself is already enforced at GUARD table 0 - this only makes the silent drop VISIBLE to the operator).
        key = "dpid%s %s %s" % (dpid, proto, ip)
        self.guard_stats[key] = cnt
        prev = self.guard_prev.get(key)
        if prev is not None and cnt > prev:
            # Shaped to the dashboard's parseAudit schema: numeric dst sentinel, \w+ roles, uppercase op, and a REFUSED
            # response word so the row is coloured/counted (tier FORBIDDEN = spoofing a trusted identity is a forbidden act).
            self._audit({"tier": "FORBIDDEN", "src": ip, "src_role": "SPOOFED",
                         "dst": "0.0.0.0", "dst_role": "guard", "proto": proto.upper(), "op": "SPOOF",
                         "action": "REFUSED (identity-spoof) - %s impersonation dropped at GUARD ingress (dpid%s) [x%d, total %d]"
                                   % (ip, dpid, cnt - prev, cnt)})
        self.guard_prev[key] = cnt

    def block(self, dpid, src, dst):
        dp = self.datapaths.get(dpid)
        if dp is None:
            return False, "unknown dpid %s" % dpid
        psr = dp.ofproto_parser
        dp.send_msg(psr.OFPFlowMod(datapath=dp, cookie=REACTIVE_COOKIE, table_id=1, priority=100,
                                   match=psr.OFPMatch(eth_src=src, eth_dst=dst), instructions=[]))
        self.blocks.add((dpid, src, dst))
        self.logger.info("CARS: BLOCK dpid=%s %s -> %s", dpid, src, dst)
        return True, "blocked"

    def unblock(self, dpid, src, dst):
        dp = self.datapaths.get(dpid)
        if dp is None:
            return False, "unknown dpid %s" % dpid
        ofp, psr = dp.ofproto, dp.ofproto_parser
        dp.send_msg(psr.OFPFlowMod(datapath=dp, table_id=1, command=ofp.OFPFC_DELETE_STRICT,
                                   out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY, priority=100,
                                   match=psr.OFPMatch(eth_src=src, eth_dst=dst)))
        self.blocks.discard((dpid, src, dst))
        self.logger.info("CARS: UNBLOCK dpid=%s %s -> %s", dpid, src, dst)
        return True, "unblocked"
