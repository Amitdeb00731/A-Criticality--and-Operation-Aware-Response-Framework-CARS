"""Parity test: the extracted site.yaml must reproduce the validated engine's
policy constants exactly. This is the safety net that lets the config overlay be
trusted: if these pass, `site.testbed.yaml` == `06_Build/cars_engine.py` policy.

Engine constants are read via ast.literal_eval (no os-ken import needed).
"""
import ast
import os

import pytest

from cars.config import load

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENGINE = os.path.join(REPO, "06_Build", "cars_engine.py")
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "examples", "site.testbed.yaml")

WANT = {"REGISTRY", "BINDINGS", "UPLINKS", "BLOCK_TIMEOUT", "THROTTLE_RATE",
        "THROTTLE_BURST", "SHARED_ROLES", "FLOOD_EXEMPT", "HONEYPOT_IP",
        "ALLOWLIST", "DEFAULT_DENY", "CRITICALITY", "CW", "RULEBOOK"}


def _engine_constants():
    tree = ast.parse(open(ENGINE, encoding="utf-8").read())
    out = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in WANT):
            out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


@pytest.fixture(scope="module")
def eng():
    return _engine_constants()


@pytest.fixture(scope="module")
def sc():
    return load(SITE)


def test_all_constants_present(eng):
    assert WANT <= set(eng), f"missing engine constants: {WANT - set(eng)}"


def test_roles(eng, sc):
    assert set(sc.registry) == set(eng["REGISTRY"])
    assert all(sc.role_of(ip) == v["role"] for ip, v in eng["REGISTRY"].items())


def test_criticality_and_weights(eng, sc):
    assert {ip: sc.crit_of(ip) for ip in eng["CRITICALITY"]} == eng["CRITICALITY"]
    assert sc.weights == eng["CW"]
    assert sc.timeout_base_s == eng["BLOCK_TIMEOUT"]
    assert sc.timeout_for("CRITICAL") == 75 and sc.timeout_for("LOW") == 30


def test_conduits_and_deny(eng, sc):
    assert [tuple(c) for c in sc.conduits] == [tuple(a) for a in eng["ALLOWLIST"]]
    assert [tuple(d) for d in sc.default_deny] == [tuple(d) for d in eng["DEFAULT_DENY"]]


def test_rulebook(eng, sc):
    assert [tuple(r) for r in sc.rulebook] == [tuple(r) for r in eng["RULEBOOK"]]


def test_bindings_and_uplinks(eng, sc):
    got = [(b["dpid"], b["ofport"], b["mac"], b["ip"]) for b in sc.bindings]
    assert got == [tuple(b) for b in eng["BINDINGS"]]
    assert sc.uplinks == {int(k): v for k, v in eng["UPLINKS"].items()}


def test_response_tuning(eng, sc):
    r = sc.response
    assert r["throttle_rate"] == eng["THROTTLE_RATE"]
    assert r["throttle_burst"] == eng["THROTTLE_BURST"]
    assert set(r["shared_roles"]) == eng["SHARED_ROLES"]
    assert {str(x) for x in r["flood_exempt"]} == eng["FLOOD_EXEMPT"]
    assert str(r["honeypot_ip"]) == eng["HONEYPOT_IP"]
