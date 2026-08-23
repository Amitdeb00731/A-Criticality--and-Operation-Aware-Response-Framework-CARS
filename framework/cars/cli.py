"""CARS command-line entry point.

Currently implements ``cars config validate`` (fully working). ``cars run`` and
``cars demo`` are scaffolded and will be wired to the engine and the emulation
harness in the next phases (see docs/CARS_FRAMEWORK_PLAN.md).
"""
from __future__ import annotations

import argparse
import sys

from .config import load


def _cmd_config(args: argparse.Namespace) -> int:
    sc = load(args.file)
    print(f"OK: {args.file}")
    print(f"  assets   : {len(sc.registry)}")
    print(f"  conduits : {len(sc.conduits)}")
    print(f"  rulebook : {len(sc.rulebook)} rows")
    print("  timeouts : " + ", ".join(f"{t}={sc.timeout_for(t)}s"
                                       for t in ("CRITICAL", "HIGH", "MEDIUM", "LOW")))
    return 0


def _not_wired(name: str) -> int:
    print(f"'cars {name}' is scaffolded but not wired yet. "
          f"See docs/CARS_FRAMEWORK_PLAN.md for the phase plan.", file=sys.stderr)
    return 2


def _demo() -> int:
    print(
        "CARS emulation (no hardware). Requires a Linux host with root, Mininet,\n"
        "Open vSwitch and Snort. See emulation/README.md. In short:\n\n"
        "  # 1. controller (config-driven)\n"
        "  CARS_SITE=examples/site.testbed.yaml osken-manager ../06_Build/cars_engine.py\n\n"
        "  # 2. fabric + software PLCs (root)\n"
        "  sudo python3 emulation/topo.py\n"
        "  mininet> plc1 python3 emulation/plc/s7_server.py 192.168.2.10 &\n"
        "  mininet> hist python3 emulation/plc/tank.py --host 192.168.2.10 &\n\n"
        "  # 3. attack -> CARS isolates it\n"
        "  mininet> atk python3 ../06_Build/s7_write.py 192.168.2.10\n"
    )
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cars", description="CARS intrusion-response framework")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("config", help="work with site configuration")
    pcsub = pc.add_subparsers(dest="subcmd", required=True)
    pv = pcsub.add_parser("validate", help="validate a site.yaml")
    pv.add_argument("file")
    pv.set_defaults(func=_cmd_config)

    pr = sub.add_parser("run", help="run the controller against a live fabric (scaffold)")
    pr.add_argument("--config", required=True)
    pr.set_defaults(func=lambda a: _not_wired("run"))

    pd = sub.add_parser("demo", help="show the no-hardware emulation quickstart")
    pd.set_defaults(func=lambda a: _demo())

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
