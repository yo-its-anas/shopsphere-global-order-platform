import type { ApiClient } from "./apiClient";
import type {
  CategoryInput,
  InventoryAdjustmentInput,
  InventoryInitializationInput,
  InventoryItem,
  InventoryMovement,
  InventoryMutationResponse,
  InventoryStatistics,
  PageResponse,
  Product,
  ProductAvailability,
  ProductCategory,
  ProductInput,
  ProductPrice,
  ProductSearchParameters,
} from "../types/catalogue";

function queryString(values: Record<string, string | number | boolean | undefined>): string {
  const parameters = new URLSearchParams();
  Object.entries(values).forEach(([name, value]) => {
    if (value !== undefined && value !== "") parameters.set(name, String(value));
  });
  const encoded = parameters.toString();
  return encoded ? `?${encoded}` : "";
}

export class CatalogueApi {
  constructor(private readonly client: ApiClient) {}

  listCategories(
    active?: boolean,
    offset = 0,
    limit = 100,
  ): Promise<PageResponse<ProductCategory>> {
    return this.client.request(`/categories${queryString({ active, offset, limit })}`);
  }

  getCategory(categoryId: string): Promise<ProductCategory> {
    return this.client.request(`/categories/${encodeURIComponent(categoryId)}`);
  }

  createCategory(input: CategoryInput): Promise<ProductCategory> {
    return this.client.request("/categories", { method: "POST", body: JSON.stringify(input) });
  }

  updateCategory(categoryId: string, input: Partial<CategoryInput>): Promise<ProductCategory> {
    return this.client.request(`/categories/${encodeURIComponent(categoryId)}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  }

  listProducts(parameters: ProductSearchParameters = {}): Promise<PageResponse<Product>> {
    return this.client.request(`/products${queryString({ ...parameters })}`);
  }

  getProduct(productId: string): Promise<Product> {
    return this.client.request(`/products/${encodeURIComponent(productId)}`);
  }

  createProduct(input: Required<Pick<ProductInput, "sku">> & ProductInput): Promise<Product> {
    return this.client.request("/products", { method: "POST", body: JSON.stringify(input) });
  }

  updateProduct(productId: string, input: ProductInput): Promise<Product> {
    const update = {
      name: input.name,
      description: input.description,
      category_id: input.category_id,
      status: input.status,
      is_searchable: input.is_searchable,
    };
    return this.client.request(`/products/${encodeURIComponent(productId)}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  }

  deactivateProduct(productId: string): Promise<Product> {
    return this.client.request(`/products/${encodeURIComponent(productId)}/deactivate`, {
      method: "POST",
    });
  }

  listPrices(productId: string, includeHistory = false): Promise<{ items: ProductPrice[] }> {
    return this.client.request(
      `/products/${encodeURIComponent(productId)}/prices${queryString({ include_history: includeHistory })}`,
    );
  }

  setPrice(productId: string, currencyCode: string, amount: string): Promise<ProductPrice> {
    return this.client.request(
      `/products/${encodeURIComponent(productId)}/prices/${encodeURIComponent(currencyCode.toUpperCase())}`,
      { method: "PUT", body: JSON.stringify({ amount }) },
    );
  }

  getAvailability(productId: string): Promise<ProductAvailability> {
    return this.client.request(`/inventory/products/${encodeURIComponent(productId)}/availability`);
  }

  listInventory(state?: string, offset = 0, limit = 25): Promise<PageResponse<InventoryItem>> {
    return this.client.request(`/inventory${queryString({ state, offset, limit })}`);
  }

  getInventory(productId: string): Promise<InventoryItem> {
    return this.client.request(`/inventory/products/${encodeURIComponent(productId)}`);
  }

  initializeInventory(
    productId: string,
    input: InventoryInitializationInput,
  ): Promise<InventoryMutationResponse> {
    return this.client.request(`/inventory/products/${encodeURIComponent(productId)}/initialize`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  adjustInventory(
    productId: string,
    input: InventoryAdjustmentInput,
  ): Promise<InventoryMutationResponse> {
    return this.client.request(`/inventory/products/${encodeURIComponent(productId)}/adjustments`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  listMovements(
    productId: string,
    offset = 0,
    limit = 25,
  ): Promise<PageResponse<InventoryMovement>> {
    return this.client.request(
      `/inventory/products/${encodeURIComponent(productId)}/movements${queryString({ offset, limit })}`,
    );
  }

  getStatistics(): Promise<InventoryStatistics> {
    return this.client.request("/inventory/statistics");
  }
}
