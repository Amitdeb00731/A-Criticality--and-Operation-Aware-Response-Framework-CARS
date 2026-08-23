# CARS controller image. Build from the REPOSITORY ROOT (needs both framework/ and
# the engine in 06_Build):
#
#   docker build -f framework/Dockerfile -t cars-controller:0.1.0 .
#
# This image is the controller only. The OpenFlow data plane (Open vSwitch) and the
# Snort sensor are provided by the host or the emulation; switches connect in to :6653.
FROM python:3.11-slim

LABEL org.opencontainers.image.title="CARS controller" \
      org.opencontainers.image.description="Criticality- and operation-aware SDN intrusion-response controller for ICS" \
      org.opencontainers.image.source="https://github.com/Amitdeb00731/A-Criticality--and-Operation-Aware-Response-Framework-CARS" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="0.1.0"

ENV PYTHONUNBUFFERED=1
WORKDIR /cars

RUN pip install --no-cache-dir \
      pyyaml os-ken eventlet requests python-snap7 "pymodbus>=3.5,<3.9"

# the framework package (config loader + CLI) and the validated engine
COPY framework/ /cars/framework/
COPY 06_Build/cars_engine.py /cars/engine/cars_engine.py
RUN pip install --no-cache-dir -e /cars/framework \
 && mkdir -p /home/msclab/cars      # engine runtime state (rulebook/a2/audit are self-seeded)

# config-driven by default; override by mounting your own site.yaml and setting CARS_SITE
ENV CARS_SITE=/cars/framework/examples/site.testbed.yaml

EXPOSE 6653 8080
# :6653 OpenFlow (switches connect here) · :8080 control API + /cars/respond
CMD ["osken-manager", "/cars/engine/cars_engine.py"]
