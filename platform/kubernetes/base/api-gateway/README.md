# API Gateway Kubernetes Base

Defines one internal API Gateway replica, a ClusterIP Service, restricted pod/container security contexts, probes, resource bounds, and NetworkPolicy intent. The gateway contains transport routing only; customer-service and catalogue-service remain authoritative for JWT validation, authorization, ownership, and domain invariants.

The committed NetworkPolicy allows egress only to cluster DNS and the explicitly labelled customer and catalogue workloads. Ingress is reserved for namespaces explicitly labelled `shopsphere.io/ingress-access=allowed`; no namespace receives that label in this baseline and no Ingress, NodePort, or LoadBalancer is created. Administrative `kubectl port-forward` access remains possible for PoC verification.

NetworkPolicy enforcement requires a compatible CNI. The default kindnet installation does not enforce these policies, so they document intended connectivity but must not be presented as an active security boundary in this cluster.
