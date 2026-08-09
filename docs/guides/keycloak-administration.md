# Keycloak Administrator Guide

Keycloak owns ShopSphere identities, passwords, password policies, login/logout, sessions, tokens, roles, and authentication events. Customer-service owns profiles, addresses, account metadata, and customer-domain audit history. Never place customer passwords in customer-service, PostgreSQL customer tables, Jenkins parameters, application logs, or documentation.

## Protected administration access

Keycloak is ClusterIP-only. From the Ubuntu host, bind a loopback port:

```bash
kubectl --context kind-shopsphere-poc \
  -n shopsphere-platform port-forward --address 127.0.0.1 service/keycloak 8081:8080
```

From Windows, create an SSH tunnel in a separate PowerShell session:

```powershell
ssh -L 8081:127.0.0.1:8081 anas@YOUR_APPROVED_VM_ADDRESS
```

Open `http://127.0.0.1:8081/admin/` locally. Replace the VM address explicitly; do not commit it. Obtain the bootstrap administrator username/password through the approved secret-management process. This guide intentionally does not print retrieval commands or secret values.

## Realm structure

- Realm: `shopsphere`
- Roles: `customer`, `support`, `operations_admin`
- Public browser client: `shopsphere-frontend`, Authorization Code Flow only, S256 PKCE, no client secret
- Resource audience: `shopsphere-api`
- Activity reader: `shopsphere-customer-activity-reader`, confidential service account with only `realm-management/view-events`

Self-registration assigns `customer` by default. Grant `support` and `operations_admin` only through an approved administrative process with a recorded business owner and periodic review. Never use frontend role visibility as proof of authorization; customer-service enforces permissions.

## Safe reconciliation and verification

```bash
make keycloak-configure
make keycloak-status
```

Reconciliation is idempotent for the managed client policies and activity reader. Realm startup import does not overwrite an existing realm. Treat changes to live realm state, redirect URIs, roles, token lifetimes, or event retention as reviewed migrations.

The status check verifies registration, password and brute-force policy, refresh-token behavior, realm roles, default customer assignment, public-client properties, PKCE, event recording, PostgreSQL connectivity, and least-privilege event-reader access without displaying tokens or client secrets.

## Password and recovery limitations

The realm enforces password complexity and history and enables brute-force protection. Reset-password functionality is configured, but SMTP is absent, so email recovery is not operational. Verified email and MFA are not implemented. Do not manually reset customer credentials for demonstrations unless an approved, audited administrative procedure has been defined.

## Production administration

Production requires private administrative connectivity, individual administrator identities, MFA, separation of duties, external secret storage and rotation, resilient identity hosting, regional database availability, audited configuration changes, durable event export, backup/restore tests, incident response, and periodic role review. The single PoC Keycloak pod and PostgreSQL pod on one VM do not provide host-level high availability.
