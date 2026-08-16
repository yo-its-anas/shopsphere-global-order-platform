package shopsphere.security

test_privileged_denied {
    res := violation with input as {
        "items": [
            {
                "kind": "Deployment",
                "metadata": {"name": "app", "namespace": "shopsphere-apps"},
                "spec": {"template": {"spec": {"containers": [{"name": "app", "securityContext": {"privileged": true}}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "privileged"}) == 1
}

test_privileged_excepted {
    res := violation with input as {
        "items": [
            {
                "kind": "DaemonSet",
                "metadata": {"name": "wazuh-agent", "namespace": "shopsphere-security"},
                "spec": {"template": {"spec": {"containers": [{"name": "wazuh-agent", "securityContext": {"privileged": true}}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "privileged"}) == 0
}

test_latest_tag_denied {
    res := violation with input as {
        "items": [
            {
                "kind": "Deployment",
                "metadata": {"name": "app", "namespace": "shopsphere-apps"},
                "spec": {"template": {"spec": {"containers": [{"name": "app", "image": "nginx:latest"}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "latest_tag"}) == 1
}

test_service_loadbalancer_denied {
    res := violation with input as {
        "items": [
            {
                "kind": "Service",
                "metadata": {"name": "redis", "namespace": "shopsphere-data"},
                "spec": {"type": "LoadBalancer"}
            }
        ]
    }
    count({x | x := res[_]; x.id == "service_type_loadbalancer"}) == 1
}

test_hostPath_denied {
    res := violation with input as {
        "items": [
            {
                "kind": "Deployment",
                "metadata": {"name": "app", "namespace": "shopsphere-apps"},
                "spec": {"template": {"spec": {"containers": [{"name": "app"}], "volumes": [{"name": "danger", "hostPath": {"path": "/var/lib"}}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "hostPath"}) == 1
}

test_runAsNonRoot_denied_when_missing {
    res := violation with input as {
        "items": [
            {
                "kind": "Deployment",
                "metadata": {"name": "app", "namespace": "shopsphere-apps"},
                "spec": {"template": {"spec": {"containers": [{"name": "app", "securityContext": {}}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "runAsNonRoot"}) == 1
}

test_runAsNonRoot_allowed_when_set {
    res := violation with input as {
        "items": [
            {
                "kind": "Deployment",
                "metadata": {"name": "app", "namespace": "shopsphere-apps"},
                "spec": {"template": {"spec": {"securityContext": {"runAsNonRoot": true}, "containers": [{"name": "app"}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "runAsNonRoot"}) == 0
}

test_probes_required_for_apps {
    res := violation with input as {
        "items": [
            {
                "kind": "Deployment",
                "metadata": {"name": "app", "namespace": "shopsphere-apps"},
                "spec": {"template": {"spec": {"containers": [{"name": "app"}]}}}
            }
        ]
    }
    count({x | x := res[_]; x.id == "require_probes"}) == 2 # missing both liveness and readiness
}
