# ADR-002: Use a single GCP VM and single-node kind cluster for the PoC

## Status

Accepted — the existing GCP VM hosts a live single-node `shopsphere-poc` kind cluster.
Current evidence confirms one Ready control-plane node and Ready PostgreSQL, Keycloak,
Redis, Kafka, customer-service, catalogue-service, order-service and API Gateway
workloads. The Terraform baseline remains import-oriented and has not been applied by
this repository.

## Context

The capstone needs a reproducible Kubernetes demonstration within limited time, cost, and operational capacity. The agreed execution environment is one Ubuntu 22.04 Google Cloud VM using Docker and kind.

## Decision

Run the PoC on one Ubuntu 22.04 GCP VM. Use Docker as the container runtime and a single-node kind Kubernetes cluster for application and platform workloads. Size resources deliberately and document all consolidation constraints.

## Alternatives considered

- GKE for the PoC: more representative but adds cost, provisioning complexity, and external dependencies.
- Docker Compose only: simpler, but does not demonstrate the mandatory Kubernetes capability.
- Multiple VMs or multi-node kind: improves topology demonstrations but exceeds the PoC resource envelope.

## Consequences

The environment is affordable, inspectable, and rebuildable. The VM, Docker daemon, and kind node are single points of failure; resource contention can affect every component, and Kubernetes availability characteristics cannot be demonstrated.

## Security implications

The VM must use restricted firewall rules, patched images, least-privilege IAM, protected SSH access, encrypted disks, and no committed kubeconfig or secrets. Workload isolation on one host is weaker than production isolation.

## PoC limitations

No high availability, multi-zone resilience, managed control plane, realistic autoscaling,
or node-failure recovery is provided. All implemented application and platform workloads
run through the same Docker host and kind node. Logical customer, catalogue, order and
Keycloak databases also share one PostgreSQL server. A host failure affects identity,
customer, catalogue, inventory, order, cache, event and Gateway capabilities together;
node-failure recovery has not been demonstrated.

## Production evolution

Move workloads to a regional private GKE cluster with multiple node pools and zones, controlled ingress and egress, workload identity, autoscaling, managed data services, backups, and disaster-recovery testing.

## Viva defence notes

Present kind as a conscious delivery constraint that still demonstrates declarative Kubernetes operations. State plainly that it validates packaging and orchestration mechanics, not production reliability.
