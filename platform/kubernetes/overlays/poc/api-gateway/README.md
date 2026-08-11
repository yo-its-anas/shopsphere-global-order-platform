# API Gateway PoC Overlay

This opt-in overlay deploys the API Gateway after customer-service and catalogue-service are Ready. Its fixed upstream origins come from a ConfigMap and cannot be selected by request data. It requires no application credential Secret because it propagates caller bearer tokens without storing or logging them; downstream services validate those tokens and enforce RBAC.

The gateway Service is ClusterIP-only. For workstation testing, use an SSH tunnel to the VM and `kubectl port-forward`; no public Kubernetes service is created. The readiness endpoint requires both synchronous upstream services to be Ready. This provides traffic admission information, not host-level high availability.

NetworkPolicy enforcement depends on a compatible CNI. The current kindnet setup does not enforce NetworkPolicy.

```bash
make validate-api-gateway
make api-gateway-build
make api-gateway-load
make api-gateway-apply
make api-gateway-status
```
