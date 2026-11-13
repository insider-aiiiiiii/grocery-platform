import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000/api/v1";

export const customerClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Carts and orders are identified by a secret token as well as a numeric id: the id alone is
// guessable, so every cart/order request must prove it holds the token the server issued.
// Tokens live in localStorage next to the ids the storefront already keeps there.
const cartTokenKey = (slug: string, cartId: number | string) => `dukaan_cart_token_${slug}_${cartId}`;
const orderTokenKey = (slug: string, orderId: number | string) => `dukaan_order_token_${slug}_${orderId}`;

function readToken(key: string): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeToken(key: string, token: string | undefined | null) {
  if (!token) return;
  try {
    window.localStorage.setItem(key, token);
  } catch {
    /* storage unavailable: the cart simply cannot be resumed after a reload */
  }
}

export function getCartToken(slug: string, cartId: number | string): string | null {
  return readToken(cartTokenKey(slug, cartId));
}

export function getOrderToken(slug: string, orderId: number | string): string | null {
  return readToken(orderTokenKey(slug, orderId));
}

export function rememberOrderToken(slug: string, orderId: number | string, token: string | null | undefined) {
  writeToken(orderTokenKey(slug, orderId), token);
}

function cartHeaders(slug: string, cartId: number | string): Record<string, string> {
  const token = getCartToken(slug, cartId);
  return token ? { "X-Cart-Token": token } : {};
}

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
  google_maps_url?: string;
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
  parent?: number | null;
  parent_name?: string | null;
  is_subcategory?: boolean;
  products_count?: number;
}

export interface PublicProductVariant {
  id: number;
  name: string;
  description: string;
  image: string | null;
  effective_image?: string | null;
  price: string;
  mrp?: string | null;
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
  effective_image?: string | null;
  price: string | null;
  mrp?: string | null;
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
  access_token?: string;
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
  fulfillment_type: "HOME_DELIVERY" | "PICKUP";
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
  /** Secret order link token; only present in the response to the checkout request. */
  access_token?: string;
  status: "PENDING" | "ACCEPTED" | "PREPARING" | "READY" | "COMPLETED" | "REJECTED";
  payment_status: string;
  fulfillment_type: "HOME_DELIVERY" | "PICKUP";
  customer_name?: string;
  customer_phone?: string;
  delivery_address?: {
    address_line: string;
    area: string;
    city: string;
    state: string;
    pincode: string;
    landmark?: string;
    delivery_notes?: string;
  } | null;
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
    hinglish?: string;
    en?: string;
    hi?: string;
    customer_confirmation_url?: string;
    merchant_alert_url?: string;
  } | null;
}

