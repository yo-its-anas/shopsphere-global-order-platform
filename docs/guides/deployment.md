# Customer Capability PoC Deployment Guide

This runbook deploys only PostgreSQL, Keycloak, and customer-service to the existing `kind-shopsphere-poc` cluster. It performs no production deployment and does not expose internal services publicly.

## Deployment order

1. Create or reuse the single-node cluster:

   ```bash
   ./platform/kind/create-cluster.sh
   ```

2. Create PostgreSQL credentials interactively, validate, apply, and verify:

   ```bash
   make postgresql-secret
   make validate-postgresql
   make postgresql-apply
   make postgresql-status
   ```

3. Create Keycloak credentials, validate, apply, reconcile clients/policies, and verify:

   ```bash
   make keycloak-secret
   make validate-keycloak
   make keycloak-apply
   make keycloak-configure
   make keycloak-status
   ```

4. Build and load customer-service, derive its database Secret, then apply and verify:

   ```bash
   make customer-service-build
   make customer-service-load
   make customer-service-secret
   make validate-customer-service
   make customer-service-apply
   make customer-service-status
   ```

The Keycloak reconciliation step creates the namespace-scoped activity-reader Secret without displaying its value. The customer-service init container runs Alembic before the application becomes Ready.

## Expected deployed boundary

- `postgresql` StatefulSet and ClusterIP Service in `shopsphere-data`, with a Bound PVC and separate `customer_db`, `keycloak_db`, and `catalogue_db` logical databases;
- `keycloak` Deployment and ClusterIP Service in `shopsphere-platform`;
- `customer-service` Deployment and ClusterIP Service in `shopsphere-apps`; and
- no PostgreSQL, Keycloak administration, or customer-service NodePort, LoadBalancer, or public ingress.

API Gateway and frontend have source implementations but are not part of this deployed cluster boundary. Customer-service NetworkPolicy permits intended ingress from an `api-gateway` pod label, but policy enforcement requires a compatible CNI.

## Read-only verification

```bash
kubectl --context kind-shopsphere-poc get nodes
kubectl --context kind-shopsphere-poc get deployments,statefulsets,pods,services -A
make postgresql-status
make keycloak-status
make customer-service-status
```

These commands must not print secret values. A Ready workload and HTTP 200 probes establish deployment health only; they do not prove registration, profile, address, RBAC, audit, or activity journeys. Run the customer-service suite and the explicitly enabled integration suite for functional evidence.

## Availability and recovery boundary

All pods, the PostgreSQL volume, Docker, and the Kubernetes control plane depend on one physical GCP VM. Multiple replicas on this node do not provide host-level high availability. Follow the PostgreSQL overlay backup/restore runbook before destructive cluster maintenance. Production must use separate failure domains, replicated identity services, regional managed PostgreSQL, automated backups, PITR, and tested recovery.
