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

export interface MerchantShopItem {
  id: number;
  shopId: number;
  shopName: string;
  merchantName: string;
  mobileNumber: string;
  city: string;
  status: "ACTIVE" | "PENDING_PASSWORD_CHANGE" | "SUSPENDED" | "DEACTIVATED";
  catalogItemsCount: number;
  monthlyVolume: string;
  publicSlug: string;
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

  getTopProducts: async (token?: string, period: string = "today", limit: number = 10) => {
    const res = await apiClient.get("/analytics/platform/top-products/", {
      params: { period, limit },
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

  listShops: async (token?: string): Promise<MerchantShopItem[]> => {
    const res = await apiClient.get<Array<{
      id: number;
      name: string;
      public_slug: string;
      status: "ACTIVE" | "SUSPENDED" | "DEACTIVATED";
      city: string;
      owner__username?: string;
      owner__mobile_number?: string;
      owner_username?: string;
      owner_mobile_number?: string;
      catalog_items_count?: number;
      monthly_volume?: string;
    }>>("/shops/admin/directory/", {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data.map((item) => ({
      id: item.id,
      shopId: item.id,
      shopName: item.name,
      merchantName: item.owner_username || item.owner__username || "Merchant",
      mobileNumber: item.owner_mobile_number || item.owner__mobile_number || "—",
      city: item.city || "—",
      status: item.status,
      catalogItemsCount: item.catalog_items_count ?? 0,
      monthlyVolume: item.monthly_volume || "₹0",
      publicSlug: item.public_slug,
    }));
  },

  promoteShopProduct: async (
    productId: number,
    payload?: {
      name?: string;
      brand?: string;
      description?: string;
      category?: number;
    },
    token?: string
  ) => {
    const res = await apiClient.post(`/catalog/shop-products/${productId}/promote/`, payload || {}, {
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
      params: { confirm: "true" },
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  // Campaign Management (CampaignViewSet)
  listCampaigns: async (token?: string) => {
    const res = await apiClient.get<Array<{
      id: number;
      name: string;
      banner_url: string;
      discount_percentage: string;
      status: "DRAFT" | "ACTIVE" | "ENDED";
      starts_at: string;
      ends_at: string;
      selected_shops?: number[];
    }>>("/campaigns/", {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  createCampaign: async (
    payload: {
      name: string;
      banner_url?: string;
      discount_percentage?: string;
      starts_at: string;
      ends_at?: string;
      selected_shops?: number[];
    },
    token?: string
  ) => {
    const res = await apiClient.post("/campaigns/", payload, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  activateCampaign: async (campaignId: number, token?: string) => {
    const res = await apiClient.post(`/campaigns/${campaignId}/activate/`, {}, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  endCampaign: async (campaignId: number, token?: string) => {
    const res = await apiClient.post(`/campaigns/${campaignId}/deactivate/`, {}, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  deleteCampaign: async (campaignId: number, token?: string) => {
    const res = await apiClient.delete(`/campaigns/${campaignId}/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  // Security Self-Recovery & Admin Reset
  requestSelfRecovery: async (payload: { channel: "EMAIL" | "SMS"; contact: string }) => {
    const res = await apiClient.post("/auth/super-admin/recovery/", payload);
    return res.data;
  },

  confirmSelfRecovery: async (payload: { code: string; new_password: string; contact: string }) => {
    const res = await apiClient.post("/auth/super-admin/recovery/confirm/", payload);
    return res.data;
  },

  requestAdminReset: async (
    payload: { target_user_id: number; channel: "EMAIL" | "SMS"; current_password: string },
    token?: string
  ) => {
    const res = await apiClient.post("/auth/super-admin/password-reset-requests/", payload, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return res.data;
  },

  confirmAdminReset: async (payload: { code: string; new_password: string }) => {
    const res = await apiClient.post("/auth/super-admin/password-reset-requests/confirm/", payload);
    return res.data;
  },
};

