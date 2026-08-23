"""Site-configuration loader for CARS.

Turns a ``site.yaml`` into the structures the CARS engine reasons over, so the
policy (assets, roles, conduits, rulebook, criticality) lives in config rather
than being hardcoded. This is the portable-core / site-config split described
in ``docs/CARS_FRAMEWORK_PLAN.md``.

The loader is deliberately dependency-light (PyYAML only) and does no I/O beyond
reading the file, so it is safe to import from the engine, the emulation harness
and the tests alike.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc


VALID_ROLES = {
    "plc", "hmi", "historian", "scada", "ews",
    "remediation", "gateway", "supervisory", "unknown",
}
VALID_TIERS = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


@dataclass
class SiteConfig:
    raw: dict[str, Any]
    registry: dict[str, dict[str, Any]]                 # ip -> {role, name, cell, tier}
    bindings: list[dict[str, Any]]                      # {dpid, ofport, mac, ip}
    conduits: list[tuple[str, str, int, int]]           # (src, dst, proto, dport)
    default_deny: list[tuple[int | None, str]]       # (dpid|None, ip)
    rulebook: list[tuple[str, str, str, str]]           # (src_role, dst_role, op, tier)
    weights: dict[str, int]
    timeout_base_s: int
    timeout_step_s: int
    response: dict[str, Any]
    controller: dict[str, Any]
    detection: dict[str, Any]
    uplinks: dict[int, list[int]] = field(default_factory=dict)

    # ---- lookups mirroring the engine's helpers ----
    def role_of(self, ip: str) -> str:
        return self.registry.get(ip, {}).get("role", "unknown")

    def crit_of(self, ip: str) -> str:
        return self.registry.get(ip, {}).get("tier") or "LOW"

    def weight_of(self, ip: str) -> int:
        return self.weights.get(self.crit_of(ip), 0)

    def timeout_for(self, tier: str) -> int:
        """Criticality-scaled hold: base + step * weight (75/60/45/30 s on the testbed)."""
        return self.timeout_base_s + self.timeout_step_s * self.weights.get(tier, 0)


def _require(d: dict[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise ValueError(f"site config: missing '{key}' in {where}")
    return d[key]


def load(path: str) -> SiteConfig:
    """Load and validate a site config, returning a :class:`SiteConfig`."""
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    crit = _require(cfg, "criticality", "top level")
    weights = _require(crit, "weights", "criticality")
    for tier in weights:
        if tier not in VALID_TIERS:
            raise ValueError(f"site config: unknown criticality tier '{tier}'")

    registry: dict[str, dict[str, Any]] = {}
    for a in cfg.get("assets", []):
        ip = _require(a, "ip", "assets[]")
        role = a.get("role", "unknown")
        if role not in VALID_ROLES:
            raise ValueError(f"site config: unknown role '{role}' for {ip}")
        registry[ip] = {"role": role, "name": a.get("name", ip),
                        "cell": a.get("cell"), "tier": a.get("tier")}  # None if unset

    conduits = [(c["src"], c["dst"], int(c.get("proto", 6)), int(c["dport"]))
                for c in cfg.get("conduits", [])]
    default_deny = [(d.get("dpid"), d["ip"]) for d in cfg.get("default_deny", [])]
    rulebook = [tuple(r) for r in cfg.get("rulebook", [])]
    for r in rulebook:
        if len(r) != 4:
            raise ValueError(f"site config: rulebook row must be 4-tuple, got {r}")
        if r[3] not in (VALID_TIERS | {"OPERATIONAL", "SENSITIVE", "FORBIDDEN"}):
            raise ValueError(f"site config: unknown rulebook tier '{r[3]}'")

    return SiteConfig(
        raw=cfg,
        registry=registry,
        bindings=cfg.get("bindings", []),
        conduits=conduits,
        default_deny=default_deny,
        rulebook=rulebook,
        weights=weights,
        timeout_base_s=int(crit.get("timeout_base_s", 30)),
        timeout_step_s=int(crit.get("timeout_step_s", 15)),
        response=cfg.get("response", {}),
        controller=cfg.get("controller", {}),
        detection=cfg.get("detection", {}),
        uplinks={int(k): v for k, v in cfg.get("uplinks", {}).items()},
    )


if __name__ == "__main__":  # tiny smoke test: python -m cars.config.loader site.yaml
    import sys
    sc = load(sys.argv[1])
    print(f"loaded {len(sc.registry)} assets, {len(sc.conduits)} conduits, "
          f"{len(sc.rulebook)} rulebook rows")
    print("timeouts:", {t: sc.timeout_for(t) for t in VALID_TIERS})
