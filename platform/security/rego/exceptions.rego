package shopsphere.security.exceptions

# ----------------------------------------------------------------------------------------------------------------------
# Wazuh Exceptions
# ----------------------------------------------------------------------------------------------------------------------
exception[{"rule": "privileged", "kind": "DaemonSet", "name": "wazuh-agent", "namespace": "shopsphere-security", "reason": "Wazuh agent requires privileged execution to monitor the host"}]
exception[{"rule": "hostPath", "kind": "DaemonSet", "name": "wazuh-agent", "namespace": "shopsphere-security", "reason": "Wazuh agent requires access to host paths"}]
exception[{"rule": "allowPrivilegeEscalation", "kind": "DaemonSet", "name": "wazuh-agent", "namespace": "shopsphere-security", "reason": "Wazuh agent requires privilege escalation"}]
exception[{"rule": "runAsNonRoot", "kind": "DaemonSet", "name": "wazuh-agent", "namespace": "shopsphere-security", "reason": "Wazuh agent must run as root to read system logs"}]

# ----------------------------------------------------------------------------------------------------------------------
# Local Path Provisioner Exceptions (Third Party)
# ----------------------------------------------------------------------------------------------------------------------
exception[{"rule": "hostPath", "kind": "Deployment", "name": "local-path-provisioner", "namespace": "local-path-storage", "reason": "Provisioner requires hostPath to provision local volumes"}]
exception[{"rule": "runAsNonRoot", "kind": "Deployment", "name": "local-path-provisioner", "namespace": "local-path-storage", "reason": "Provisioner requires root access to manage host directories"}]

# ----------------------------------------------------------------------------------------------------------------------
# Database / State Exceptions
# ----------------------------------------------------------------------------------------------------------------------
# PostgreSQL
exception[{"rule": "runAsNonRoot", "kind": "StatefulSet", "name": "postgresql", "namespace": "shopsphere-data", "reason": "PostgreSQL official image might run init scripts as root"}]
# Redis
exception[{"rule": "runAsNonRoot", "kind": "StatefulSet", "name": "redis", "namespace": "shopsphere-data", "reason": "Redis official image might run as root"}]
# Kafka
exception[{"rule": "runAsNonRoot", "kind": "StatefulSet", "name": "kafka", "namespace": "shopsphere-platform", "reason": "Kafka image might run as root"}]
# Keycloak
exception[{"rule": "runAsNonRoot", "kind": "StatefulSet", "name": "keycloak", "namespace": "shopsphere-platform", "reason": "Keycloak image might run as root"}]

# ----------------------------------------------------------------------------------------------------------------------
# Kube-State-Metrics Exceptions
# ----------------------------------------------------------------------------------------------------------------------
exception[{"rule": "allowPrivilegeEscalation", "kind": "Deployment", "name": "kube-state-metrics", "namespace": "shopsphere-monitoring", "reason": "Third-party kube-state-metrics image default"}]
exception[{"rule": "runAsNonRoot", "kind": "Deployment", "name": "kube-state-metrics", "namespace": "shopsphere-monitoring", "reason": "Third-party kube-state-metrics default"}]

# ----------------------------------------------------------------------------------------------------------------------
# OpenTelemetry Exceptions
# ----------------------------------------------------------------------------------------------------------------------
exception[{"rule": "runAsNonRoot", "kind": "Deployment", "name": "opentelemetry-collector", "namespace": "shopsphere-monitoring", "reason": "OTel collector image default"}]
exception[{"rule": "allowPrivilegeEscalation", "kind": "Deployment", "name": "opentelemetry-collector", "namespace": "shopsphere-monitoring", "reason": "OTel collector image default"}]

# ----------------------------------------------------------------------------------------------------------------------
# Prometheus Exceptions
# ----------------------------------------------------------------------------------------------------------------------
exception[{"rule": "runAsNonRoot", "kind": "Deployment", "name": "prometheus", "namespace": "shopsphere-monitoring", "reason": "Prometheus image default"}]
exception[{"rule": "allowPrivilegeEscalation", "kind": "Deployment", "name": "prometheus", "namespace": "shopsphere-monitoring", "reason": "Prometheus image default"}]

# ----------------------------------------------------------------------------------------------------------------------
# Promtail Exceptions
# ----------------------------------------------------------------------------------------------------------------------
exception[{"rule": "hostPath", "kind": "DaemonSet", "name": "promtail", "namespace": "shopsphere-monitoring", "reason": "Promtail requires hostPath to read container logs"}]
exception[{"rule": "runAsNonRoot", "kind": "DaemonSet", "name": "promtail", "namespace": "shopsphere-monitoring", "reason": "Promtail must run as root to read container logs"}]
exception[{"rule": "allowPrivilegeEscalation", "kind": "DaemonSet", "name": "promtail", "namespace": "shopsphere-monitoring", "reason": "Promtail must run as root to read container logs"}]
