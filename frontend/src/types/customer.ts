export type CustomerStatus = "active" | "suspended" | "closed";

export interface CustomerProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  status: CustomerStatus;
  created_at: string;
  updated_at: string;
}

export interface ProfileProvisioningResponse {
  profile: CustomerProfile;
  provisioned: boolean;
}

export interface ProfileUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string | null;
}

export interface CustomerAddress {
  id: string;
  label: string;
  recipient_name: string;
  line1: string;
  line2: string | null;
  city: string;
  region: string | null;
  postal_code: string;
  country_code: string;
  phone: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AddressInput {
  label: string;
  recipient_name: string;
  line1: string;
  line2?: string | null;
  city: string;
  region?: string | null;
  postal_code: string;
  country_code: string;
  phone?: string | null;
  is_default?: boolean;
}

export interface ActivityEvent {
  timestamp: string;
  event_category: string;
  action: string;
  source: string;
  result: string;
  context: Record<string, unknown>;
}

export interface ActivityListResponse {
  items: ActivityEvent[];
  offset: number;
  limit: number;
}

export interface ProfileListResponse {
  items: CustomerProfile[];
  offset: number;
  limit: number;
}
