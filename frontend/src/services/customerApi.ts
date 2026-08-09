import type {
  ActivityListResponse,
  AddressInput,
  CustomerAddress,
  CustomerProfile,
  CustomerStatus,
  ProfileListResponse,
  ProfileProvisioningResponse,
  ProfileUpdate,
} from "../types/customer";
import { ApiClientError, type ApiClient } from "./apiClient";

export class CustomerApi {
  constructor(private readonly client: ApiClient) {}

  async getOrProvisionProfile(): Promise<CustomerProfile> {
    try {
      return await this.client.request<CustomerProfile>("/customers/me");
    } catch (error) {
      if (!(error instanceof ApiClientError) || error.status !== 404) throw error;
      const response = await this.client.request<ProfileProvisioningResponse>("/customers/me", {
        method: "PUT",
      });
      return response.profile;
    }
  }

  updateProfile(update: ProfileUpdate): Promise<CustomerProfile> {
    return this.client.request("/customers/me", {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  }

  listAddresses(): Promise<CustomerAddress[]> {
    return this.client.request("/customers/me/addresses");
  }

  createAddress(input: AddressInput): Promise<CustomerAddress> {
    return this.client.request("/customers/me/addresses", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  updateAddress(addressId: string, input: Partial<AddressInput>): Promise<CustomerAddress> {
    return this.client.request(`/customers/me/addresses/${encodeURIComponent(addressId)}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  }

  deleteAddress(addressId: string): Promise<void> {
    return this.client.request(`/customers/me/addresses/${encodeURIComponent(addressId)}`, {
      method: "DELETE",
    });
  }

  setDefaultAddress(addressId: string): Promise<CustomerAddress> {
    return this.client.request(`/customers/me/addresses/${encodeURIComponent(addressId)}/default`, {
      method: "PUT",
    });
  }

  listOwnActivity(offset = 0, limit = 50): Promise<ActivityListResponse> {
    return this.client.request(`/customers/me/activity?offset=${offset}&limit=${limit}`);
  }

  listCustomers(offset = 0, limit = 50): Promise<ProfileListResponse> {
    return this.client.request(`/admin/customers?offset=${offset}&limit=${limit}`);
  }

  changeCustomerStatus(customerId: string, status: CustomerStatus): Promise<CustomerProfile> {
    const reasonCode = "administrative_correction";
    return this.client.request(`/admin/customers/${encodeURIComponent(customerId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, reason_code: reasonCode }),
    });
  }
}
