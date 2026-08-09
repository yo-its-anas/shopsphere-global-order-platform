# Customer Profile and Address User Guide

The React customer screens are implemented, but the complete browser-to-live-platform journey has not been validated because API Gateway and frontend are not deployed in the current cluster and the live integration suite has not passed. Use only simulated customer information in demonstrations.

## Registration and sign-in

1. Open `/register` and choose **Continue to secure registration**.
2. Complete the Keycloak-hosted registration form. ShopSphere React and customer-service never receive the password.
3. Use `/login` to redirect to Keycloak for authentication.
4. After successful authentication, the frontend returns to ShopSphere and loads the customer profile through API Gateway.

Keycloak manages password policy, storage, login, logout, and sessions. Password recovery by email is not operational in the PoC because SMTP is not configured.

## Profile

Open **My Profile** at `/profile`. On the first authenticated visit, a missing profile triggers idempotent provisioning from the verified Keycloak identity. The Keycloak `sub`, not email, is the immutable external identity link. Repeated sign-ins should reuse the same domain profile UUID.

Customers may edit allowed name, email, and phone fields. Account status is visible but cannot be administratively changed from customer self-service. Authentication information remains managed by Keycloak.

## Addresses

Open **Addresses** at `/addresses` to:

- add an address;
- view owned addresses;
- edit address fields;
- select a default address; and
- delete an address.

Use a two-letter country code and valid postal/phone formats. The backend resolves ownership from the authenticated subject. Changing an address UUID must not grant access to another customer's address.

## Account activity

Open **Account Activity** at `/account-activity` to request normalized customer-domain and Keycloak activity. The view excludes passwords, tokens, sessions, raw Keycloak details, IP addresses, and administrator secrets. Customer-domain audit history and authentication activity have different sources even when presented together.

If Keycloak is unavailable, merged activity returns a safe unavailable state rather than fabricated authentication events.

## Support and operations access

Support users receive a read-only customer administration view. Operations administrators may also apply explicitly allowed account-status changes. These frontend controls improve usability only; backend role and ownership checks remain authoritative.

## Demonstration evidence

Frontend tests validate authentication redirects, role-aware navigation, profile rendering, address creation/deletion, unauthorized administration, and API error states. During the current review, 11 frontend tests passed and the production build succeeded. The profile/address APIs and integration tests exist, but their live execution is not current success evidence. Do not describe the user journey as complete until those suites pass against the PoC.
