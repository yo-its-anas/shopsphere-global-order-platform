locals {
  common_labels = merge(var.additional_labels, {
    environment = var.environment
    project     = var.project_label
    managed_by  = "terraform"
  })

  ssh_firewall_name = "${var.project_label}-${var.environment}-allow-ssh"
  web_firewall_name = "${var.project_label}-${var.environment}-allow-web"

  ssh_network_tag = "${var.project_label}-${var.environment}-ssh"
  web_network_tag = "${var.project_label}-${var.environment}-web"

  vm_network_tags = concat(
    [local.ssh_network_tag],
    var.enable_public_web_ingress ? [local.web_network_tag] : []
  )
}
