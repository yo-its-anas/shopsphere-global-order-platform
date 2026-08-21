# Recommended Production Architecture (Diagrams 16–17)

> **CRITICAL ARCHITECTURAL WARNING**
>
> **THE DIAGRAMS IN THIS DOCUMENT DESCRIBE A RECOMMENDED PRODUCTION-REFERENCE ARCHITECTURE.**
> **THIS ARCHITECTURE IS NOT IMPLEMENTED IN THE POC ENVIRONMENT.**

This document provides a professional, cloud-scale architecture design for ShopSphere Global, highlighting how the platform scales to support millions of concurrent users across multiple availability zones.

---

## Diagram 16: Recommended Production Enterprise Architecture Diagram

### Purpose
Exposes the horizontally scalable, highly available, and cloud-replicated production blueprint for ShopSphere.

### Mermaid Diagram
```mermaid
graph TD
    subgraph PublicInternet [Edge Layer]
        DNS[Global Cloud DNS] -->|Anycast| CDN[Global CDN / Cloud Armor WAF]
        CDN -->|Anycast| GLB[Global Cloud Load Balancer]
    end

    subgraph MultiZoneCluster [Multi-Zone Google Kubernetes Engine - GKE]
        subgraph Autoscaling [Cluster Autoscaling & Pod Elasticity]
            HPA[Horizontal Pod Autoscaler - HPA]
            CA[Cluster Autoscaler]
        end

        subgraph ZoneA [Availability Zone A]
            subgraph AppsA [Namespace: apps]
                subgraph ServicesA [Stateless ShopSphere Microservices - Zone A]
                    GW_A[api-gateway]
                    CS_A[customer-service]
                    CAT_A[catalogue-service]
                    OS_A[order-service]
                    AS_A[analytics-service]
                end
            end
        end

        subgraph ZoneB [Availability Zone B]
            subgraph AppsB [Namespace: apps]
                subgraph ServicesB [Stateless ShopSphere Microservices - Zone B]
                    GW_B[api-gateway]
                    CS_B[customer-service]
                    CAT_B[catalogue-service]
                    OS_B[order-service]
                    AS_B[analytics-service]
                end
            end
        end
    end

    subgraph SecurityTier [Production Security & Identity]
        SM[Secret Manager]
        KMS[Cloud KMS]
        WI[Workload Identity]
    end

    subgraph ManagedDataTier [Managed Database & Message Tiers]
        subgraph CloudSQL [Cloud SQL for PostgreSQL - HA + Read Replicas + PITR]
            PG_M[(Primary Write Node)]
            PG_R[(Read Replica Zone B)]
            PG_M -->|Synchronous Replication| PG_R
        end

        subgraph Memorystore [Memorystore for Redis - HA]
            RD_M[(Redis Master)]
            RD_S[(Redis Replica)]
            RD_M -->|Sync Replication| RD_S
        end

        subgraph MSK [Managed / Multi-Broker Kafka Cluster]
            KB1[[Broker 1 - Zone A]]
            KB2[[Broker 2 - Zone B]]
        end
    end

    subgraph RecoveryTier [Disaster Recovery & Data Protection]
        DR[Backups / PITR / DR]
        CS_DR[Cloud Storage / cross-region recovery]
        DR --> CS_DR
    end

    GLB -->|Route traffic| GW_A
    GLB -->|Route traffic| GW_B

    GW_A --> OS_A
    GW_B --> OS_B
    GW_A --> CAT_A
    GW_B --> CAT_B
    GW_A --> CS_A
    GW_B --> CS_B
    GW_A --> AS_A
    GW_B --> AS_B

    %% Database Writes
    OS_A -->|Write| PG_M
    OS_B -->|Write| PG_M
    CAT_A -->|Read Replica| PG_R
    CAT_B -->|Read Replica| PG_R
    CS_A -->|Write| PG_M
    CS_B -->|Write| PG_M

    %% Cache & Kafka
    CAT_A --> RD_M
    CAT_B --> RD_M
    OS_A --> KB1
    OS_B --> KB2

    %% Security & Storage mappings (logical dependencies)
    ServicesA -.->|Fetch Secrets| SM
    ServicesB -.->|Fetch Secrets| SM
    PG_M -.->|Async Archive| DR
```

### Accompanying Metadata
*   **Main Components:** CDN, WAF, Global Load Balancer, Multi-Zone GKE cluster, horizontally scaled stateless microservice pods, managed PostgreSQL with replication, managed Redis, multi-broker Kafka, and multi-zone failover.
*   **Key Flow:** Global traffic enters the edge layer, filters through WAF, maps to availability zones, and hits stateless gateways. Stateless microservices scale dynamically via HPAs based on traffic signals, routing writes to PostgreSQL Primary and reads to secondary replicas.
*   **Architecture Decisions:** Adopted Google Cloud SQL Multi-AZ PostgreSQL and Memorystore Redis clusters to completely decouple operations from local storage failures and provide high-durability persistence.
*   **Production Recommendations:** Maintain complete isolation of the telemetry tier (observability metrics/logs) on a separate infrastructure to prevent commerce node starvation.
*   **Viva Talking Points:** "How does this scale to millions? By keeping microservices entirely stateless, we can scale pods horizontally across multiple availability zones using HPA, while offloading state management to highly scalable, managed cloud databases."

---

## Diagram 17: PoC vs Production Comparison Diagram

### Purpose
Exposes a side-by-side technical comparison between the single-node virtualized PoC environment and the recommended cloud production architecture.

### Mermaid Diagram
```mermaid
graph LR
    subgraph PoCLayout [Single-Node Virtualized PoC]
        VM[GCP Ubuntu Host VM]
        VM -->|Shared Disk / CPU| K8S[Kind Single-Node Cluster]
        K8S -->|Ephemeral emptyDir| TS[Local Metrics/Logs]
        K8S -->|Shared Instance| DBS[(Local PostgreSQL / Redis Pods)]
    end

    subgraph ProductionLayout [Recommended Cloud Production]
        LB[Global Load Balancer]
        LB -->|Distribute| GKE[Horizontally Scaled Multi-Zone GKE]
        GKE -->|Scale Stateless Pods| HPA[Metrics-Driven HPA]
        GKE -->|Durable Logs/Metrics| CloudObs[Managed SaaS: Datadog / Stackdriver]
        GKE -->|State Storage| ManagedDB[(Cloud SQL Multi-AZ / Memorystore)]
        GKE -->|Events Ingestion| ManagedKafka[[Cloud Managed Kafka Cluster]]
    end
```

### Accompanying Metadata
*   **Main Components:** Single-node Kind cluster layout (PoC) vs. Multi-Zone GKE, Global LB, managed datastores, and SaaS telemetry stack (Production).
*   **Key Flow:** Compares single-host resource-competing execution with distributed, zone-isolated, and scalable cloud processing.
*   **Architecture Decisions:** Selected Cloud SQL, Memorystore, and Managed Kafka to minimize SRE operational overhead and guarantee high-replicated data durability.
*   **Viva Talking Points:** "What is the primary difference? The PoC runs as a single process group sharing CPU, Memory, and Disk on a single GCP VM, constituting a unified failure domain. The Recommended Production Architecture is fully distributed across multiple availability zones, guaranteeing high availability, horizontal scaling, and complete disaster recovery."
