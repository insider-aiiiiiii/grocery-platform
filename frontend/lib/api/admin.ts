import { apiClient } from "./client";

export interface SuperAdminLoginRequest {
  identifier: string;
  password: string;
}

export interface SuperAdminLoginResponse {
  access: string;
  refresh: string;
  role: "SUPER_ADMIN";
}

export interface PlatformAnalytics {
  period: string;
  start_time: string;
  end_time: string;
  filtered_shop_id: number | null;
  shops: {
    total_shops: number;
    active_shops: number;
    deactivated_shops: number;
  };
  orders: {
    total_orders: number;
    completed_orders: number;
    rejected_orders: number;
    status_distribution: {
      PENDING: number;
      ACCEPTED: number;
      PREPARING: number;
      READY: number;
      COMPLETED: number;
      REJECTED: number;
    };
  };
  sales: {
    realized_sales: string;
    average_order_value: string;
  };
  customers: {
    ordering_customers: number;
  };
  inventory: {
    out_of_stock_items_count: number;
  };
  top_products: Array<{
    product_id: number;
    variant_id: number | null;
    product_name: string;
    variant_name: string;
    sku: string;
    units_sold: string;
    total_revenue: string;
  }>;
  top_shops: Array<{
    shop_id: number;
    shop_name: string;
    completed_orders: number;
    realized_sales: string;
  }>;
}

export interface ProvisionMerchantPayload {
  username: string;
  mobile_number: string;
  email: string;
  initial_password: string;
}

export interface ProvisionMerchantResponse {
  id: number;
  username: string;
  mobile_number: string;
  email: string;
  role: "MERCHANT";
  must_change_password: boolean;
}

export interface MasterProduct {
  id: number;
  name: string;
  category: number | string;
  category_name?: string;
  brand: string;
  description: string;
  is_verified?: boolean;
}

export const adminApi = {
  login: async (payload: SuperAdminLoginRequest): Promise<SuperAdminLoginResponse> => {
    const res = await apiClient.post<SuperAdminLoginResponse>("/auth/super-admin/login/", payload);
    return res.data;
  },

  getAnalytics: async (token?: string, period: string = "today"): Promise<PlatformAnalytics> => {
    const res = await apiClient.get<PlatformAnalytics>("/analytics/platform/", {
      params: { period },
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  getTopShops: async (token?: string, period: string = "today") => {
    const res = await apiClient.get("/analytics/platform/top-shops/", {
      params: { period },
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  provisionMerchant: async (payload: ProvisionMerchantPayload, token?: string): Promise<ProvisionMerchantResponse> => {
    const res = await apiClient.post<ProvisionMerchantResponse>("/super-admin/merchants/", payload, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  listMasterProducts: async (token?: string) => {
    const res = await apiClient.get<{ results: MasterProduct[] }>("/catalog/master-products/", {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  createMasterProduct: async (payload: Omit<MasterProduct, "id">, token?: string) => {
    const res = await apiClient.post<MasterProduct>("/catalog/master-products/", payload, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  promoteShopProduct: async (productId: number, token?: string) => {
    const res = await apiClient.post(`/catalog/shop-products/${productId}/promote/`, {}, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  deactivateShop: async (shopId: number, token?: string) => {
    const res = await apiClient.post(`/shops/${shopId}/deactivate/`, {}, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  reactivateShop: async (shopId: number, token?: string) => {
    const res = await apiClient.post(`/shops/${shopId}/reactivate/`, {}, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  regenerateShopQR: async (shopId: number, token?: string) => {
    const res = await apiClient.post(`/shops/${shopId}/regenerate-qr/`, {}, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  deleteShop: async (shopId: number, token?: string) => {
    const res = await apiClient.delete(`/shops/${shopId}/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },
};
