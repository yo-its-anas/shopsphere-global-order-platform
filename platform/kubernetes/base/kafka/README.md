# Apache Kafka Event Broker

This opt-in base defines one Apache Kafka 4.3.1 broker/controller in KRaft combined mode. It runs in `shopsphere-platform`, uses a retained 10 Gi PVC, and exposes only internal Kubernetes Services. There is no ZooKeeper, public listener, NodePort, LoadBalancer, or host-port mapping.

The `kafka` client Service is `ClusterIP`; `kafka-headless` gives the single StatefulSet pod a stable controller identity. NetworkPolicy permits port 9092 from `catalogue-service` and permits the broker's own KRaft controller traffic. Enforcement requires a compatible CNI. The PoC uses plaintext only inside the cluster boundary and has no broker ACLs; that is a documented PoC security limitation, not a production recommendation.

The broker writes logs and KRaft metadata to `kafka-data-kafka-0`. Retention helps events survive an ordinary pod restart, but one PVC, node, VM, broker, and controller provide no replication, failover, infrastructure isolation, or host-level high availability. The image needs writable configuration/data paths during startup, so `readOnlyRootFilesystem` is not enabled; it still runs as non-root, drops capabilities, disables privilege escalation, and does not mount a service-account token.

Topic creation is explicit because auto-creation is disabled. Use `make kafka-topics` after the broker is Ready.
