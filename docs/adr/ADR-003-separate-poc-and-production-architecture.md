# ADR-003: Separate the PoC architecture from the recommended GKE production architecture

## Status

Accepted — separate documentation and Kubernetes overlay locations exist. Detailed diagrams, manifests, and production designs remain planned.

## Context

The single-VM PoC intentionally cannot satisfy enterprise production qualities. Mixing implemented topology with future recommendations would create misleading evidence and weaken architectural traceability.

## Decision

Maintain distinct PoC and production-reference views. The PoC view describes only demonstrable assets and constraints. The production view recommends GKE and enterprise-grade resilience, security, operations, and managed services. Documentation and Kubernetes overlays remain explicitly separated.

## Alternatives considered

- One architecture diagram with annotations: compact but easy to misinterpret.
- Document only the PoC: fails to demonstrate production design competence.
- Build the production architecture during the capstone: outside the seven-day scope and cost envelope.

## Consequences

Claims remain auditable and the gap between demonstration and recommendation is visible. Documentation must be maintained in parallel and reviewers must understand that production-reference artifacts are not deployment evidence.

## Security implications

The separation prevents PoC shortcuts from becoming implicit production controls. Production guidance must specify stronger IAM, secrets, networking, supply-chain, audit, backup, and incident-response measures.

## PoC limitations

Current evidence is limited to directory separation and explanatory READMEs. No complete PoC or production diagrams, threat models, or manifests exist yet.

## Production evolution

Develop a GKE deployment view, trust boundaries, data flows, availability model, capacity model, recovery objectives, and control mapping. Validate recommendations through architecture review before adoption.

## Viva defence notes

Use this ADR to distinguish evidence from aspiration. Explain why a credible architect records constraints and provides an evolutionary path without claiming that a reference design has been deployed.
