# Platform Foundation Checklist

Date: 2026-08-07  
Scope: repository foundation only

## Repository structure

- [x] Backend service boundaries created for customer, catalogue, order, analytics, and API gateway.
- [x] React frontend and governed shared-assets areas created.
- [x] Terraform, kind, Kubernetes base, PoC overlay, and production-reference overlay created.
- [x] Jenkins, monitoring, and security platform areas created.
- [x] Unit, integration, end-to-end, and performance test areas created.
- [x] Architecture, ADR, API, guide, standards, viva, and evidence documentation areas created.
- [x] Major directories include concise ownership README files.

## Governance and safety

- [x] Root purpose, modules, architecture, stack, and capability delivery model documented.
- [x] `.gitignore` covers Python, Node, Terraform, IDE, secret, Kubernetes, and test artifacts.
- [x] `.editorconfig` establishes consistent text formatting.
- [x] `.env.example` contains placeholders only.
- [x] Security, contribution, and code-owner placeholders added.
- [x] Make targets are non-destructive placeholders.
- [x] No business features, credentials, Terraform state, binaries, or vendor directories created.

## Review evidence

- [ ] Replace placeholder CODEOWNERS handles with real repository principals.
- [ ] Review naming and boundaries with the project supervisor.
- [x] Record approved and proposed architecture decisions as indexed ADRs.
- [ ] Capture the reviewed platform-foundation commit identifier.
