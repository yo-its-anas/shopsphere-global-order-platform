# ShopSphere System Architecture Maps (Diagrams 1–5)

This document contains the core structural maps of the ShopSphere Global Enterprise Order Management Platform, representing the actual implemented single-node PoC cluster.

---

## Diagram 1: Enterprise Software Architecture Diagram

### Purpose
Provides a holistic view of the major business capabilities of the ShopSphere platform, mapping them to their technical ownership layers.

### Mermaid Diagram
```mermaid
graph TD
    subgraph ClientLayer [Client Presentation]
        FE[React Frontend]
    end

    subgraph EdgeLayer [API Platform & Ingress]
        GW[API Gateway]
    end

    subgraph CoreCapabilities [Core Business Capabilities]
        subgraph ID [Identity]
            KC[Keycloak OIDC]
        end
        subgraph Customer [Customer Management]
            CS[customer-service]
        end
        subgraph CatalogueCap [Catalogue & Inventory]
            CAT[catalogue-service]
        end
        subgraph OrderCap [Order Processing]
            OS[order-service]
        end
        subgraph AnalyticsCap [Executive Analytics]
            AS[analytics-service]
        end
    end

    subgraph PlatformLayer [Security & Observability]
        PROM[Prometheus Scraper]
        GRAF[Grafana Dashboards]
        LOKI[Loki Log Server]
        OTEL[OTEL Collector]
        WAZUH[Wazuh SIEM]
    end

    FE -->|HTTPS| GW
    GW -->|Validate Token| KC
    GW -->|Forward Profile| CS
    GW -->|Forward Catalogue| CAT
    GW -->|Forward Checkout| OS
    GW -->|Forward Ops| AS

    %% Observability Scrapes
    PROM -.->|Scrape| CS
    PROM -.->|Scrape| CAT
    PROM -.->|Scrape| OS
    PROM -.->|Scrape| AS
    PROM -.->|Scrape| GW
```

### Accompanying Metadata
*   **Main Components:** React frontend, API Gateway, 4 active backend microservices (Customer, Catalogue, Order, Analytics), Keycloak IAM, and 5 observability/security utilities.
*   **Key Flow:** Browsers hit the API Gateway, which delegates identity checks to Keycloak before proxying commerce calls to backend owners.
*   **Architecture Decisions:** Separated Customer profile sync from Keycloak OIDC login scopes (ADR-005) to ensure database schemas never hold credential tables.
*   **PoC Limitations:** Single-node host shares resources across all layers, causing performance contention under parallel quality pipelines.
*   **Viva Talking Points:** "How do we prevent customer profile replication errors? We enforce profile-sync at first login via idempotent PUT calls from the client, keyed only by Keycloak's validated sub."

---

## Diagram 2: High-Level Solution Architecture Diagram

### Purpose
Maps the technical relationships, protocols, and datastores connecting the React frontend, API Gateway, and backend microservices.

### Mermaid Diagram
```mermaid
graph LR
    Browser[React Browser Client] -->|HTTPS / W3C Trace| GW[API Gateway]
    
    subgraph DataApps [Core Applications & Datastores]
        GW -->|REST / JWT| CS[customer-service]
        GW -->|REST / JWT| CAT[catalogue-service]
        GW -->|REST / JWT| OS[order-service]
        GW -->|REST / JWT| AS[analytics-service]
        
        CS -->|psycopg| DB[(PostgreSQL Server)]
        CAT -->|psycopg| DB
        OS -->|psycopg| DB
        AS -->|HTTP| PROM[Prometheus]
        
        CAT -->|Cache-aside| REDIS[(Redis Cache)]
        OS -.->|Asynchronous Outbox| KAFKA[[Kafka KRaft Broker]]
        CAT -.->|Asynchronous Outbox| KAFKA
    end

    subgraph IAM [Identity Provider]
        GW -->|OIDC / JWKS| KC[Keycloak]
    end
```

