# Redis PoC Overlay

Create the runtime Secrets with `make redis-secret` or `make redis-secret-generate`, then apply with `make redis-apply`. The helper places the same generated/provided password in `shopsphere-data/shopsphere-redis-credentials` and `shopsphere-apps/shopsphere-catalogue-cache` without displaying it.

Redis is an ephemeral cache with no PVC. Restart or eviction clears cached entries and catalogue-service reconstructs them from PostgreSQL. This is appropriate for the PoC cache role and is not production high availability.
