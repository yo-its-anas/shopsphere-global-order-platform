# ShopSphere PoC kind Cluster

This directory defines the `shopsphere-poc` Kubernetes cluster for one Ubuntu 22.04 Google Cloud VM. The cluster contains exactly one kind control-plane node and no worker nodes. It is a cost- and time-constrained capstone environment, not a highly available topology.

Multiple replicas can demonstrate Kubernetes scheduling, rolling updates, and service behavior, but every pod still depends on the same kind node, Docker daemon, physical VM, disk, network path, and failure domain. Replicas here do **not** provide host-level high availability.

## Network exposure

The kind node maps VM ports 80 and 443 to prepare for a future ingress controller. No ingress controller or application is deployed by this foundation configuration. PostgreSQL, Redis, Kafka, Keycloak administration, Jenkins, Kubernetes administration, and monitoring administration ports are not mapped. Google Cloud firewall policy must independently control access to ports 80 and 443.

## Prerequisites

Docker, kind, and kubectl must already be installed. The scripts never install packages, elevate privileges, pull application images, or change host firewall rules.

## Create or reconcile the foundation

```bash
./platform/kind/create-cluster.sh
```

The script checks prerequisites, creates the cluster only when absent, waits for its single node, and idempotently applies the PoC Kustomize overlay. If the named cluster already exists, it is reused and never implicitly replaced.

## Load locally built images later

```bash
./platform/kind/load-images.sh shopsphere/customer-service:dev
```

Only explicitly named images already present in the local Docker daemon are loaded. The script neither builds nor pulls images. No business or data-service image is part of the platform baseline.

## Delete deliberately

```bash
./platform/kind/delete-cluster.sh
```

Deletion requires an interactive exact-text confirmation. It removes the entire local cluster and its in-cluster state; there is no non-interactive bypass in this script.

## Validate without creating a cluster

```bash
make validate-shell
make validate-kubernetes
make validate
```

These targets check Bash syntax, assert the expected single-node kind shape, and render the Kubernetes overlay locally. They do not create, modify, or delete a cluster.
