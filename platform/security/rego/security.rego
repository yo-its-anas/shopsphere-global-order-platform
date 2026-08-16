package shopsphere.security

import data.shopsphere.security.exceptions.exception

# Helper to check if a resource is excepted from a rule
is_excepted(rule, kind, name, namespace) {
    e := exception[_]
    e.rule == rule
    e.kind == kind
    e.name == name
    e.namespace == namespace
}

# 1. Deny privileged containers
violation[{"id": "privileged", "msg": msg}] {
    container := input_containers[_]
    container.c.securityContext.privileged == true
    not is_excepted("privileged", container.kind, container.name, container.namespace)
    msg := sprintf("Security Violation: Privileged container '%s' detected in %s '%s'", [container.c.name, container.kind, container.name])
}

# 2. Deny hostPID
violation[{"id": "hostPID", "msg": msg}] {
    pod := input_pod_specs[_]
    pod.spec.hostPID == true
    not is_excepted("hostPID", pod.kind, pod.name, pod.namespace)
    msg := sprintf("Security Violation: %s '%s' uses hostPID", [pod.kind, pod.name])
}

# 3. Deny hostIPC
violation[{"id": "hostIPC", "msg": msg}] {
    pod := input_pod_specs[_]
    pod.spec.hostIPC == true
    not is_excepted("hostIPC", pod.kind, pod.name, pod.namespace)
    msg := sprintf("Security Violation: %s '%s' uses hostIPC", [pod.kind, pod.name])
}

# 4. Deny hostNetwork unless explicitly approved
violation[{"id": "hostNetwork", "msg": msg}] {
    pod := input_pod_specs[_]
    pod.spec.hostNetwork == true
    not is_excepted("hostNetwork", pod.kind, pod.name, pod.namespace)
    msg := sprintf("Security Violation: %s '%s' uses hostNetwork", [pod.kind, pod.name])
}

# 5. Require runAsNonRoot where compatible
violation[{"id": "runAsNonRoot", "msg": msg}] {
    container := input_containers[_]
    pod := get_pod_spec_by_container(container)
    
    pod_run_as_non_root := object.get(object.get(pod.spec, "securityContext", {}), "runAsNonRoot", false)
    container_run_as_non_root := object.get(object.get(container.c, "securityContext", {}), "runAsNonRoot", false)
    
    not pod_run_as_non_root
    not container_run_as_non_root
    
    not is_excepted("runAsNonRoot", container.kind, container.name, container.namespace)
    msg := sprintf("Security Violation: Container '%s' in %s '%s' does not set runAsNonRoot=true", [container.c.name, container.kind, container.name])
}

get_pod_spec_by_container(container) = pod {
    pod := input_pod_specs[_]
    pod.kind == container.kind
    pod.name == container.name
    pod.namespace == container.namespace
}

# 6. Detect allowPrivilegeEscalation=true
violation[{"id": "allowPrivilegeEscalation", "msg": msg}] {
    container := input_containers[_]
    esc := object.get(object.get(container.c, "securityContext", {}), "allowPrivilegeEscalation", true)
    esc == true
    not is_excepted("allowPrivilegeEscalation", container.kind, container.name, container.namespace)
    msg := sprintf("Security Violation: Container '%s' in %s '%s' allows privilege escalation", [container.c.name, container.kind, container.name])
}

# 7. Require resource requests
violation[{"id": "resource_requests", "msg": msg}] {
    container := input_containers[_]
    not container.c.resources.requests
    not is_excepted("resource_requests", container.kind, container.name, container.namespace)
    msg := sprintf("Policy Violation: Container '%s' in %s '%s' is missing resource requests", [container.c.name, container.kind, container.name])
}

# 8. Require resource limits
violation[{"id": "resource_limits", "msg": msg}] {
    container := input_containers[_]
    not container.c.resources.limits
    not is_excepted("resource_limits", container.kind, container.name, container.namespace)
    msg := sprintf("Policy Violation: Container '%s' in %s '%s' is missing resource limits", [container.c.name, container.kind, container.name])
}

