import { merchantClient } from "./merchant-client";

export type Shop = {
  id: number;
  name: string;
  description: string;
  address_line: string;
  area: string;
  city: string;
  state: string;
  pincode: string;
  contact_number: string;
  status: string;
  is_temporarily_closed: boolean;
  opening_time: string | null;
  closing_time: string | null;
  is_home_delivery_enabled: boolean;
  is_pickup_enabled: boolean;
  delivery_fee_type: "FIXED" | "CONFIRMED_ON_WHATSAPP";
  delivery_charge: string;
  pending_order_timeout_minutes: number;
  public_slug: string;
  public_url: string;
};

export type MerchantOrder = {
  id: number;
  status: "PENDING" | "ACCEPTED" | "PREPARING" | "READY" | "COMPLETED" | "REJECTED";
  payment_status: "UNPAID" | "PAID";
  fulfillment_type: "PICKUP" | "HOME_DELIVERY";
  customer_name_snapshot: string;
  customer_phone_snapshot: string;
  items: Array<{
    id: number;
    product_name_snapshot: string;
    variant_name_snapshot: string;
    ordered_quantity: string;
    quantity: string;
    unit_price_snapshot: string;
    line_total: string;
  }>;
  items_subtotal: string;
  delivery_charge_snapshot: string;
  total_amount: string;
  expires_at: string | null;
  created_at: string;
  delivery_address?: {
    address_line: string;
    area: string;
    city: string;
    state: string;
    pincode: string;
    landmark?: string;
    delivery_notes?: string;
  } | null;
  rejection_note?: string;
};

export type Product = {
  id: number;
  name: string;
  description: string;
  brand: string;
  price: string;
  sku: string;
  is_visible: boolean;
  is_available: boolean;
  has_variants: boolean;
  categories: number[];
};

export type InventoryItem = {
  id: number;
  product: number;
  product_name: string;
  variant: number | null;
  variant_name: string | null;
  sku: string | null;
  quantity: string;
  reserved_quantity: string;
  available_quantity: string;
  is_out_of_stock: boolean;
  has_variants: boolean;
};

export type Customer = {
  id: number;
  name: string;
  whatsapp_number: string;
  created_at: string;
};

export type Overview = {
  period: string;
  orders: {
    total_orders: number;
    completed_orders: number;
    rejected_orders: number;
    status_distribution: Record<string, number>;
  };
  sales: { realized_sales: string; average_order_value: string };
  customers: { ordering_customers: number; returning_customers: number };
  inventory: { out_of_stock_items_count: number };
  top_products: Array<{ product_name: string; units_sold: string; total_revenue: string }>;
};

export type ShopPayload = Partial<Omit<Shop, "id" | "status" | "public_slug" | "public_url" | "contact_number">> & {
  name: string;
  address_line: string;
  area: string;
  city: string;
  state: string;
  pincode: string;
};

export const merchantApi = {
  login: async (mobile_number: string, password: string) =>
    (await merchantClient.post("/auth/login/", { mobile_number, password })).data as {
      access: string;
      refresh: string;
      user: { id: number; role: string; shop_id: number | null };
      must_change_password: boolean;
    },
  changePassword: async (current_password: string, new_password: string) =>
    merchantClient.post("/auth/change-password/", { current_password, new_password }),
  requestPasswordRecovery: async (mobile_number: string) =>
    (await merchantClient.post("/auth/merchant-password-recovery/", { mobile_number })).data as { detail: string },
  confirmPasswordRecovery: async (payload: { mobile_number: string; otp: string; new_password: string }) =>
    merchantClient.post("/auth/merchant-password-recovery/confirm/", payload),
  logout: async () => {
    const refresh = sessionStorage.getItem("merchant_refresh_token");
    if (refresh) await merchantClient.post("/auth/logout/", { refresh });
  },
  shop: async () => (await merchantClient.get<Shop>("/shops/me/")).data,
  createShop: async (payload: ShopPayload) => (await merchantClient.post<Shop>("/shops/", payload)).data,
  updateShop: async (payload: Partial<ShopPayload>) => (await merchantClient.patch<Shop>("/shops/me/", payload)).data,
  orders: async () => (await merchantClient.get<MerchantOrder[]>("/orders/")).data,
  order: async (id: number) => (await merchantClient.get<MerchantOrder>(`/orders/${id}/`)).data,
  orderAction: async (id: number, action: string, payload: Record<string, unknown> = {}) =>
    (await merchantClient.post(`/orders/${id}/${action}/`, payload)).data,
  products: async () => (await merchantClient.get<Product[]>("/shops/me/products/")).data,
  createProduct: async (payload: Partial<Product> & { name: string }) =>
    (await merchantClient.post<Product>("/shops/me/products/", payload)).data,
  updateProduct: async (id: number, payload: Partial<Product>) =>
    (await merchantClient.patch<Product>(`/shops/me/products/${id}/`, payload)).data,
  deleteProduct: async (id: number) => merchantClient.delete(`/shops/me/products/${id}/`),
  categories: async () => (await merchantClient.get<Array<{ id: number; name: string }>>("/shops/me/categories/")).data,
  inventory: async () => (await merchantClient.get<InventoryItem[]>("/shops/me/inventory/")).data,
  updateStock: async (id: number, action: "set-stock" | "add-stock" | "subtract-stock", quantity: string) =>
    (await merchantClient.post(`/shops/me/inventory/${id}/${action}/`, { quantity })).data,
  customers: async () => (await merchantClient.get<Customer[]>("/shops/me/customers/")).data,
  analytics: async (period = "today") =>
    (await merchantClient.get<Overview>("/shops/me/analytics/", { params: { period } })).data,
};

export function getApiError(error: unknown) {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: Record<string, unknown> } }).response;
    const data = response?.data;
    if (data?.detail) return String(data.detail);
    if (data) {
      const first = Object.values(data)[0];
      if (Array.isArray(first) && first.length) return String(first[0]);
      if (typeof first === "string") return first;
    }
  }
  return "Something went wrong. Please try again.";
}
