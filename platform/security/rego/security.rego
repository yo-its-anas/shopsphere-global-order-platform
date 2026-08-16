package shopsphere.security

default allow = true

# Violation rule to check for privileged containers, excluding wazuh-agent
violation[msg] {
    some i, j
    input.items[i].kind == "Deployment"
    input.items[i].spec.template.spec.containers[j].securityContext.privileged == true
    input.items[i].metadata.name != "wazuh-agent"
    msg := sprintf("Security Violation: Privileged container detected in Deployment '%s'", [input.items[i].metadata.name])
}

# Violation rule to check for missing liveness probe, excluding datastores
violation[msg] {
    some i, j
    input.items[i].kind == "Deployment"
    container := input.items[i].spec.template.spec.containers[j]
    not container.livenessProbe
    # Allow third party system or database containers to bypass if needed, but enforce for core apps
    regex.match("^(api-gateway|customer-service|catalogue-service|order-service|analytics-service)", input.items[i].metadata.name)
    msg := sprintf("Policy Violation: Core container '%s' in Deployment '%s' is missing a livenessProbe", [container.name, input.items[i].metadata.name])
}
