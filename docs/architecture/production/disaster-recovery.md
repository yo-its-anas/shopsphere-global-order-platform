# Enterprise Disaster Recovery Strategy

> **CRITICAL ARCHITECTURAL WARNING**
>
> **THIS DOCUMENT DESCRIBES A THEORETICAL DISASTER RECOVERY STRATEGY FOR PRODUCTION.**
> **THIS IS NOT IMPLEMENTED IN THE CURRENT SINGLE-VM PROOF-OF-CONCEPT (POC).**

This document outlines the conceptual Disaster Recovery (DR) and Business Continuity Plan (BCP) for the ShopSphere Global Order Platform, defining realistic recovery metrics and regional failover strategies.

---

## 1. Recovery Objectives (SLAs)

We explicitly reject unrealistic "zero-RPO / zero-RTO" promises. Our targets are balanced against the prohibitive cost of global synchronous replication.

*   **RPO (Recovery Point Objective):** **5 Minutes.** In the event of a catastrophic regional loss (e.g., an entire GCP region burns down), we accept a maximum of 5 minutes of data loss. This is the boundary of our asynchronous cross-region database replication and Kafka mirroring.
*   **RTO (Recovery Time Objective):** **2 Hours.** In the event of a full regional failover, we target returning the platform to an operational state (processing new orders) within 2 hours. This accounts for DNS TTL propagation, cold-starting secondary database promotion, and scaling up standby compute pools.

## 2. Backup Strategy

Data persistence relies on Google Cloud Managed Services.
*   **PostgreSQL (Cloud SQL):** Automated daily snapshots are taken and stored in multi-region Cloud Storage buckets. Write-Ahead Logs (WAL) are archived continuously, allowing Point-in-Time Recovery (PITR) to any second within the last 7 days.
*   **Kafka Events:** Historical topic partitions are continuously backed up to Cloud Storage using Confluent Tiered Storage or Kafka Connect Sink tasks, allowing historical event replay if consumer state is lost.

## 3. Regional Failure Strategy

ShopSphere utilizes an **Active-Passive (Warm Standby)** multi-region strategy.

*   **Primary Region (e.g., `europe-west2` - London):** Handles 100% of read and write traffic during normal operations.
*   **Secondary Region (e.g., `europe-west1` - Belgium):** Runs a scaled-down ("pilot light") GKE cluster containing minimum replica sets of stateless microservices.
*   **Data Replication:** Cloud SQL maintains an asynchronous cross-region read replica in the Secondary Region.
*   **The Failover Sequence:**
    1.  Declare a Disaster.
    2.  Promote the secondary Cloud SQL read replica to become the new Primary Master.
    3.  Update GKE cluster configurations to point to the new Master IP.
    4.  Scale the Secondary Region HPA minimums to 100% capacity.
    5.  Update Global Cloud DNS / Load Balancer to route traffic exclusively to the Secondary Region.

## 4. Restore Testing (Game Days)

A DR plan is useless if it is never tested.
*   **Quarterly Game Days:** SRE teams conduct simulated regional failovers in a staging environment every quarter.
*   **Automated Validation:** Restoration scripts (Terraform/Bash) are automated and version-controlled. Manual intervention during failover is strictly minimized to reduce human error during high-stress incidents.

---

## Viva-Ready Architecture Trade-offs

*   **Active-Passive vs. Active-Active:**
    *   *Trade-off:* We elected for Active-Passive (Warm Standby) rather than true Active-Active multi-region deployment. Active-Active requires complex synchronous multi-master database replication (e.g., Google Cloud Spanner) to prevent split-brain write conflicts, which introduces significant latency to every transaction. Active-Passive accepts a 2-hour RTO in exchange for high-performance localized database writes and much simpler operational overhead.
*   **Asynchronous vs. Synchronous Cross-Region Replication:**
    *   *Trade-off:* We accept a 5-minute RPO data loss window in extreme regional catastrophes because synchronous cross-region replication would add hundreds of milliseconds of latency to every checkout request. We trade absolute disaster data perfection for high-speed user experience.