#!/usr/bin/env python3
import json
import yaml

def gen_overview():
    return {
        "title": "ShopSphere Service Overview",
        "description": "Availability, rate, errors, and latency for core services",
        "uid": "service-overview",
        "tags": ["shopsphere", "overview"],
        "schemaVersion": 38,
        "panels": [
            {
                "type": "stat",
                "title": "Service Up/Down",
                "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0},
                "targets": [
                    {
                        "expr": "up{job=\"shopsphere-applications\"}",
                        "legendFormat": "{{service}}",
                        "refId": "A"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "thresholds"},
                        "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]}
                    }
                }
            },
            {
                "type": "timeseries",
                "title": "Request Rate (rps)",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                "targets": [
                    {
                        "expr": "sum by (service) (rate(http_requests_total{job=\"shopsphere-applications\"}[1m]))",
                        "legendFormat": "{{service}}",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "Error Rate (HTTP 5xx)",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                "targets": [
                    {
                        "expr": "sum by (service) (rate(http_requests_total{job=\"shopsphere-applications\", status=~\"5..\"}[1m]))",
                        "legendFormat": "{{service}}",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "P95 Latency",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 12},
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket{job=\"shopsphere-applications\"}[5m])))",
                        "legendFormat": "{{service}}",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "Pod Restarts",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 12},
                "targets": [
                    {
                        "expr": "sum by (pod) (kube_pod_container_status_restarts_total{namespace=\"shopsphere-apps\"})",
                        "legendFormat": "{{pod}}",
                        "refId": "A"
                    }
                ]
            }
        ]
    }

def gen_api_perf():
    return {
        "title": "API Performance",
        "description": "Deep dive into API requests, latency, and status codes",
        "uid": "api-performance",
        "tags": ["shopsphere", "api", "performance"],
        "schemaVersion": 38,
        "panels": [
            {
                "type": "timeseries",
                "title": "Requests by Status Code",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "targets": [
                    {
                        "expr": "sum by (status) (rate(http_requests_total{job=\"shopsphere-applications\"}[1m]))",
                        "legendFormat": "{{status}}",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "Slowest Routes (P99)",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "targets": [
                    {
                        "expr": "histogram_quantile(0.99, sum by (le, method, route, service) (rate(http_request_duration_seconds_bucket{job=\"shopsphere-applications\"}[5m]))) > 0",
                        "legendFormat": "{{service}} {{method}} {{route}}",
                        "refId": "A"
                    }
                ]
            }
        ]
    }

def gen_order_ops():
    return {
        "title": "Order Processing Operations",
        "description": "Business operations metrics for orders and inventory",
        "uid": "order-ops",
        "tags": ["shopsphere", "business", "operations"],
        "schemaVersion": 38,
        "panels": [
            {
                "type": "timeseries",
                "title": "Checkout Attempts vs Success",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "targets": [
                    {
                        "expr": "sum by (status) (rate(shopsphere_checkout_attempts_total[5m]))",
                        "legendFormat": "{{status}} attempts",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "Inventory Reservation Operations",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "targets": [
                    {
                        "expr": "sum by (status) (rate(shopsphere_inventory_reservations_total[5m]))",
                        "legendFormat": "{{status}}",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "Outbox Event Publication",
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                "targets": [
                    {
                        "expr": "sum by (event_type, service) (rate(shopsphere_outbox_events_published_total[5m]))",
                        "legendFormat": "{{service}} - {{event_type}}",
                        "refId": "A"
                    }
                ]
            }
        ]
    }

def gen_platform_health():
    return {
        "title": "Platform Health",
        "description": "Infrastructure and dependency health",
        "uid": "platform-health",
        "tags": ["shopsphere", "infrastructure", "health"],
        "schemaVersion": 38,
        "panels": [
            {
                "type": "stat",
                "title": "Nodes Ready",
                "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {
                        "expr": "sum(kube_node_status_condition{condition=\"Ready\", status=\"true\"})",
                        "legendFormat": "Nodes",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "CPU Usage by Namespace",
                "gridPos": {"h": 8, "w": 9, "x": 6, "y": 0},
                "targets": [
                    {
                        "expr": "sum by (namespace) (rate(container_cpu_usage_seconds_total{container!=\"POD\", container!=\"\"}[5m]))",
                        "legendFormat": "{{namespace}}",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "timeseries",
                "title": "Memory Usage by Namespace",
                "gridPos": {"h": 8, "w": 9, "x": 15, "y": 0},
                "targets": [
                    {
                        "expr": "sum by (namespace) (container_memory_working_set_bytes{container!=\"POD\", container!=\"\"})",
                        "legendFormat": "{{namespace}}",
                        "refId": "A"
                    }
                ]
            }
        ]
    }

def main():
    cm = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "grafana-dashboards-json",
            "namespace": "shopsphere-monitoring"
        },
        "data": {
            "1-shopsphere-service-overview.json": json.dumps(gen_overview(), indent=2),
            "2-api-performance.json": json.dumps(gen_api_perf(), indent=2),
            "3-order-processing-operations.json": json.dumps(gen_order_ops(), indent=2),
            "4-platform-health.json": json.dumps(gen_platform_health(), indent=2)
        }
    }
    print(yaml.dump(cm))

if __name__ == "__main__":
    main()
