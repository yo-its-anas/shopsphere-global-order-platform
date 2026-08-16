# OpenTelemetry Collector PoC Overlay

Deploy this overlay only after the `shopsphere-monitoring` namespace and its resource
quota exist. It retains one Collector replica because every workload and telemetry
component shares one kind node and one physical VM.

Applications export traces to:

`http://opentelemetry-collector.shopsphere-monitoring.svc.cluster.local:4318/v1/traces`

The endpoint is internal Kubernetes DNS. Collector failure must not affect application
liveness or readiness; application SDK queues are bounded and export asynchronously.
