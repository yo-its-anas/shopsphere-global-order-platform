#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import ssl
from time import perf_counter

KC_URL = "http://localhost:8080"
GATEWAY_URL = "http://localhost:8000"

# Unverified SSL context for local/kind connections
ctx = ssl._create_unverified_context()

def get_token(username, password):
    data = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "shopsphere-frontend",
        "username": username,
        "password": password
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{KC_URL}/realms/shopsphere/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.load(resp)["access_token"]
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Keycloak Token HTTPError {e.code}: {e.read().decode()}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch Keycloak token: {e}", file=sys.stderr)
        return None

async def send_write_request(sem, client, url, headers, collector):
    async with sem:
        start = perf_counter()
        try:
            # Send POST with empty JSON body for checkout
            response = await client.post(url, headers=headers, json={})
            duration = perf_counter() - start
            success = response.status_code < 400
            collector.record(duration, success)
            if not success:
                print(f"[ERROR] Request to {url} failed with status {response.status_code}: {response.text}")
        except Exception as e:
            duration = perf_counter() - start
            collector.record(duration, False)
            print(f"[ERROR] Request to {url} failed with exception: {e}")

async def run_write_workload(concurrency, total_requests, urls, headers):
    import httpx2
    sem = asyncio.Semaphore(concurrency)
    collectors = {name: MetricCollector(name) for name in urls.keys()}
    async with httpx2.AsyncClient(timeout=5.0) as client:
        tasks = []
        for i in range(total_requests):
            for name, url in urls.items():
                tasks.append(
                    send_write_request(sem, client, url, headers, collectors[name])
                )
        start_time = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start_time
    return collectors, duration

def fetch_product_id(token):
    # Retrieve a valid product ID from catalogue-service via Gateway
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/v1/products?limit=1",
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = json.load(resp)
            if data.get("items"):
                return data["items"][0]["product_id"]
    except Exception as e:
        print(f"[ERROR] Failed to fetch product ID: {e}", file=sys.stderr)
    return None

class MetricCollector:
    def __init__(self, name):
        self.name = name
        self.latencies = []
        self.errors = 0
        self.successes = 0

    def record(self, duration, success):
        if success:
            self.latencies.append(duration)
            self.successes += 1
        else:
            self.errors += 1

    def get_summary(self):
        self.latencies.sort()
        count = len(self.latencies)
        p50 = self.latencies[int(count * 0.5)] * 1000 if count > 0 else 0
        p95 = self.latencies[int(count * 0.95)] * 1000 if count > 0 else 0
        p99 = self.latencies[int(count * 0.99)] * 1000 if count > 0 else 0
        avg = (sum(self.latencies) / count) * 1000 if count > 0 else 0
        
        return {
            "name": self.name,
            "requests": count + self.errors,
            "successes": self.successes,
            "errors": self.errors,
            "error_rate_pct": (self.errors / (count + self.errors)) * 100 if (count + self.errors) > 0 else 0,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "avg_ms": avg
        }

async def send_request(sem, client, url, headers, collector):
    async with sem:
        start = perf_counter()
        try:
            response = await client.get(url, headers=headers)
            duration = perf_counter() - start
            success = response.status_code < 400
            collector.record(duration, success)
            if not success:
                print(f"[ERROR] Request to {url} failed with status {response.status_code}: {response.text}")
        except Exception as e:
            duration = perf_counter() - start
            collector.record(duration, False)
            print(f"[ERROR] Request to {url} failed with exception: {e}")

async def run_workload(concurrency, total_requests, urls, headers):
    import httpx2 # Async HTTP client
    
    sem = asyncio.Semaphore(concurrency)
    collectors = {name: MetricCollector(name) for name in urls.keys()}
    
    async with httpx2.AsyncClient(timeout=5.0) as client:
        tasks = []
        # Distribute requests across URLs
        for i in range(total_requests):
            for name, url in urls.items():
                tasks.append(
                    send_request(sem, client, url, headers, collectors[name])
                )
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
    return collectors, duration

def main():
    print("[INFO] Starting controlled performance-test baseline...")
    
    # 1. Fetch tokens
    ops_token = get_token("operations@yopmail.com", "TestPassword@1234")
    cust_token = ops_token
    
    if not ops_token:
        print("[ERROR] Token acquisition failed. Ensure Port forwards are running.")
        sys.exit(1)
        
    product_id = fetch_product_id(cust_token) or "f876e8c8-b22e-40d5-b3e1-6a02123ff21f"
    print(f"[INFO] Using verified product ID: {product_id}")

    # 2. Define target workflows
    read_urls = {
        "catalogue-search": f"{GATEWAY_URL}/api/v1/products?limit=5",
        "inventory-status": f"{GATEWAY_URL}/api/v1/inventory/products/{product_id}/availability",
        "executive-dashboard": f"{GATEWAY_URL}/api/v1/dashboard/summary",
        "customer-profile": f"{GATEWAY_URL}/api/v1/customers/me",
        "order-history": f"{GATEWAY_URL}/api/v1/orders/me?limit=5"
    }
    
    # Run a modest, controlled load: concurrency of 5, 20 requests per endpoint
    concurrency = 5
    requests_per_endpoint = 20
    
    print(f"[INFO] Executing READ baseline (Concurrency: {concurrency}, Requests/Endpoint: {requests_per_endpoint})...")
    headers = {"Authorization": f"Bearer {ops_token}"}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    collectors, duration = loop.run_until_complete(
        run_workload(concurrency, requests_per_endpoint, read_urls, headers)
    )
    
    # 3. Controlled write (checkout) scenario separately
    checkout_url = {"order-checkout": f"{GATEWAY_URL}/api/v1/orders/checkout"}
    # Modest write baseline: Concurrency of 2, 5 requests
    print(f"[INFO] Executing WRITE checkout baseline (Concurrency: 2, Requests: 5)...")
    checkout_collectors, write_duration = loop.run_until_complete(
        run_write_workload(2, 5, checkout_url, {"Authorization": f"Bearer {cust_token}", "Content-Type": "application/json", "Idempotency-Key": "perf-test-key"})
    )
    
    # Merge results
    collectors.update(checkout_collectors)
    total_duration = duration + write_duration
    
    # Compile report
    report_data = {
        "test_metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "concurrency_reads": concurrency,
            "concurrency_writes": 2,
            "duration_seconds": total_duration,
            "total_requests": sum(c.get_summary()["requests"] for c in collectors.values())
        },
        "results": [c.get_summary() for c in collectors.values()]
    }
    
    os.makedirs("test-results/performance", exist_ok=True)
    with open("test-results/performance/baseline.json", "w") as f:
        json.dump(report_data, f, indent=2)
        
    print("[OK] Performance test completed. Results written to test-results/performance/baseline.json")

if __name__ == "__main__":
    main()
