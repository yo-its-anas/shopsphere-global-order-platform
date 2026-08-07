resource "google_compute_network" "poc" {
  name                    = var.network_name
  description             = "ShopSphere PoC custom-mode VPC; not the production GKE network design."
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_subnetwork" "poc" {
  name                     = var.subnet_name
  description              = "ShopSphere PoC subnet for the existing single VM and kind workloads."
  region                   = var.gcp_region
  network                  = google_compute_network.poc.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_address" "poc" {
  name         = var.static_ip_name
  description  = "Reserved external IPv4 address for controlled ShopSphere PoC ingress."
  region       = var.gcp_region
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"

  lifecycle {
    prevent_destroy = true
  }
}
