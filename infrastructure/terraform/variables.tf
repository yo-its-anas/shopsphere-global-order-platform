variable "gcp_project_id" {
  description = "Existing Google Cloud project ID. Supply this manually; do not commit it."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.gcp_project_id))
    error_message = "gcp_project_id must be a valid 6-30 character Google Cloud project ID."
  }
}

variable "gcp_region" {
  description = "Google Cloud region containing the existing PoC resources."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.gcp_region))
    error_message = "gcp_region must resemble a Google Cloud region such as europe-west2."
  }
}

variable "gcp_zone" {
  description = "Google Cloud zone containing the existing PoC VM."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+-[a-z]$", var.gcp_zone))
    error_message = "gcp_zone must resemble a Google Cloud zone such as europe-west2-a."
  }
}

variable "environment" {
  description = "Deployment environment label. This baseline is intentionally PoC-only."
  type        = string
  default     = "poc"

  validation {
    condition     = var.environment == "poc"
    error_message = "This root module supports only the PoC environment. Build production GKE separately."
  }
}

variable "project_label" {
  description = "Stable workload label; this is not the Google Cloud project ID."
  type        = string
  default     = "shopsphere"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_-]{0,62}$", var.project_label))
    error_message = "project_label must be a valid lowercase Google Cloud label value."
  }
}

variable "additional_labels" {
  description = "Optional non-sensitive labels merged with the mandatory project and environment labels."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for key, value in var.additional_labels :
      can(regex("^[a-z][a-z0-9_-]{0,62}$", key)) &&
      can(regex("^[a-z0-9_-]{0,63}$", value))
    ])
    error_message = "Additional label keys and values must follow Google Cloud lowercase label syntax."
  }
}

variable "network_name" {
  description = "Name of the existing or planned custom-mode VPC network."
  type        = string
  default     = "shopsphere-poc-vpc"

  validation {
    condition     = can(regex("^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$", var.network_name))
    error_message = "network_name must be a valid Google Cloud resource name."
  }
}

variable "subnet_name" {
  description = "Name of the existing or planned PoC subnet."
  type        = string
  default     = "shopsphere-poc-subnet"

  validation {
    condition     = can(regex("^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$", var.subnet_name))
    error_message = "subnet_name must be a valid Google Cloud resource name."
  }
}

variable "subnet_cidr" {
  description = "Private IPv4 CIDR for the PoC subnet. Confirm it matches the existing subnet before import."
  type        = string
  nullable    = false

  validation {
    condition = can(cidrhost(var.subnet_cidr, 0)) && (
      startswith(var.subnet_cidr, "10.") ||
      startswith(var.subnet_cidr, "192.168.") ||
      can(regex("^172[.](1[6-9]|2[0-9]|3[01])[.]", var.subnet_cidr))
    )
    error_message = "subnet_cidr must be a valid RFC1918 IPv4 CIDR."
  }
}

variable "instance_name" {
  description = "Name of the existing Google Compute Engine VM."
  type        = string
  default     = "shopsphere-poc-vm"

  validation {
    condition     = can(regex("^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$", var.instance_name))
    error_message = "instance_name must be a valid Google Compute Engine instance name."
  }
}

variable "machine_type" {
  description = "Compute Engine machine type for the PoC VM."
  type        = string
  default     = "n2-standard-8"

  validation {
    condition     = var.machine_type == "n2-standard-8"
    error_message = "This PoC baseline is validated for n2-standard-8 (8 vCPU and 32 GB RAM)."
  }
}

variable "boot_disk_size_gb" {
  description = "Balanced persistent boot disk size in GiB. Confirm the existing disk size before import."
  type        = number
  default     = 300

  validation {
    condition     = var.boot_disk_size_gb >= 100 && var.boot_disk_size_gb <= 500 && floor(var.boot_disk_size_gb) == var.boot_disk_size_gb
    error_message = "boot_disk_size_gb must be a whole number between 100 and 500 GiB."
  }
}

variable "boot_disk_type" {
  description = "Compute Engine disk type for the PoC boot disk."
  type        = string
  default     = "pd-balanced"

  validation {
    condition     = var.boot_disk_type == "pd-balanced"
    error_message = "This PoC baseline requires a balanced persistent disk (pd-balanced)."
  }
}

variable "boot_image" {
  description = "Public Ubuntu 22.04 LTS image family used only if a VM is deliberately created."
  type        = string
  default     = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"

  validation {
    condition     = var.boot_image == "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
    error_message = "This PoC baseline requires the official Ubuntu 22.04 LTS image family."
  }
}

variable "static_ip_name" {
  description = "Name of the existing or planned regional static external IP address."
  type        = string
  default     = "shopsphere-poc-ip"

  validation {
    condition     = can(regex("^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$", var.static_ip_name))
    error_message = "static_ip_name must be a valid Google Cloud resource name."
  }
}

variable "ssh_source_cidr" {
  description = "Required trusted IPv4 CIDR allowed to reach SSH. Never use 0.0.0.0/0."
  type        = string
  nullable    = false

  validation {
    condition = (can(cidrhost(var.ssh_source_cidr, 0)) &&
      can(regex("^[0-9.]+/[0-9]{1,2}$", var.ssh_source_cidr)) &&
    can(tonumber(split("/", var.ssh_source_cidr)[1]) >= 8))
    error_message = "ssh_source_cidr must be a valid restricted IPv4 CIDR with a /8 to /32 prefix; unrestricted /0 networks are rejected."
  }
}

variable "enable_public_web_ingress" {
  description = "Explicit switch for public HTTP/HTTPS ingress preparation. Disabled by default."
  type        = bool
  default     = false
}

variable "web_source_cidrs" {
  description = "Explicit IPv4 CIDRs allowed to reach ports 80 and 443 when public web ingress is enabled."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.web_source_cidrs :
      can(cidrhost(cidr, 0)) && can(regex("^[0-9.]+/[0-9]{1,2}$", cidr))
    ])
    error_message = "Every web_source_cidrs entry must be a valid IPv4 CIDR."
  }
}

variable "vm_service_account_email" {
  description = "Optional email of an existing least-privilege service account. No account or key is created."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = var.vm_service_account_email == null || can(regex(
      "^[a-z0-9-]+@[a-z0-9-]+\\.iam\\.gserviceaccount\\.com$",
      var.vm_service_account_email
    ))
    error_message = "vm_service_account_email must be null or a valid Google service-account email."
  }
}

variable "vm_service_account_scopes" {
  description = "OAuth scopes for the optional existing VM service account. IAM roles remain the authorization boundary."
  type        = list(string)
  default     = ["https://www.googleapis.com/auth/cloud-platform"]

  validation {
    condition     = length(var.vm_service_account_scopes) > 0 && alltrue([for scope in var.vm_service_account_scopes : startswith(scope, "https://www.googleapis.com/auth/")])
    error_message = "At least one valid Google API OAuth scope URL is required."
  }
}

variable "enable_os_login" {
  description = "Enable OS Login and block project-wide SSH keys on the VM. Review compatibility before importing."
  type        = bool
  default     = true
}