### Accompanying Metadata
*   **Main Components:** React Single Page App, API Gateway, microservices, Keycloak, PostgreSQL (shared instance, isolated logical DBs), Redis, and Kafka KRaft.
*   **Key Flow:** API Gateway validates the incoming JWT against Keycloak JWKS, propagates correlation headers, and forwards requests. Catalogue-service leverages Redis cache-aside (ADR-006) for fast availability checks.
*   **Architecture Decisions:** Retained KRaft single-broker Kafka (ADR-007) to remove ZooKeeper and simplify single-node Kind orchestration.
*   **PoC Limitations:** Databases share a single PostgreSQL StatefulSet failure domain.
*   **Viva Talking Points:** "We enforce transactional outbox publishing on Catalogue and Order services (ADR-011) to ensure at-least-once message delivery to Kafka without risking two-phase commit overhead on a shared database server."

---

## Diagram 3: Detailed System Architecture Diagram

### Purpose
Details the physical container layout, namespaces, and virtual networking of the deployed `kind-shopsphere-poc` Kubernetes cluster.

### Mermaid Diagram
```mermaid
graph TD
    subgraph UbuntuVM [GCP N2-Standard-8 Host VM]
        subgraph KindCluster [Kind Kubernetes Cluster: shopsphere-poc]
            
            subgraph NamespaceApps [Namespace: shopsphere-apps]
                GW[api-gateway Pod]
                CS[customer-service Pod]
                CAT[catalogue-service Pod]
                OS[order-service Pod]
                AS[analytics-service Pod]
            end

            subgraph NamespaceData [Namespace: shopsphere-data]
                PG[(postgresql-0 StatefulSet)]
                RD[(redis-0 StatefulSet)]
            end

            subgraph NamespacePlatform [Namespace: shopsphere-platform]
                KC[keycloak-0 StatefulSet]
                KF[[kafka-0 StatefulSet]]
            end

            subgraph NamespaceMonitoring [Namespace: shopsphere-monitoring]
                PROM[prometheus-0 Deployment]
                GRAF[grafana-0 Deployment]
                LOKI[loki-0 StatefulSet]
                PROMTAIL[[promtail DaemonSet]]
                OTEL[opentelemetry-collector Deployment]
            end

            subgraph NamespaceSecurity [Namespace: shopsphere-security]
                WAZUH_MGR[wazuh-manager Deployment]
                WAZUH_AGT[[wazuh-agent DaemonSet]]
            end
        end
    end

    %% Network Policies
    GW -->|ClusterIP 8000| CS
    GW -->|ClusterIP 8000| CAT
    GW -->|ClusterIP 8000| OS
    GW -->|ClusterIP 8000| AS
    
    CS -->|Port 5432| PG
    CAT -->|Port 5432| PG
    CAT -->|Port 6379| RD
    OS -->|Port 5432| PG
    
    OS -->|Port 9092| KF
    CAT -->|Port 9092| KF
```

### Accompanying Metadata
*   **Main Components:** 5 isolated Kubernetes namespaces (`shopsphere-apps`, `shopsphere-data`, `shopsphere-platform`, `shopsphere-monitoring`, `shopsphere-security`) hosted on an Ubuntu GCP VM.
*   **Key Flow:** Pods communicate exclusively via secure, internal ClusterIP services. External traffic is locked down via host firewall mappings.
*   **Architecture Decisions:** Bound all databases and core services to internal ClusterIP-only networks to prevent public cloud exposure.
*   **PoC Limitations:** Host virtualization (Docker-in-Docker kind node) isolates the Wazuh DaemonSet from native host-level VM processes.
*   **Viva Talking Points:** "How do we isolate namespaces? We apply custom NetworkPolicies (e.g. `analytics-service-ingress`) to restrict cross-namespace traffic strictly to approved ports and pods."

---

## Diagram 4: Microservices Architecture Diagram

### Purpose
Highlights the API boundaries, system-to-service communication paths, and transactional state ownership.

