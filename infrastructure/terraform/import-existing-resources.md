# Import Existing Google Cloud Resources

Use this runbook only after confirming that each remote object is the intended ShopSphere PoC resource. Import changes Terraform state; it does not change the remote resource, but a later apply can. Back up approved state, use a dedicated workspace, and never commit state or plan files.

This guide does not authorize `terraform apply`, resource deletion, VM recreation, service interruption, or service-account key generation.

## 1. Collect and verify identifiers

Supply these manually through ignored `terraform.tfvars` or temporary shell variables in your own trusted terminal:

- Google Cloud project ID;
- region and VM zone;
- VPC network name;
- subnet name and exact private CIDR;
- reserved static external IP resource name;
- SSH and optional web firewall-rule names;
- VM name, machine type, disk properties, image lineage, network tags, labels, metadata, service account, and deletion-protection state;
- trusted SSH source CIDR.

Do not copy credentials, tokens, private keys, Jenkins passwords, or service-account keys into Terraform variables.

## 2. Initialize without a backend

For syntax and provider validation only:

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

Before a durable import, configure an approved remote backend using `backend.tf.example`, initialize it deliberately, and confirm access controls and state recovery. Do not migrate existing state casually.

## 3. Match configuration before import

Update the ignored `terraform.tfvars` with the **exact** existing names and properties. In particular, compare:

- subnet CIDR, region, private Google access, and VPC routing mode;
- address region and network tier;
- firewall directions, priorities, sources, targets, ports, and logging;
- VM zone, machine type, boot disk type/size/auto-delete, image, NIC, static IP, service account, scopes, tags, labels, metadata, Shielded VM settings, and deletion protection.

The baseline intentionally prefers secure settings. An imported object may differ. Import does not reconcile those differences; the next plan will display proposed changes, including possible replacement.

## 4. Import resources

Set shell variables to verified, non-secret identifiers in your trusted session. The examples below deliberately contain no real values:

```bash
export TF_VAR_gcp_project_id="replace-with-project-id"
export TF_VAR_gcp_region="replace-with-region"
export TF_VAR_gcp_zone="replace-with-zone"
export TF_VAR_ssh_source_cidr="replace-with-trusted-ipv4-cidr"
```

Import the existing network:

```bash
terraform import google_compute_network.poc \
  "projects/${TF_VAR_gcp_project_id}/global/networks/replace-with-network-name"
```

Import the existing subnet:

```bash
terraform import google_compute_subnetwork.poc \
  "projects/${TF_VAR_gcp_project_id}/regions/${TF_VAR_gcp_region}/subnetworks/replace-with-subnet-name"
```

Import the existing regional static IP:

```bash
terraform import google_compute_address.poc \
  "projects/${TF_VAR_gcp_project_id}/regions/${TF_VAR_gcp_region}/addresses/replace-with-address-name"
```

Import the restricted SSH firewall rule:

```bash
terraform import google_compute_firewall.ssh \
  "projects/${TF_VAR_gcp_project_id}/global/firewalls/replace-with-ssh-firewall-name"
```

If and only if `enable_public_web_ingress = true` and a matching approved rule already exists, import it at its counted address:

```bash
terraform import 'google_compute_firewall.web[0]' \
  "projects/${TF_VAR_gcp_project_id}/global/firewalls/replace-with-web-firewall-name"
```

Import the existing VM last, after its network and address are represented in state:

```bash
terraform import google_compute_instance.poc \
  "projects/${TF_VAR_gcp_project_id}/zones/${TF_VAR_gcp_zone}/instances/replace-with-instance-name"
```

These commands import only the specified resource addresses. They do not import related disks, IAM policies, DNS records, or other firewall rules as separately managed resources.

## 5. Review state and plan without applying

Use read-only state inspection and save a reviewable plan locally:

```bash
terraform state list
terraform plan -out=shopsphere-poc.tfplan
terraform show shopsphere-poc.tfplan
```

Stop if the plan contains `destroy`, replacement (`-/+` or `+/-`), VM stopping, disk recreation, external IP change, network replacement, broad ingress, unexpected IAM changes, or removal of deletion protection. Correct the configuration or resource mapping and plan again. Do not bypass `prevent_destroy` to make a plan pass.

## Firewall-rule mapping caveat

Existing environments may use separate HTTP and HTTPS rules, different target tags, or centrally managed firewall policy. Do not import multiple remote rules into one Terraform address. Either adapt the reviewed configuration to represent each rule faithfully or leave centrally managed rules outside this state and document ownership.

## Safe exit

This repository does not prescribe state removal commands because they can detach governance unexpectedly. If a resource was imported to the wrong address, stop and obtain peer review before changing state. Import completion is not approval to apply.
