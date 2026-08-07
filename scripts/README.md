# Scripts

Contains small, reviewed automation entry points for repeatable local and CI tasks. Scripts must be safe by default, portable where practical, and must not embed credentials.

## Day 1 environment validation

- `check-host.sh` reports read-only Ubuntu host capacity and network-listener information.
- `check-docker.sh` checks the Docker CLI, daemon access, Compose, and Buildx.
- `check-kubernetes-tools.sh` checks local `kubectl` and kind clients without contacting or changing a cluster.
- `check-terraform.sh` checks the Terraform CLI.
- `check-jenkins.sh` reports only non-sensitive systemd service state.
- `capture-tool-versions.sh` writes sanitized version evidence to `docs/evidence/tool-versions.md`.

Run all checks with `make doctor`. A non-zero result means one or more prerequisites need attention; scripts never install packages or modify host services.
