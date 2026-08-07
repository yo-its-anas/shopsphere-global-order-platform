resource "google_compute_instance" "poc" {
  name         = var.instance_name
  description  = "Existing ShopSphere single-VM PoC host; not a production GKE node."
  zone         = var.gcp_zone
  machine_type = var.machine_type

  deletion_protection       = true
  allow_stopping_for_update = false
  can_ip_forward            = false

  labels = local.common_labels
  tags   = local.vm_network_tags

  boot_disk {
    auto_delete = false

    initialize_params {
      image = var.boot_image
      size  = var.boot_disk_size_gb
      type  = var.boot_disk_type
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.poc.id

    access_config {
      nat_ip       = google_compute_address.poc.address
      network_tier = "PREMIUM"
    }
  }

  metadata = var.enable_os_login ? {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
  } : {}

  dynamic "service_account" {
    for_each = var.vm_service_account_email == null ? [] : [var.vm_service_account_email]

    content {
      email  = service_account.value
      scopes = var.vm_service_account_scopes
    }
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    provisioning_model  = "STANDARD"
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = true
    enable_vtpm                 = true
  }

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = startswith(var.gcp_zone, "${var.gcp_region}-")
      error_message = "The VM zone must belong to the configured region."
    }
  }
}
