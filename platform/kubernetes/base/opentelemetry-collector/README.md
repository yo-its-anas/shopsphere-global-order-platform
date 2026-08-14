# OpenTelemetry Collector Kubernetes Base

Defines one internal OpenTelemetry Collector replica in `shopsphere-monitoring`.
The Collector accepts OTLP/gRPC and OTLP/HTTP, applies memory limiting and batching,
and writes basic trace batch summaries only to its container log. It does not send
telemetry to an external service and does not contain credentials.

The ClusterIP Service also exposes the health extension and Collector self-metrics for
internal monitoring and validation. No NodePort, LoadBalancer, Ingress, host port, or
external exporter is configured.

The NetworkPolicy permits OTLP ingress from the applications namespace and operational
health/metrics access from the monitoring namespace. It declares no Collector egress.
The default kind CNI may not enforce NetworkPolicy; treat the manifest as intent until
enforcement is tested with a compatible CNI.

The single Collector, kind node, and physical VM are not highly available. Basic debug
output is validation evidence, not durable trace storage.
