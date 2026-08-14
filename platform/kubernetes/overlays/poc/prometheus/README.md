# Prometheus PoC Overlay

This overlay deploys the internal, single-replica Prometheus metrics capability. It does
not provide monitoring high availability: workloads, metrics collection and local TSDB
storage remain on the same physical VM and kind node.
