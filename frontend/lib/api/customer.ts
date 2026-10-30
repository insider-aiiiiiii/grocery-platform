import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const customerClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface PublicShopInfo {
  public_slug: string;
  public_url: string;
  name: string;
  description: string;
  logo: string | null;
  address_line: string;
  area: string;
  city: string;
  state: string;
  pincode: string;
  contact_number: string;
  is_temporarily_closed: boolean;
  opening_time: string | null;
  closing_time: string | null;
  is_home_delivery_enabled: boolean;
  is_pickup_enabled: boolean;
  delivery_fee_type: "FIXED" | "CONFIRMED_ON_WHATSAPP";
  delivery_charge: string;
}

export interface PublicCampaign {
  id: number;
  title: string;
  content: string;
  status: "ACTIVE";
  starts_at: string | null;
  ends_at: string | null;
}

export interface PublicCategory {
  id: number;
  name: string;
  slug: string;
  description?: string;
  products_count?: number;
}

export interface PublicProductVariant {
  id: number;
  name: string;
  description: string;
  image: string | null;
  price: string;
  sku: string;
  attributes: Record<string, any>;
  available_quantity: number | null;
  is_out_of_stock: boolean;
  is_orderable: boolean;
  display_status: string;
}

export interface PublicProduct {
  id: number;
  name: string;
  description: string;
  brand: string;
  image: string | null;
  price: string | null;
  sku: string;
  attributes: Record<string, any>;
  has_variants: boolean;
  variants: PublicProductVariant[];
  categories: PublicCategory[];
  available_quantity: number | null;
  is_out_of_stock: boolean;
  is_orderable: boolean;
  display_status: string;
}

export interface PublicCartItem {
  id: number;
  product: {
    id: number;
    name: string;
    brand: string;
    image: string | null;
  };
  variant: {
    id: number;
    name: string;
    image: string | null;
  } | null;
  quantity: number;
  unit_price: string;
  total_price: string;
}

export interface PublicCart {
  id: number;
  shop: number;
  items_count: number;
  total_amount: string;
  items: PublicCartItem[];
  customer?: {
    id: number;
    name: string;
    whatsapp_number: string;
  } | null;
}

export interface RecognizeCustomerResponse {
  recognized: boolean;
  customer?: {
    id: number;
    name: string;
    whatsapp_number: string;
    address_line?: string;
    area?: string;
    city?: string;
    state?: string;
    pincode?: string;
  };
  detail?: string;
}

export interface CheckoutPayload {
  cart_id: number;
  customer_name: string;
  whatsapp_number: string;
  fulfillment_type: "HOME_DELIVERY" | "STORE_PICKUP";
  delivery_address?: {
    address_line: string;
    area: string;
    city: string;
    state: string;
    pincode: string;
    landmark?: string;
    delivery_notes?: string;
  };
}

export interface CheckoutResponse {
  id: number;
  status: "PENDING" | "ACCEPTED" | "READY" | "OUT_FOR_DELIVERY" | "COMPLETED" | "CANCELLED";
  payment_status: string;
  fulfillment_type: "HOME_DELIVERY" | "STORE_PICKUP";
  shop_name: string;
  shop_contact_number: string;
  items_subtotal: string;
  delivery_charge: string;
  total_amount: string;
  expires_at: string;
  items: Array<{
    product_name: string;
    variant_name?: string;
    sku: string;
    quantity: string;
    unit_price: string;
    line_total: string;
  }>;
  whatsapp_notification_links?: {
    customer_confirmation_url?: string;
    merchant_alert_url?: string;
  } | null;
}

