# ADR-008: Use a monorepo for the enterprise capstone

## Status

Accepted — the repository contains the planned service, frontend, shared, infrastructure, platform, test, documentation, and script boundaries.

## Context

The capstone has one delivery team, shared governance, and a need for a single traceable evidence pack. Coordinated changes will often span API contracts, services, platform assets, tests, and documentation.

## Decision

Maintain all ShopSphere source and governance assets in one monorepo with explicit top-level ownership boundaries. Use path-aware CI and CODEOWNERS as governance matures. Do not treat repository co-location as permission for uncontrolled service coupling.

## Alternatives considered

- Repository per service: stronger isolation but creates administration, cross-repository coordination, and evidence overhead.
- Separate application and platform repositories: credible for larger organizations but inefficient for the single-team capstone.
- One undifferentiated source tree: simple initially but obscures ownership and deployment boundaries.

## Consequences

Atomic cross-cutting changes and unified evidence become easier. Repository size, pipeline duration, access boundaries, and accidental coupling can grow; directory ownership and selective builds are therefore required.

## Security implications

Repository access potentially exposes a broader code surface. Apply branch protection, reviews, secret scanning, dependency controls, least-privilege CI credentials, and path ownership. No runtime secrets or generated state belong in the monorepo.

## PoC limitations

Current CODEOWNERS entries are placeholders, and path-filtered pipelines are not implemented. The current repository size does not validate monorepo scaling characteristics.

## Production evolution

Introduce enforceable ownership, affected-component builds, artifact provenance, release versioning, dependency boundaries, and access reviews. Split repositories only if organizational or regulatory ownership demands outweigh coordination benefits.

## Viva defence notes

Defend the choice using team topology and delivery economics. A monorepo is not a monolith: deployability and data ownership are architectural properties, while repository layout is a collaboration choice.