function normalizeCart(raw: any): PublicCart {
  if (!raw) return raw;
  const rawItems = Array.isArray(raw.items) ? raw.items : [];
  const items: PublicCartItem[] = rawItems.map((it: any) => {
    const qty = Math.max(1, Math.round(parseFloat(String(it.quantity || "1"))));
    const unitPrice = it.unit_price ? parseFloat(String(it.unit_price)).toFixed(2) : "0.00";
    const totalPrice = it.line_total
      ? parseFloat(String(it.line_total)).toFixed(2)
      : it.total_price
      ? parseFloat(String(it.total_price)).toFixed(2)
      : (parseFloat(unitPrice) * qty).toFixed(2);

    return {
      id: it.id,
      product: {
        id: it.product?.id ?? 0,
        name: it.product?.name ?? "Item",
        brand: it.product?.brand ?? "",
        image: it.product?.image ?? null,
      },
      variant: it.variant
        ? {
            id: it.variant.id,
            name: it.variant.name,
            image: it.variant.image ?? null,
          }
        : null,
      quantity: qty,
      unit_price: unitPrice,
      total_price: totalPrice,
    };
  });

  const count =
    raw.item_count != null
      ? Number(raw.item_count)
      : raw.items_count != null
      ? Number(raw.items_count)
      : items.reduce((acc, i) => acc + i.quantity, 0);

  const total =
    raw.subtotal != null
      ? String(raw.subtotal)
      : raw.total_amount != null
      ? String(raw.total_amount)
      : items.reduce((acc, i) => acc + parseFloat(i.total_price || "0"), 0).toFixed(2);

  return {
    ...raw,
    items,
    item_count: count,
    items_count: count,
    subtotal: total,
    total_amount: total,
  };
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
    writeToken(cartTokenKey(publicSlug, res.data.id), res.data.access_token);
    return normalizeCart(res.data);
  },

  getCart: async (publicSlug: string, cartId: number): Promise<PublicCart> => {
    const res = await customerClient.get<PublicCart>(`/shops/public/${publicSlug}/cart/`, {
      params: { cart_id: cartId },
      headers: cartHeaders(publicSlug, cartId),
    });
    return normalizeCart(res.data);
  },

  addItemToCart: async (
    publicSlug: string,
    cartId: number,
    payload: { product_id: number; variant_id?: number; quantity: number }
  ): Promise<PublicCart> => {
    await customerClient.post(`/shops/public/${publicSlug}/cart/${cartId}/items/`, payload, {
      headers: cartHeaders(publicSlug, cartId),
    });
    return customerApi.getCart(publicSlug, cartId);
  },

  updateCartItem: async (
    publicSlug: string,
    cartId: number,
    itemId: number,
    quantity: number
  ): Promise<PublicCart> => {
    await customerClient.patch(
      `/shops/public/${publicSlug}/cart/${cartId}/items/${itemId}/`,
      { quantity },
      { headers: cartHeaders(publicSlug, cartId) }
    );
    return customerApi.getCart(publicSlug, cartId);
  },

  removeCartItem: async (publicSlug: string, cartId: number, itemId: number): Promise<PublicCart> => {
    await customerClient.delete(`/shops/public/${publicSlug}/cart/${cartId}/items/${itemId}/`, {
      headers: cartHeaders(publicSlug, cartId),
    });
    return customerApi.getCart(publicSlug, cartId);
  },

  validateCart: async (publicSlug: string, cartId: number): Promise<{ is_valid: boolean; errors?: any[] }> => {
    const res = await customerClient.post(`/shops/public/${publicSlug}/cart/${cartId}/validate/`, {}, {
      headers: cartHeaders(publicSlug, cartId),
    });
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
  checkout: async (
    publicSlug: string,
    payload: CheckoutPayload,
    // Callers pass a stable key per checkout attempt so a retry or double submit
    // replays the original order instead of failing with "empty cart".
    idempotencyKey: string = `chk_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
  ): Promise<CheckoutResponse> => {
    const res = await customerClient.post<CheckoutResponse>(
      `/shops/public/${publicSlug}/orders/`,
      payload,
      {
        headers: {
          "Idempotency-Key": idempotencyKey,
          ...cartHeaders(publicSlug, payload.cart_id),
        },
      }
    );
    rememberOrderToken(publicSlug, res.data.id, res.data.access_token);
    return res.data;
  },

  getOrder: async (publicSlug: string, orderId: number, token?: string | null): Promise<CheckoutResponse> => {
    const orderToken = token || getOrderToken(publicSlug, orderId);
    const res = await customerClient.get<CheckoutResponse>(
      `/shops/public/${publicSlug}/orders/${orderId}/`,
      { headers: orderToken ? { "X-Order-Token": orderToken } : {} }
    );
    return res.data;
  },

  // Order Cancellation
  cancelOrder: async (
    publicSlug: string,
    orderId: number,
    token?: string | null
  ): Promise<{ id: number; status: string }> => {
    const orderToken = token || getOrderToken(publicSlug, orderId);
    const res = await customerClient.post(
      `/shops/public/${publicSlug}/orders/${orderId}/cancel/`,
      {},
      { headers: orderToken ? { "X-Order-Token": orderToken } : {} }
    );
    return res.data;
  },
};