export const customerApi = {
  getShop: async (publicSlug: string): Promise<PublicShopInfo> => {
    const res = await customerClient.get<PublicShopInfo>(`/shops/public/${publicSlug}/`);
    return res.data;
  },

  getCampaigns: async (publicSlug: string): Promise<PublicCampaign[]> => {
    try {
      const res = await customerClient.get<PublicCampaign[]>(`/shops/public/${publicSlug}/campaigns/`);
      return res.data;
    } catch {
      return [];
    }
  },

  getCategories: async (publicSlug: string): Promise<PublicCategory[]> => {
    const res = await customerClient.get<PublicCategory[]>(`/shops/public/${publicSlug}/categories/`);
    return res.data;
  },

  getProducts: async (
    publicSlug: string,
    params?: { search?: string; category?: number | string }
  ): Promise<PublicProduct[]> => {
    const queryParams: Record<string, any> = {};
    if (params?.search) queryParams.search = params.search;
    if (params?.category && params.category !== "all") queryParams.category = params.category;
    const res = await customerClient.get<PublicProduct[]>(`/shops/public/${publicSlug}/products/`, {
      params: queryParams,
    });
    return res.data;
  },

  getProductDetail: async (publicSlug: string, productId: number): Promise<PublicProduct> => {
    const res = await customerClient.get<PublicProduct>(`/shops/public/${publicSlug}/products/${productId}/`);
    return res.data;
  },

  // Cart Operations
  createCart: async (publicSlug: string): Promise<PublicCart> => {
    const res = await customerClient.post<PublicCart>(`/shops/public/${publicSlug}/cart/`, {});
    return res.data;
  },

  getCart: async (publicSlug: string, cartId: number): Promise<PublicCart> => {
    const res = await customerClient.get<PublicCart>(`/shops/public/${publicSlug}/cart/`, {
      params: { cart_id: cartId },
    });
    return res.data;
  },

  addItemToCart: async (
    publicSlug: string,
    cartId: number,
    payload: { product_id: number; variant_id?: number; quantity: number }
  ): Promise<PublicCart> => {
    await customerClient.post(`/shops/public/${publicSlug}/cart/${cartId}/items/`, payload);
    return customerApi.getCart(publicSlug, cartId);
  },

  updateCartItem: async (
    publicSlug: string,
    cartId: number,
    itemId: number,
    quantity: number
  ): Promise<PublicCart> => {
    await customerClient.patch(`/shops/public/${publicSlug}/cart/${cartId}/items/${itemId}/`, {
      quantity,
    });
    return customerApi.getCart(publicSlug, cartId);
  },

  removeCartItem: async (publicSlug: string, cartId: number, itemId: number): Promise<PublicCart> => {
    await customerClient.delete(`/shops/public/${publicSlug}/cart/${cartId}/items/${itemId}/`);
    return customerApi.getCart(publicSlug, cartId);
  },

  validateCart: async (publicSlug: string, cartId: number): Promise<{ is_valid: boolean; errors?: any[] }> => {
    const res = await customerClient.post(`/shops/public/${publicSlug}/cart/${cartId}/validate/`, {});
    return res.data;
  },

  // Customer Recognition
  recognizeCustomer: async (publicSlug: string, whatsappNumber: string): Promise<RecognizeCustomerResponse> => {
    try {
      const res = await customerClient.post<RecognizeCustomerResponse>(
        `/shops/public/${publicSlug}/customer/recognize/`,
        { whatsapp_number: whatsappNumber }
      );
      return res.data;
    } catch {
      return { recognized: false };
    }
  },

  // Checkout
  checkout: async (publicSlug: string, payload: CheckoutPayload): Promise<CheckoutResponse> => {
    const idempotencyKey = `chk_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const res = await customerClient.post<CheckoutResponse>(
      `/shops/public/${publicSlug}/orders/`,
      payload,
      {
        headers: {
          "Idempotency-Key": idempotencyKey,
        },
      }
    );
    return res.data;
  },

  // Order Cancellation
  cancelOrder: async (orderId: number): Promise<{ id: number; status: string }> => {
    const res = await customerClient.post(`/customer/orders/${orderId}/cancellation/`, {});
    return res.data;
  },
};
