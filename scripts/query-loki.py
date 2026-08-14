#!/usr/bin/env python3
import json
import subprocess
import sys
import urllib.parse

def query_loki(query, limit=5):
    # Properly URL-encode the parameters for raw path
    encoded_query = urllib.parse.quote(query)
    path = f"/api/v1/namespaces/shopsphere-monitoring/services/http:loki:3100/proxy/loki/api/v1/query_range?query={encoded_query}&limit={limit}"
    
    cmd = ["kubectl", "--context", "kind-shopsphere-poc", "get", "--raw", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to query Loki API via kubectl: {e}\nStderr: {e.stderr}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Failed to parse Loki response: {e}", file=sys.stderr)
        return None

def print_logs_for_service(service, limit=3):
    print(f"\n==========================================")
    print(f"QUERYING LOKI LOGS FOR SERVICE: {service}")
    print(f"==========================================")
    
    query = f'{{service="{service}"}}'
    res = query_loki(query, limit=limit)
    if not res:
        return []
        
    results = res.get("data", {}).get("result", [])
    if not results:
        print("No logs found for this service in Loki.")
        return []
        
    log_lines = []
    for stream_info in results:
        stream_labels = stream_info.get("stream", {})
        for val in stream_info.get("values", []):
            timestamp, log_msg = val[0], val[1]
            print(f"[{timestamp}] labels={stream_labels}\n  -> {log_msg}")
            log_lines.append(log_msg)
    return log_lines

def demonstrate_correlation_search(correlation_id):
    print(f"\n==========================================")
    print(f"DEMONSTRATING SEARCH BY CORRELATION_ID: {correlation_id}")
    print(f"==========================================")
    
    # We use LogQL filter pipeline to search within the log line content
    query = f'{{environment="poc"}} |= "{correlation_id}"'
    res = query_loki(query, limit=5)
    if not res:
        print("Failed to run correlation search.")
        return
        
    results = res.get("data", {}).get("result", [])
    if not results:
        print(f"No logs matched the correlation ID {correlation_id}.")
        return
        
    for stream_info in results:
        for val in stream_info.get("values", []):
            timestamp, log_msg = val[0], val[1]
            print(f"[{timestamp}] MATCHED LOG:\n  -> {log_msg}")

def verify_no_secrets_in_logs(log_lines):
    print(f"\n==========================================")
    print(f"VERIFYING SECRETS ARE NOT VISIBLE IN LOGS")
    print(f"==========================================")
    
    # Secrets we want to ensure are not present in logs
    prohibited_keywords = [
        "eyJhG", "password", "client_secret", "KC_BOOTSTRAP_ADMIN", "KEYCLOAK_PASSWORD"
    ]
    
    clean = True
    for line in log_lines:
        for kw in prohibited_keywords:
            if kw in line:
                print(f"[WARNING] Potential secret/sensitive keyword '{kw}' found in log: {line}")
                clean = False
                
    if clean:
        print("[OK] Verified: No JWTs, passwords, client secrets, or credentials visible in the sampled logs.")
    else:
        print("[ERROR] Potential secrets discovered in logs.")

def main():
    services = ["api-gateway", "customer-service", "catalogue-service", "order-service"]
    all_logs = []
    sample_correlation_id = None
    
    for s in services:
        logs = print_logs_for_service(s, limit=3)
        all_logs.extend(logs)
        
        # Try to find a sample correlation_id to demonstrate search
        for log in logs:
            if sample_correlation_id:
                break
            try:
                parsed = json.loads(log)
                corr_id = parsed.get("correlation_id")
                if corr_id and corr_id != "unassigned":
                    sample_correlation_id = corr_id
            except Exception:
                pass
                
    if sample_correlation_id:
        demonstrate_correlation_search(sample_correlation_id)
    else:
        # Fallback to a query using a wildcard or a static check if none found
        print("\n[INFO] No active correlation_id found in sampled JSON logs yet.")
        
    verify_no_secrets_in_logs(all_logs)

if __name__ == "__main__":
    main()
