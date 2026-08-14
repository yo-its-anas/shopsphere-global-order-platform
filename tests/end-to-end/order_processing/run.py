#!/usr/bin/env python3
# ruff: noqa: E701, E702
"""Live, credential-safe Order Processing validation for the single-node PoC."""

from __future__ import annotations

import concurrent.futures
import json
import os
import secrets
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
CONTEXT = os.getenv("KUBE_CONTEXT", "kind-shopsphere-poc")
PREFIX = f"order-e2e-{secrets.token_hex(5)}"
RESULTS = ROOT / "test-results/end-to-end"
EVIDENCE = ROOT / "docs/evidence/order-processing-e2e-evidence.md"


class CheckError(RuntimeError):
    pass


@dataclass
class Result:
    scenario: str
    status: str
    evidence: str
    seconds: float


def command(args: list[str], stdin: str | None = None, timeout: int = 180) -> str:
    result = subprocess.run(args, input=stdin, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        stage = next(
            (line for line in reversed(result.stdout.splitlines()) if line.startswith("SAFE_STAGE:")),
            "SAFE_STAGE:unspecified",
        )
        raise CheckError(
            f"A controlled platform command failed at {stage.removeprefix('SAFE_STAGE:')}; "
            "inspect cluster events separately."
        )
    return result.stdout.strip()


def kube(*args: str, stdin: str | None = None, timeout: int = 180) -> str:
    return command(["kubectl", "--context", CONTEXT, *args], stdin, timeout)


def find_pod(namespace: str, name: str) -> str:
    value = kube("-n", namespace, "get", "pod", "-l", f"app.kubernetes.io/name={name}", "-o", "jsonpath={.items[0].metadata.name}")
    if not value:
        raise CheckError(f"Required {name} pod was not found.")
    return value


HTTP = r'''
import json,sys,urllib.error,urllib.request
d=json.load(sys.stdin); h={"Accept":"application/json","Authorization":"Bearer "+d["token"],"X-Request-ID":d["request"]}
if d.get("key"): h["Idempotency-Key"]=d["key"]
b=json.dumps(d["body"]).encode() if d.get("body") is not None else None
if b is not None: h["Content-Type"]="application/json"
r=urllib.request.Request("http://127.0.0.1:8000/api/v1"+d["path"],data=b,headers=h,method=d["method"])
try:
 x=urllib.request.urlopen(r,timeout=25); raw=x.read(); print(json.dumps({"status":x.status,"body":json.loads(raw) if raw else None}))
except urllib.error.HTTPError as e:
 raw=e.read()
 try: body=json.loads(raw) if raw else None
 except Exception: body=None
 print(json.dumps({"status":e.code,"body":body}))
'''

TOKEN = r'''
import json,os,sys,urllib.parse,urllib.request
b=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":os.environ["CLIENT"],"client_secret":sys.stdin.read()}).encode()
r=urllib.request.Request(os.environ["SERVICE_TOKEN_URL"],data=b,headers={"Content-Type":"application/x-www-form-urlencoded"})
print(json.load(urllib.request.urlopen(r,timeout=10))["access_token"])
'''


class Live:
    def __init__(self) -> None:
        self.keycloak = find_pod("shopsphere-platform", "keycloak")
        self.gateway = find_pod("shopsphere-apps", "api-gateway")
        self.order = find_pod("shopsphere-apps", "order-service")
        self.catalogue = find_pod("shopsphere-apps", "catalogue-service")
        self.clients: dict[str, dict[str, str]] = {}
        self.tokens: dict[str, str] = {}
        self.orders: list[str] = []
        self.category = ""
        self.kafka_down = False
        self.redis_down = False

    def identities(self) -> None:
        script = r'''
set -Eeuo pipefail
c=/tmp/order-e2e.config; m=/tmp/order-e2e.json; created=""
cleanup_create() { status=$?; if [[ $status -ne 0 ]]; then for value in $created; do "$k" delete "clients/${value}" -r shopsphere --config "$c" >/dev/null 2>&1 || true; done; fi; rm -f "$c" "$m"; exit $status; }
trap cleanup_create EXIT
k=/opt/keycloak/bin/kcadm.sh
echo "SAFE_STAGE:admin-login"
"$k" config credentials --config "$c" --server http://127.0.0.1:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1
echo "SAFE_STAGE:mapper-template"
printf '%s' '{"name":"shopsphere-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper","consentRequired":false,"config":{"included.client.audience":"shopsphere-api","access.token.claim":"true","id.token.claim":"false"}}' >"$m"
for spec in a:customer b:customer admin:operations_admin; do
 n=${spec%%:*}; role=${spec#*:}; client="${E2E_PREFIX}-${n}"
 echo "SAFE_STAGE:create-${n}"
 id=$("$k" create clients -r shopsphere --config "$c" -i -s clientId="$client" -s enabled=true -s protocol=openid-connect -s publicClient=false -s clientAuthenticatorType=client-secret -s standardFlowEnabled=false -s directAccessGrantsEnabled=false -s serviceAccountsEnabled=true -s fullScopeAllowed=true)
 created="$created $id"
 echo "SAFE_STAGE:role-${n}"
 u=$("$k" get "clients/${id}/service-account-user" -r shopsphere --config "$c" --fields username | sed -n 's/.*"username" : "\([^"]*\)".*/\1/p')
 "$k" add-roles -r shopsphere --config "$c" --uusername "$u" --rolename "$role" >/dev/null
 "$k" create "clients/${id}/protocol-mappers/models" -r shopsphere --config "$c" -f "$m" >/dev/null
 echo "SAFE_STAGE:secret-${n}"
 s=$("$k" get "clients/${id}/client-secret" -r shopsphere --config "$c" | sed -n 's/.*"value" : "\([^"]*\)".*/\1/p')
 printf '%s\t%s\t%s\t%s\n' "$n" "$id" "$client" "$s"
done
'''
        try:
            output = kube("-n", "shopsphere-platform", "exec", self.keycloak, "--", "env", f"E2E_PREFIX={PREFIX}", "bash", "-ec", script)
        except Exception as error:
            raise CheckError(f"Temporary Keycloak client creation failed: {error}") from error
        for line in output.splitlines():
            fields = line.split("\t")
            if len(fields) != 4:
                continue
            actor, identity, client, secret = fields
            self.clients[actor] = {"id": identity, "client": client, "secret": secret}
            try:
                self.tokens[actor] = kube("-n", "shopsphere-apps", "exec", "-i", self.order, "--", "env", f"CLIENT={client}", "python", "-c", TOKEN, stdin=secret)
            except Exception as error:
                raise CheckError(f"Token acquisition failed for temporary actor {actor}.") from error
        if set(self.tokens) != {"a", "b", "admin"}:
            raise CheckError("Temporary client creation returned an incomplete safe result.")

    def cleanup(self) -> None:
        for namespace, resource, active in [("shopsphere-platform", "statefulset/kafka", self.kafka_down), ("shopsphere-data", "deployment/redis", self.redis_down)]:
            if active:
                try: self.scale(namespace, resource, 1)
                except Exception: pass
        ids = [item["id"] for item in self.clients.values()]
        if ids:
            script = r'''
c=/tmp/order-e2e-clean.config; trap 'rm -f "$c"' EXIT; k=/opt/keycloak/bin/kcadm.sh
"$k" config credentials --config "$c" --server http://127.0.0.1:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1
for id in "$@"; do "$k" delete "clients/${id}" -r shopsphere --config "$c" >/dev/null 2>&1 || true; done
'''
            try: kube("-n", "shopsphere-platform", "exec", self.keycloak, "--", "bash", "-ec", script, "clean", *ids)
            except Exception: pass
        self.tokens.clear()
        for item in self.clients.values(): item["secret"] = ""

    def api(self, actor: str, method: str, path: str, body: Any = None, key: str | None = None) -> dict[str, Any]:
        request = {"token": self.tokens[actor], "method": method, "path": path, "body": body, "key": key, "request": f"{PREFIX}-{secrets.token_hex(4)}"}
        output = kube("-n", "shopsphere-apps", "exec", "-i", self.gateway, "--", "python", "-c", HTTP, stdin=json.dumps(request), timeout=60)
        return json.loads(output.splitlines()[-1])

    @staticmethod
    def expect(response: dict[str, Any], status: int) -> Any:
        if response["status"] != status:
            code = ((response.get("body") or {}).get("error") or {}).get("code", "unknown")
            raise CheckError(f"Expected HTTP {status}; received {response['status']} ({code}).")
        return response["body"]

    def setup(self) -> str:
        for target in ["keycloak-status", "postgresql-status", "customer-service-status", "catalogue-service-status", "order-service-status", "api-gateway-status", "redis-status", "kafka-status"]:
            command(["make", target], timeout=240)
        try:
            self.identities()
        except Exception as error:
            raise CheckError(str(error)) from error
        try:
            category = self.expect(self.api("admin", "POST", "/categories", {"name": f"Order E2E {PREFIX[-8:]}", "slug": PREFIX, "description": "Synthetic order evidence", "is_active": True}), 201)
        except Exception as error:
            raise CheckError("Synthetic category setup through API Gateway failed.") from error
        self.category = category["id"]
        return "Keycloak, PostgreSQL, customer, catalogue, order, Gateway, Redis and Kafka checks passed; three temporary identities authenticated."

    def product(self, stock: int, price: str) -> str:
        suffix = secrets.token_hex(4).upper()
        product = self.expect(self.api("admin", "POST", "/products", {"sku": f"E2E-{suffix}", "name": f"Synthetic Product {suffix}", "description": "Simulated data", "category_id": self.category, "status": "active", "is_searchable": True}), 201)
        pid = product["id"]
        self.expect(self.api("admin", "PUT", f"/products/{pid}/prices/USD", {"amount": price}), 200)
        self.expect(self.api("admin", "POST", f"/inventory/products/{pid}/initialize", {"quantity_on_hand": stock, "reorder_threshold": 1, "reason": "Synthetic E2E initialization", "reference": PREFIX, "idempotency_key": f"{PREFIX}-{suffix}-stock"}), 201)
        return pid

    def add(self, actor: str, pid: str, quantity: int) -> dict[str, Any]:
        return self.expect(self.api(actor, "POST", "/carts/me/items", {"product_id": pid, "quantity": quantity}), 201)

    def reset_cart(self, actor: str) -> None:
        response = self.api(actor, "DELETE", "/carts/me/items")
        if response["status"] not in {200, 404}:
            self.expect(response, 200)

    def checkout(self, actor: str, key: str) -> dict[str, Any]:
        order = self.expect(self.api(actor, "POST", "/orders/checkout", key=key), 201)
        if order["order_id"] not in self.orders: self.orders.append(order["order_id"])
        return order

    def inventory(self, pid: str) -> dict[str, Any]:
        return self.expect(self.api("admin", "GET", f"/inventory/products/{pid}"), 200)

    def sql(self, service: str, sql: str, values: dict[str, str]) -> list[list[Any]]:
        target = self.order if service == "order" else self.catalogue
        helper = r'''
import json,os,psycopg
url=os.environ["DATABASE_URL"].replace("postgresql+psycopg://","postgresql://")
with psycopg.connect(url,connect_timeout=3) as c: print(json.dumps(c.execute(json.loads(os.environ["QUERY"]),json.loads(os.environ["VALUES"])).fetchall(),default=str))
'''
        output = kube("-n", "shopsphere-apps", "exec", target, "--", "env", f"QUERY={json.dumps(sql)}", f"VALUES={json.dumps(values)}", "python", "-c", helper)
        return json.loads(output.splitlines()[-1])

    def reservations(self, pid: str) -> int:
        return int(self.sql("catalogue", "SELECT count(*) FROM inventory_reservations WHERE product_id=%(id)s::uuid AND status='ACTIVE'", {"id": pid})[0][0])

    def wait_events(self, order: str, expected: set[str], timeout: int = 60) -> list[list[Any]]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rows = self.sql("order", "SELECT event_type,status,attempts FROM order_event_outbox WHERE aggregate_id=%(id)s::uuid ORDER BY occurred_at", {"id": order})
            states = {row[0]: row[1] for row in rows}
            if expected.issubset(states) and all(states[name] == "published" for name in expected): return rows
            time.sleep(1)
        raise CheckError("Expected outbox events did not reach published state within the bounded wait.")

    def scale(self, namespace: str, resource: str, replicas: int) -> None:
        kube("-n", namespace, "scale", resource, f"--replicas={replicas}")
        if replicas: kube("-n", namespace, "rollout", "status", resource, "--timeout=180s", timeout=190)


def success(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(10, "19.9900"); c.add("a", pid, 2)
    if c.expect(c.api("a", "GET", "/carts/me"), 200)["item_count"] != 2: raise CheckError("Cart was not persisted.")
    order = c.checkout("a", f"{PREFIX}-success")
    if order["items"][0]["unit_price"] != "19.9900" or order["total"] != "39.9800": raise CheckError("Server total was incorrect.")
    inv = c.inventory(pid)
    if (inv["quantity_reserved"], inv["quantity_available"]) != (2, 8): raise CheckError("Reservation state was incorrect.")
    listing = c.expect(c.api("a", "GET", "/orders/me?offset=0&limit=100"), 200)
    if sum(item["order_id"] == order["order_id"] for item in listing["items"]) != 1: raise CheckError("Customer history was missing or duplicated.")
    c.expect(c.api("a", "GET", f"/orders/me/{order['order_id']}"), 200)
    history = c.expect(c.api("a", "GET", f"/orders/me/{order['order_id']}/history"), 200)
    audit = c.expect(c.api("a", "GET", f"/orders/me/{order['order_id']}/audit"), 200)
    if not history["items"] or not audit["items"]: raise CheckError("History or audit was empty.")
    rows = c.wait_events(order["order_id"], {"order.created.v1", "order.confirmed.v1"})
    return f"{order['order_number']} ({order['order_id']}) confirmed at USD 39.9800; reserved=2, available=8; {len(rows)} outbox rows observed."


def insufficient(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(2, "7.0000"); before = c.expect(c.api("a", "GET", "/orders/me?limit=100"), 200)["total"]; c.add("a", pid, 3)
    response = c.api("a", "POST", "/orders/checkout", key=f"{PREFIX}-insufficient")
    after = c.expect(c.api("a", "GET", "/orders/me?limit=100"), 200)["total"]; inv = c.inventory(pid)
    if response["status"] != 409 or after != before or inv["quantity_available"] != 2 or inv["quantity_reserved"] != 0 or c.reservations(pid): raise CheckError("Rejected checkout changed authoritative state.")
    return "HTTP 409; no order, negative stock, or stranded ACTIVE reservation."


def price_change(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(5, "10.0000"); cart = c.add("a", pid, 1)
    target = next(item for item in cart["items"] if item["product_id"] == pid)
    if target["display_unit_price"] != "10.0000": raise CheckError("Stale price snapshot was not established.")
    c.expect(c.api("admin", "PUT", f"/products/{pid}/prices/USD", {"amount": "12.5000"}), 200)
    order = c.checkout("a", f"{PREFIX}-price")
    if order["items"][0]["unit_price"] != "12.5000" or order["total"] != "12.5000": raise CheckError("Checkout trusted stale pricing.")
    return f"{order['order_id']} used authoritative USD 12.5000, not stale USD 10.0000."


def retry(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(4, "8.2500"); c.add("a", pid, 1); key = f"{PREFIX}-retry"
    first = c.checkout("a", key); second = c.checkout("a", key)
    count = int(c.sql("order", "SELECT count(*) FROM orders WHERE id=%(id)s::uuid", {"id": first["order_id"]})[0][0])
    if first != second or count != 1 or c.reservations(pid) != 1 or c.inventory(pid)["quantity_reserved"] != 1: raise CheckError("Retry duplicated durable state.")
    return f"Both calls recovered {first['order_id']}; one order and one reservation."


def idor(c: Live) -> str:
    c.reset_cart("b"); pid = c.product(3, "5.0000"); cart = c.add("b", pid, 1); order = c.checkout("b", f"{PREFIX}-idor")
    cart_probe = c.api("a", "GET", f"/carts/{cart['id']}"); order_probe = c.api("a", "GET", f"/orders/me/{order['order_id']}")
    if cart_probe["status"] != 404 or order_probe["status"] != 404: raise CheckError("Cross-customer probe was not denied.")
    return "Arbitrary-cart Gateway path and Customer B order both returned 404 to Customer A."


def race(c: Live) -> str:
    c.reset_cart("a"); c.reset_cart("b"); pid = c.product(1, "6.0000"); c.add("a", pid, 1); c.add("b", pid, 1)
    def attempt(actor: str) -> dict[str, Any]: return c.api(actor, "POST", "/orders/checkout", key=f"{PREFIX}-race-{actor}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: responses = list(pool.map(attempt, ["a", "b"]))
    statuses = sorted(item["status"] for item in responses); inv = c.inventory(pid)
    if statuses != [201, 409] or inv["quantity_available"] != 0 or inv["quantity_reserved"] != 1 or c.reservations(pid) != 1: raise CheckError(f"Race integrity failure: statuses={statuses}.")
    winner = next(item["body"]["order_id"] for item in responses if item["status"] == 201); c.orders.append(winner)
    return f"Concurrent results 201/409; winner={winner}; available=0, reserved=1."


def cancel(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(3, "14.0000"); c.add("a", pid, 1); order = c.checkout("a", f"{PREFIX}-cancel")
    first = c.expect(c.api("a", "POST", f"/orders/me/{order['order_id']}/cancellation"), 200); second = c.expect(c.api("a", "POST", f"/orders/me/{order['order_id']}/cancellation"), 200)
    history = c.expect(c.api("a", "GET", f"/orders/me/{order['order_id']}/history"), 200); audit = c.expect(c.api("a", "GET", f"/orders/me/{order['order_id']}/audit"), 200); inv = c.inventory(pid)
    if first["status"] != "CANCELLED" or second["status"] != "CANCELLED" or sum(x["status"] == "CANCELLED" for x in history["items"]) != 1 or inv["quantity_reserved"] or c.reservations(pid) or not audit["items"]: raise CheckError("Cancellation idempotency/inventory evidence failed.")
    c.wait_events(order["order_id"], {"order.cancelled.v1"})
    return f"{order['order_id']} cancelled twice; one history transition and no ACTIVE reservation."


def kafka(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(3, "11.0000"); c.add("a", pid, 1); c.scale("shopsphere-platform", "statefulset/kafka", 0); c.kafka_down = True
    order = c.checkout("a", f"{PREFIX}-kafka"); rows = c.sql("order", "SELECT status FROM order_event_outbox WHERE aggregate_id=%(id)s::uuid", {"id": order["order_id"]})
    if not rows or all(row[0] == "published" for row in rows) or c.expect(c.api("a", "GET", f"/orders/me/{order['order_id']}"), 200)["status"] != "CONFIRMED": raise CheckError("Kafka outage evidence was inconsistent.")
    c.scale("shopsphere-platform", "statefulset/kafka", 1); c.kafka_down = False; c.wait_events(order["order_id"], {"order.created.v1", "order.confirmed.v1"}, 90)
    return f"{order['order_id']} remained CONFIRMED; pending outbox published after Kafka restoration."


def redis(c: Live) -> str:
    c.reset_cart("a"); pid = c.product(3, "9.0000"); c.scale("shopsphere-data", "deployment/redis", 0); c.redis_down = True; c.add("a", pid, 1); order = c.checkout("a", f"{PREFIX}-redis")
    if order["total"] != "9.0000": raise CheckError("PostgreSQL fallback returned incorrect data.")
    c.scale("shopsphere-data", "deployment/redis", 1); c.redis_down = False
    return f"PostgreSQL fallback confirmed {order['order_id']} at USD 9.0000; Redis restored."


SCENARIOS: list[tuple[str, Callable[[Live], str]]] = [("Prerequisites", Live.setup), ("A — Successful order", success), ("B — Insufficient inventory", insufficient), ("C — Price change", price_change), ("D — Idempotent retry", retry), ("E — IDOR", idor), ("F — Concurrent final unit", race), ("G — Cancellation", cancel), ("H — Kafka failure", kafka), ("I — Redis failure", redis)]


def write_results(items: list[Result], live: Live) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    result_documents = []
    for item in items:
        result_document = asdict(item)
        result_document["classification"] = (
            "Platform Validated"
            if item.scenario == "Prerequisites" and item.status == "passed"
            else "End-to-End Validated"
            if item.status == "passed"
            else "Not Verified"
        )
        result_documents.append(result_document)
    document = {"executed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "simulated_data_prefix": PREFIX, "results": result_documents, "resulting_order_ids": live.orders}
    (RESULTS / "order-processing.json").write_text(json.dumps(document, indent=2) + "\n")
    suite = ET.Element("testsuite", name="order-processing-e2e", tests=str(len(items)), failures=str(sum(x.status == "failed" for x in items)), skipped=str(sum(x.status == "skipped" for x in items)), time=f"{sum(x.seconds for x in items):.3f}")
    for item in items:
        case = ET.SubElement(suite, "testcase", classname="order_processing_e2e", name=item.scenario, time=f"{item.seconds:.3f}")
        if item.status == "failed": ET.SubElement(case, "failure", message=item.evidence)
        if item.status == "skipped": ET.SubElement(case, "skipped", message=item.evidence)
        ET.SubElement(case, "system-out").text = item.evidence
    ET.ElementTree(suite).write(RESULTS / "order-processing.xml", encoding="utf-8", xml_declaration=True)
    lines = ["# Enterprise Order Processing End-to-End Evidence", "", f"Executed: `{document['executed_at_utc']}`", f"Synthetic data prefix: `{PREFIX}`", "", "No password, token, client secret, or Kubernetes Secret value is retained.", "", "| Scenario | Result | Classification | Evidence |", "| --- | --- | --- | --- |"]
    lines += [f"| {x.scenario} | **{x.status.upper()}** | {'Platform Validated' if x.scenario == 'Prerequisites' and x.status == 'passed' else 'End-to-End Validated' if x.status == 'passed' else 'Not Verified'} | {x.evidence} |" for x in items]
    lines += ["", "## Classification", "", "Passed live scenarios are **End-to-End Validated** through API Gateway. Failed or skipped scenarios are **Not Verified**; unit results are not substituted.", "", "## PoC limitation", "", "This tests one VM, one kind node, one PostgreSQL instance, one Redis pod, and one Kafka broker. Outage recovery is not high availability."]
    EVIDENCE.write_text("\n".join(lines) + "\n")


def main() -> int:
    if os.getenv("SHOPSPHERE_RUN_ORDER_E2E", "").lower() != "true":
        print("[SKIP] Explicit SHOPSPHERE_RUN_ORDER_E2E=true opt-in is required.")
        return 2
    live = Live(); results: list[Result] = []
    try:
        for name, function in SCENARIOS:
            start = time.monotonic()
            try:
                evidence = function(live); result = Result(name, "passed", evidence, time.monotonic() - start)
            except Exception as error:
                result = Result(name, "failed", str(error), time.monotonic() - start)
            results.append(result); print(f"[{result.status.upper()}] {name}: {result.evidence}")
            if result.status == "failed": break
    finally:
        live.cleanup(); write_results(results, live)
    return int(any(x.status == "failed" for x in results))


if __name__ == "__main__": raise SystemExit(main())
