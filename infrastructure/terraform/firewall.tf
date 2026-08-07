resource "google_compute_firewall" "ssh" {
  name        = local.ssh_firewall_name
  description = "Restrict SSH to the explicitly supplied trusted source CIDR."
  network     = google_compute_network.poc.id
  direction   = "INGRESS"
  priority    = 1000

  source_ranges = [var.ssh_source_cidr]
  target_tags   = [local.ssh_network_tag]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_firewall" "web" {
  count = var.enable_public_web_ingress ? 1 : 0

  name        = local.web_firewall_name
  description = "Explicitly controlled HTTP/HTTPS ingress for the future PoC ingress controller."
  network     = google_compute_network.poc.id
  direction   = "INGRESS"
  priority    = 1000

  source_ranges = var.web_source_cidrs
  target_tags   = [local.web_network_tag]

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }

  lifecycle {
    precondition {
      condition     = length(var.web_source_cidrs) > 0
      error_message = "Public web ingress requires at least one explicitly controlled source CIDR."
    }
  }
}

# Intentionally absent: public ingress rules for PostgreSQL (5432), Redis (6379),
# Kafka (9092), Keycloak administration (commonly 8080/8443), Jenkins (commonly
# 8080/50000), Kubernetes control-plane ports, and observability administration.
# These services remain bound to private/container networks and are not public.
