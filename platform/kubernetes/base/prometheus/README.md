# Prometheus Metrics Platform

This component defines an internal, single-replica Prometheus and kube-state-metrics
deployment for the single-node ShopSphere PoC. It discovers application EndpointSlices,
scrapes Collector self-metrics, kube-state-metrics, the kubelet and cAdvisor, and evaluates
a deliberately small rule set.

Prometheus stores seven days of metrics on an 8 GiB local-path PVC, with a 6 GB TSDB size
limit. This survives pod replacement while the kind node and its local volume remain, but
it is neither replicated nor a backup. Loss of the VM, kind node, or local-path data loses
monitoring history. Long-term retention is intentionally excluded from the shared PoC VM.

The Prometheus Service is ClusterIP-only. Access for administration should use a temporary
`kubectl port-forward`; no public Service or Ingress is defined. The Prometheus service
account has read-only discovery and node-metrics permissions. kube-state-metrics has
read-only list/watch access only to the six resource families used by this PoC and has no
permission to read Kubernetes Secrets.

Application discovery allow-lists API Gateway, Customer, Catalogue, Order and Analytics
service names. Analytics becomes a target automatically when its Kubernetes Service is
deployed; it is not falsely represented as running today. The common route/status labels
are bounded by the application metric contract.

The alert thresholds assume 15-second scraping and intentionally require sustained
failure or a minimum traffic floor. No inventory low/out-of-stock alert is active because
the current application metrics do not expose authoritative aggregate inventory gauges.
Adding an invented or process-local value would be unsafe. Such alerts should be enabled
after Catalogue exports persisted aggregate counts without product identifiers as labels.