# 9. Prevent internal data services from using LoadBalancer
violation[{"id": "service_type_loadbalancer", "msg": msg}] {
    svc := input.items[_]
    svc.kind == "Service"
    svc.spec.type == "LoadBalancer"
    not is_excepted("service_type_loadbalancer", svc.kind, svc.metadata.name, svc.metadata.namespace)
    msg := sprintf("Security Violation: Service '%s' in namespace '%s' uses prohibited type 'LoadBalancer'", [svc.metadata.name, svc.metadata.namespace])
}

# 10. Prevent internal data services from using NodePort
violation[{"id": "service_type_nodeport", "msg": msg}] {
    svc := input.items[_]
    svc.kind == "Service"
    svc.spec.type == "NodePort"
    not is_excepted("service_type_nodeport", svc.kind, svc.metadata.name, svc.metadata.namespace)
    msg := sprintf("Security Violation: Service '%s' in namespace '%s' uses prohibited type 'NodePort'", [svc.metadata.name, svc.metadata.namespace])
}

# 11. Prevent use of :latest container tags
violation[{"id": "latest_tag", "msg": msg}] {
    container := input_containers[_]
    endswith(container.c.image, ":latest")
    not is_excepted("latest_tag", container.kind, container.name, container.namespace)
    msg := sprintf("Policy Violation: Container '%s' in %s '%s' uses the ':latest' tag", [container.c.name, container.kind, container.name])
}

# 12. Detect dangerous hostPath use
violation[{"id": "hostPath", "msg": msg}] {
    pod := input_pod_specs[_]
    volume := pod.spec.volumes[_]
    volume.hostPath
    not is_excepted("hostPath", pod.kind, pod.name, pod.namespace)
    msg := sprintf("Security Violation: %s '%s' uses dangerous hostPath volume '%s'", [pod.kind, pod.name, volume.name])
}

# 13. Require probes for ShopSphere application Deployments
violation[{"id": "require_probes", "msg": msg}] {
    container := input_containers[_]
    container.kind == "Deployment"
    startswith(container.namespace, "shopsphere-")
    not container.c.livenessProbe
    not is_excepted("require_probes", container.kind, container.name, container.namespace)
    msg := sprintf("Policy Violation: Container '%s' in Deployment '%s' is missing a livenessProbe", [container.c.name, container.name])
}

violation[{"id": "require_probes", "msg": msg}] {
    container := input_containers[_]
    container.kind == "Deployment"
    startswith(container.namespace, "shopsphere-")
    not container.c.readinessProbe
    not is_excepted("require_probes", container.kind, container.name, container.namespace)
    msg := sprintf("Policy Violation: Container '%s' in Deployment '%s' is missing a readinessProbe", [container.c.name, container.name])
}


# --- Helpers ---

input_pod_specs[{"kind": kind, "name": name, "namespace": namespace, "spec": spec}] {
    item := input.items[_]
    item.kind == "Deployment"
    kind := item.kind
    name := item.metadata.name
    namespace := item.metadata.namespace
    spec := item.spec.template.spec
}

input_pod_specs[{"kind": kind, "name": name, "namespace": namespace, "spec": spec}] {
    item := input.items[_]
    item.kind == "DaemonSet"
    kind := item.kind
    name := item.metadata.name
    namespace := item.metadata.namespace
    spec := item.spec.template.spec
}

input_pod_specs[{"kind": kind, "name": name, "namespace": namespace, "spec": spec}] {
    item := input.items[_]
    item.kind == "StatefulSet"
    kind := item.kind
    name := item.metadata.name
    namespace := item.metadata.namespace
    spec := item.spec.template.spec
}

input_containers[{"kind": pod.kind, "name": pod.name, "namespace": pod.namespace, "c": c}] {
    pod := input_pod_specs[_]
    c := pod.spec.containers[_]
}
input_containers[{"kind": pod.kind, "name": pod.name, "namespace": pod.namespace, "c": c}] {
    pod := input_pod_specs[_]
    c := pod.spec.initContainers[_]
}
