# ShopSphere Wazuh Security Monitoring (PoC & Production Evolution)

This document records the exact architectural boundaries, resource footprints, and verified security-monitoring capabilities of the Wazuh deployment within the ShopSphere Enterprise Platform PoC.

---

## 1. Verified PoC Monitoring Scope & Boundaries

The Wazuh Agent is running as a containerized Kubernetes `DaemonSet` inside a single-node `kind` (Kubernetes-in-Docker) cluster, which itself runs inside an Ubuntu 22.04 Google Cloud VM. 

Because of this nested virtualization, the Agent is **sandboxed within the kind node container**, which fundamentally limits its visibility compared to a native host-level agent.

### 1.1 Mounted Host Paths (Verified)
The following directories from the **kind node container** (not the physical GCP VM) are mounted into the Wazuh Agent container:
*   `/var/log` mounted read-only at `/var/log`
*   `/etc` mounted read-only at `/host/etc`

### 1.2 Authentication and System Log Accessibility
*   **syslog & auth.log:** The kind node container does not utilize standard `/var/log/auth.log` or `/var/log/syslog` files natively; system logging is entirely captured by `systemd-journald`. 
*   **Agent Log Collection:** By default, the wazuh-agent does not read host container logs since no `<localfile>` directives pointing to `/var/log/syslog` or `/var/log/auth.log` are present in `/var/ossec/etc/ossec.conf`.
*   **Access:** While container runtime logs (`/var/log/pods` and `/var/log/containers`) are physically accessible inside the agent pod via the `/var/log` mount, the agent is not configured to scan them. Broad application logs are already ingested by **Promtail & Loki** to prevent duplicate agent overhead.

### 1.3 File Integrity Monitoring (FIM) Scope
*   **Directories Scanned:** `<directories>/etc,/usr/bin,/usr/sbin</directories>`
*   **Verification:** These paths target the **Wazuh Agent container's own internal filesystem**, NOT the host VM or the kind node container filesystem. 
*   **Scope:** Host-level FIM (on `/host/etc`) is **not configured** in the default `ossec.conf`. Security events related to `/etc` monitor only modifications inside the agent container.

### 1.4 SCA Benchmark Execution & Origin
*   **Executed Policy:** `CIS Benchmark for Amazon Linux 2023 Benchmark v1.0.0` (`cis_amazon_linux_2023.yml`).
*   **Target Scope:** This benchmark applies **only to the Wazuh Agent container image itself** (which is built on Amazon Linux 2023). It does **not** evaluate compliance for the underlying Ubuntu 22.04 GCP VM host.
*   **Origin of Security Events:** Currently, all generated SCA compliance ratings, anomaly checks (e.g., hidden `/dev/termination-log` alerts), and file modifications originate **entirely from the agent container's local isolated filesystem**, not the underlying node or physical VM.

---

## 2. Platform Status & Evidence-Based Verification

### 2.1 Component Health (Verified)
*   **Wazuh Manager:** Deployed in the `shopsphere-security` namespace with memory limits constrained tightly to `1Gi` to protect host stability. Currently in `1/1 Running` state with 0 restarts.
*   **Wazuh Agent:** Deployed globally as a `DaemonSet` with `enableServiceLinks: false` to prevent port binding clashes with Kubernetes-injected variables. Currently in `1/1 Running` state with 0 restarts.
*   **Agent Enrollment:** Verified active. The agent successfully connects and registers with the manager via the internal `wazuh-manager` ClusterIP service on port `1515`.
*   **Manager-Agent Communication:** Operational. Handled over port `1514 (TCP)` as confirmed by agent connection establishment logs.

### 2.2 Security Event Demonstration
*   **Host-Level Coverage:** **Partial / Sandboxed**.
*   **FIM Event:** Initiated a harmless file creation `/etc/fim-trigger.txt` inside the agent container filesystem.
*   **Anomaly Event Observed:** The Wazuh Manager's rootcheck module successfully triggered a Level 7 Host-based anomaly alert in `alerts.json` identifying a hidden container termination file:
    ```json
    {
      "timestamp": "2026-08-15T02:12:57.426+0000",
      "rule": {
        "level": 7,
        "description": "Host-based anomaly detection event (rootcheck).",
        "id": "510"
      },
      "agent": {
        "id": "002",
        "name": "wazuh-agent-wazuh-agent-dd8w5"
      },
      "data": {
        "title": "File present on /dev.",
        "file": "/dev/termination-log"
      }
    }
    ```

### 2.3 Current Resource Consumption (PoC VM Host)
*   **Total VM Memory Used:** `4.67 GB` used out of `32 GB` (plenty of free headroom).
*   **Total CPU Usage:** `~21.5%` across all containers.
*   **Wazuh Footprint:** Constrained securely under Cgroup limits, protecting the primary `shopsphere-apps` commerce workloads.

---

## 3. SIEM & Security Architecture Evolution (Production)

To achieve true enterprise-level host visibility, security compliance, and robust threat hunting, the platform must evolve beyond a single-node PoC:

| Phase | PoC (Current) | Production Target |
| --- | --- | --- |
| **Agent Deployment** | Containerized DaemonSet in kind | Native host-level `wazuh-agent` systemd service running directly on each GCP VM node |
| **Host Visibility** | Sandboxed inside docker node | Complete visibility into host logs, systemd, journald, SSH, and host `/etc` FIM |
| **SCA Benchmark** | Amazon Linux 2023 (Container OS) | CIS Ubuntu 22.04 LTS Benchmark running directly on GCP VM hosts |
| **SIEM Dashboard** | Not Implemented (Resource conservation) | Dedicated, replicated Wazuh Indexer and Dashboard cluster on separate secure nodes |
| **Data Retention** | Ephemeral `/var/ossec` emptyDir volume | Replicated high-durability cloud object storage (e.g. GCS) with managed audit trail |
