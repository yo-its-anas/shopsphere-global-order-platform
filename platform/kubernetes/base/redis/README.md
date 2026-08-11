# Redis Cache Base

Defines one authenticated, internal Redis cache in `shopsphere-data`. Its ACL permits only the catalogue key namespace and required `GET`, `SET`, `UNLINK`, `SCAN`, and `PING` commands. It uses `ClusterIP`, restricted security contexts, probes, bounded memory with `allkeys-lru`, and a NetworkPolicy intended to admit catalogue-service only.

Redis stores reconstructable cache entries only. Persistence is deliberately disabled because PostgreSQL is authoritative and Redis loss must result in cache misses, not data loss. This one-pod deployment is not highly available. NetworkPolicy enforcement requires a compatible CNI; kindnet does not enforce these policies.