### Mermaid Diagram
```mermaid
graph TD
    subgraph API_Platform [Inbound Transit]
        GW[API Gateway]
    end

    subgraph Microservices [Authoritative Microservices]
        CS[customer-service]
        CAT[catalogue-service]
        OS[order-service]
        AS[analytics-service]
    end

    subgraph StateOwnership [Authoritative Databases]
        C_DB[(customer_db)]
        CAT_DB[(catalogue_db)]
        O_DB[(order_db)]
    end

    GW -->|GET/PATCH /api/v1/customers| CS
    GW -->|GET/POST /api/v1/products| CAT
    GW -->|POST /api/v1/orders| OS
    GW -->|GET /api/v1/operations| AS

    %% DB Mapping
    CS ===|Owns/Queries Only| C_DB
    CAT ===|Owns/Queries Only| CAT_DB
    OS ===|Owns/Queries Only| O_DB

    %% Inter-service Queries
    OS -->|REST Query| CAT
    AS -->|REST Query| CS
    AS -->|REST Query| CAT
    AS -->|REST Query| OS

    %% Database Isolation Violations Blocked
    O_DB -.-x|PROHIBITED DIRECT QUERY| CAT_DB
    C_DB -.-x|PROHIBITED DIRECT QUERY| O_DB
```

### Accompanying Metadata
*   **Main Components:** API Gateway, 4 microservice boundaries, 3 logically isolated database state boundaries.
*   **Key Flow:** Microservices own their databases exclusively. The `order-service` must query `catalogue-service` over secure REST APIs to revalidate prices and reserve inventory; direct cross-database queries are strictly prohibited (ADR-001).
*   **Architecture Decisions:** Enforced complete database decoupling. Each service uses dedicated SQLAlchemy engines and separate migration graphs (Alembic).
*   **PoC Limitations:** Logical databases share a single PostgreSQL master node.
*   **Viva Talking Points:** "Why can't order-service read catalogue_db directly? Direct queries break domain encapsulation, couple service schemas permanently, and bypass localized cache-aside optimizations (Redis)."

---

## Diagram 5: API Gateway Architecture Diagram

### Purpose
Exposes the ingress security loop, Bearer token validations, and headers propagation logic of the gateway.

### Mermaid Diagram
```mermaid
sequenceDiagram
    autonumber
    actor Browser as Browser Client
    participant GW as API Gateway
    participant KC as Keycloak (JWKS)
    participant CS as customer-service

    Browser->>GW: POST /api/v1/orders/checkout [Authorization: Bearer <JWT>]
    Note over GW: 1. Generate correlation_id (UUID)<br/>2. Extract W3C Traceparent
    GW->>KC: Fetch JWKS (cached)
    KC-->>GW: Return RS256 Public Keys
    Note over GW: 3. Verify Signature & Expiry<br/>4. Assert Client Role (customer)
    
    GW->>CS: POST /api/v1/orders/checkout
    Note over CS: Traceparent & Correlation ID propagated in logs
    CS-->>GW: HTTP 201 Created
    GW-->>Browser: HTTP 201 Created [X-Request-ID: correlation_id]
```

### Accompanying Metadata
*   **Main Components:** FastAPI APIRouter proxy clients, httpx2 async forwarding clients, Keycloak JWKS cache.
*   **Key Flow:** The gateway intercepts all requests, generates a structured `correlation_id` (propagated downstream), validates JWT signatures against cached JWKS, and blocks unauthenticated requests before proxying (ADR-004).
*   **Architecture Decisions:** Selected FastAPI as a transport-only routing gateway (no embedded business logic) to maintain capability-focused service layers.
*   **PoC Limitations:** Distributed rate limiting is not implemented at the gateway level.
*   **Viva Talking Points:** "How do we prevent token forgery? The gateway intercepts the public JWT and strictly validates it against Keycloak's active JWKS certificates before forwarding, completely neutralizing forged credentials."
