# Ethics and responsible use

This repository accompanies an MSc dissertation on a **defensive** system, CARS, a criticality- and operation-aware SDN intrusion-response system for industrial control systems.

## How the work was conducted

All offensive activity was carried out on an isolated, self-contained laboratory testbed with no connection to any production or external network, using hardware and a simulated process owned by the research group. No live industrial infrastructure was touched, and no data beyond the group's own was involved. Every attack, including the process-devastation injection, was run to measure the defence and was reversed after each run, with the process returned to its safe state.

## The attack tooling in this repository

The repository includes attack clients and harnesses (for example S7 and Modbus write tools, a false-data-injection script, and a fragmentation harness). These exist to substantiate and reproduce the evaluation of the defence. They are reported at the level needed to reproduce the results, and are **not** a turnkey attack against any specific deployed system.

## Your responsibilities

- Do not run any component of this repository against systems you do not own or do not have explicit written permission to test.
- Industrial control systems are safety-critical. Sending crafted S7 or Modbus traffic to a real PLC can cause physical harm. Use only on an isolated testbed you control.
- If you discover a vulnerability in a third-party product while using this code, follow responsible-disclosure practice and contact the vendor.

The intent throughout is defensive: to establish whether a reactive network defence can be trusted on a live process, so that operators have evidence before arming one.
