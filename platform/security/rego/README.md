# Open Policy Agent (OPA) Policy as Code

This directory contains the Rego policies used to enforce security and reliability best practices across ShopSphere Kubernetes manifests before they are deployed to the cluster.

These policies are evaluated dynamically by the Jenkins pipeline during the `OPA Policy Compliance` stage against the Kustomize-rendered output of the environment overlay.

## Implemented Policies

The following rules are enforced globally across all Kubernetes configurations:

1.  **Deny Privileged Containers (`privileged`):** Prevents containers from running with `securityContext.privileged = true`, which would grant them root-like access to the host.
2.  **Deny hostPID (`hostPID`):** Prevents pods from sharing the host's PID namespace, mitigating process-level tampering.
3.  **Deny hostIPC (`hostIPC`):** Prevents pods from sharing the host's IPC namespace.
4.  **Deny hostNetwork (`hostNetwork`):** Prevents pods from sharing the host's network namespace unless explicitly required.
5.  **Require runAsNonRoot (`runAsNonRoot`):** Enforces that `securityContext.runAsNonRoot` is explicitly set to `true` at the Pod or Container level to prevent containers from executing as root.
6.  **Deny allowPrivilegeEscalation (`allowPrivilegeEscalation`):** Ensures that `securityContext.allowPrivilegeEscalation` is explicitly set to `false`.
7.  **Require Resource Requests (`resource_requests`):** Ensures every container explicitly requests minimum CPU and memory.
8.  **Require Resource Limits (`resource_limits`):** Ensures every container is bounded by CPU and memory limits to prevent cluster starvation.
9.  **Deny LoadBalancer Services (`service_type_loadbalancer`):** Prevents internal data and backend services from accidentally exposing themselves externally via cloud provider LoadBalancers.
10. **Deny NodePort Services (`service_type_nodeport`):** Prevents services from binding statically to host ports.
11. **Deny `:latest` Image Tags (`latest_tag`):** Enforces deterministic deployments by requiring specific, immutable image tags instead of volatile `:latest` references.
12. **Deny Dangerous hostPath Volumes (`hostPath`):** Prevents pods from mounting arbitrary paths from the host filesystem, mitigating container escape vulnerabilities.
13. **Require Probes for Apps (`require_probes`):** Ensures all first-party applications (`shopsphere-*` namespaces) define both `livenessProbe` and `readinessProbe` for high availability.

## Exceptions Mechanism

It is inevitable that certain third-party components (e.g., monitoring agents, storage provisioners) legitimately require capabilities that are normally restricted. 

To prevent silent failures while avoiding "whitelisting everything", we utilize an explicit **Exceptions Mechanism**.

Exceptions are documented and executed in `exceptions.rego`.

### Adding an Exception

To approve a justified exception for a third-party workload, add a rule to `exceptions.rego` following this format:

```rego
exception[{"rule": "RULE_NAME", "kind": "RESOURCE_KIND", "name": "RESOURCE_NAME", "namespace": "NAMESPACE_NAME", "reason": "Explicit justification"}]
```

Example (Wazuh Agent requiring host monitoring access):
```rego
exception[{"rule": "privileged", "kind": "DaemonSet", "name": "wazuh-agent", "namespace": "shopsphere-security", "reason": "Wazuh agent requires privileged execution to monitor the host"}]
```

All exceptions must include a `reason` providing the engineering justification.

## Testing Policies

Policies are validated with unit tests using OPA's native testing framework.

To execute the tests locally:
```bash
docker run --rm -v "$PWD:/apps" openpolicyagent/opa:0.68.0 test -v /apps/platform/security/rego/
```
