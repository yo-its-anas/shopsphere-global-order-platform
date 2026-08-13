export type ProductStatus = "draft" | "active" | "inactive" | "discontinued";
export type AvailabilityState = "in_stock" | "low_stock" | "out_of_stock";
export type InventoryMovementType =
  "INITIAL_STOCK" | "STOCK_RECEIPT" | "MANUAL_ADJUSTMENT" | "DAMAGE" | "CORRECTION";

export interface PageResponse<T> {
  items: T[];
  offset: number;
  limit: number;
  total: number;
}

export interface ProductCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryInput {
  name: string;
  slug: string;
  description?: string;
  is_active: boolean;
  parent_id?: string | null;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  description: string | null;
  category_id: string;
  status: ProductStatus;
  is_searchable: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductInput {
  sku?: string;
  name: string;
  description?: string;
  category_id: string;
  status: ProductStatus;
  is_searchable: boolean;
}

export interface ProductPrice {
  id: string;
  product_id: string;
  amount: string;
  currency_code: string;
  is_active: boolean;
  effective_from: string;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductAvailability {
  product_id: string;
  quantity_available: number;
  state: AvailabilityState;
  as_of: string;
}

export interface ProductCardData {
  product: Product;
  price: ProductPrice | null;
  availability: ProductAvailability | null;
}

export interface ProductSearchParameters {
  query?: string;
  sku?: string;
  category_id?: string;
  status?: ProductStatus;
  offset?: number;
  limit?: number;
  sort_by?: "created_at" | "name" | "sku" | "updated_at";
  sort_direction?: "asc" | "desc";
}

export interface InventoryItem {
  id: string;
  product_id: string;
  location_code: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  reorder_threshold: number;
  state: AvailabilityState;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface InventoryMovement {
  id: string;
  inventory_item_id: string;
  product_id: string;
  movement_type: InventoryMovementType;
  quantity_delta: number;
  reserved_delta: number;
  previous_quantity_on_hand: number;
  resulting_quantity_on_hand: number;
  previous_quantity_reserved: number;
  resulting_quantity_reserved: number;
  reason: string;
  reference: string | null;
  actor_subject: string;
  correlation_id: string;
  idempotency_key: string;
  occurred_at: string;
}

export interface InventoryMutationResponse {
  inventory: InventoryItem;
  movement: InventoryMovement;
}

export interface InventoryStatistics {
  location_code: string;
  total_products_tracked: number;
  in_stock_products: number;
  low_stock_products: number;
  out_of_stock_products: number;
  total_units_on_hand: number;
  reserved_units: number;
  available_units: number;
  calculated_at: string;
}

export interface InventoryAdjustmentInput {
  movement_type: Exclude<InventoryMovementType, "INITIAL_STOCK">;
  quantity_delta: number;
  reason: string;
  reference?: string;
  idempotency_key: string;
  expected_version: number;
}

export interface InventoryInitializationInput {
  quantity_on_hand: number;
  reorder_threshold: number;
  reason: string;
  reference?: string;
  idempotency_key: string;
}
