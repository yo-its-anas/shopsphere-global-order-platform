output "network_name" {
  description = "PoC VPC network name."
  value       = google_compute_network.poc.name
}

output "subnet_name" {
  description = "PoC subnet name."
  value       = google_compute_subnetwork.poc.name
}

output "instance_name" {
  description = "PoC Compute Engine instance name."
  value       = google_compute_instance.poc.name
}

output "instance_zone" {
  description = "PoC Compute Engine instance zone."
  value       = google_compute_instance.poc.zone
}

output "static_external_ip" {
  description = "Reserved PoC external IP. Treat as operational infrastructure data."
  value       = google_compute_address.poc.address
}

output "public_web_ingress_enabled" {
  description = "Whether the controlled HTTP/HTTPS firewall rule is enabled."
  value       = var.enable_public_web_ingress
}
