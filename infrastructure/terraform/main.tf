# This root module describes the single-VM ShopSphere proof of concept only.
# It is deliberately not the recommended production design. Production should use
# a separately reviewed, regional GKE architecture with managed data services,
# multiple failure domains, workload identity, autoscaling, and disaster recovery.

check "zone_belongs_to_region" {
  assert {
    condition     = startswith(var.gcp_zone, "${var.gcp_region}-")
    error_message = "gcp_zone must belong to gcp_region."
  }
}

check "public_web_sources_are_explicit" {
  assert {
    condition     = !var.enable_public_web_ingress || length(var.web_source_cidrs) > 0
    error_message = "When enable_public_web_ingress is true, web_source_cidrs must contain at least one explicitly approved CIDR."
  }
}
