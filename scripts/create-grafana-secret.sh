#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-monitoring"
readonly SECRET_NAME="grafana-admin-credentials"

info() {
    printf '[INFO] %s\n' "$*"
}

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found."
}

generate_password() {
    openssl rand -base64 48 | tr -d '\n'
}

read_password() {
    local prompt="$1"
    local destination="$2"
    local first_value=""
    local second_value=""

    read -r -s -p "$prompt: " first_value
    printf '\n'
    read -r -s -p "Confirm ${prompt}: " second_value
    printf '\n'

    [[ ${#first_value} -ge 12 ]] || fail "Passwords must contain at least 12 characters."
    [[ "$first_value" == "$second_value" ]] || fail "Password confirmation did not match."
    printf -v "$destination" '%s' "$first_value"
}

encode() {
    printf '%s' "$1" | base64 | tr -d '\n'
}

main() {
    local mode="${1:-interactive}"
    local admin_password=""
    
    require_command kubectl
    require_command openssl

    if ! kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" >/dev/null 2>&1; then
        fail "Namespace '${NAMESPACE}' does not exist or the cluster is unreachable."
    fi

    if kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
        info "Secret '${SECRET_NAME}' already exists. Recreating it will invalidate active sessions."
        read -r -p "Do you want to overwrite it? (yes/NO): " confirm
        if [[ "${confirm,,}" != "yes" ]]; then
            info "Aborting. Existing secret was preserved."
            exit 0
        fi
        kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" delete secret "$SECRET_NAME" >/dev/null
    fi

    if [[ "$mode" == "--generate" ]]; then
        info "Generating secure random password for Grafana admin..."
        admin_password="$(generate_password)"
    else
        info "Enter a strong password for the Grafana 'admin' user (input will be hidden)."
        read_password "Grafana admin password" admin_password
    fi

    info "Creating Kubernetes Secret..."
    
    # We use a declarative manifest instead of imperative literal creation to ensure clean metadata
    local manifest
    manifest="$(cat <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${SECRET_NAME}
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: grafana
type: Opaque
data:
  admin-password: $(encode "${admin_password}")
  admin-user: $(encode "admin")
EOF
)"

    printf '%s\n' "${manifest}" | kubectl --context "$KUBE_CONTEXT" apply -f - >/dev/null
    
    info "Grafana admin credentials successfully stored in secret '${SECRET_NAME}'."
    
    if [[ "$mode" == "--generate" ]]; then
        info "Remember to retrieve the generated password securely when logging in:"
        info "kubectl --context \"${KUBE_CONTEXT}\" -n \"${NAMESPACE}\" get secret \"${SECRET_NAME}\" -o jsonpath='{.data.admin-password}' | base64 -d"
    fi
}

main "$@"