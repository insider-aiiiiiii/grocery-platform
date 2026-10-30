"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ShoppingBag,
  Bike,
  Store,
  Plus,
  Minus,
  Trash2,
  CheckCircle2,
  MapPin,
  Lock,
  MessageCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import {
  customerApi,
  PublicShopInfo,
  PublicCart,
  RecognizeCustomerResponse,
  CheckoutPayload,
} from "@/lib/api/customer";

export default function CustomerCartCheckoutPage() {
  const params = useParams();
  const router = useRouter();
  const publicSlug = Array.isArray(params?.publicSlug)
    ? params.publicSlug[0]
    : (params?.publicSlug as string);

  const cartStorageKey = `dukaan_cart_${publicSlug}`;

  const [shop, setShop] = useState<PublicShopInfo | null>(null);
  const [cart, setCart] = useState<PublicCart | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fulfillment Selection
  const [fulfillmentType, setFulfillmentType] = useState<"HOME_DELIVERY" | "STORE_PICKUP">("HOME_DELIVERY");

  // Customer Form Details
  const [mobileNumber, setMobileNumber] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [isRecognized, setIsRecognized] = useState(false);

  // Address Details (for Home Delivery)
  const [addressLine, setAddressLine] = useState("");
  const [area, setArea] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [pincode, setPincode] = useState("");
  const [landmark, setLandmark] = useState("");
  const [deliveryNotes, setDeliveryNotes] = useState("");

  // Load Shop & Cart
  useEffect(() => {
    if (!publicSlug) return;

    async function loadCartData() {
      setLoading(true);
      setError(null);
      try {
        const shopData = await customerApi.getShop(publicSlug);
        setShop(shopData);
        setCity(shopData.city || "");
        setState(shopData.state || "");

        // Determine default fulfillment
        if (!shopData.is_home_delivery_enabled && shopData.is_pickup_enabled) {
          setFulfillmentType("STORE_PICKUP");
        }

        const savedCartId = localStorage.getItem(cartStorageKey);
        if (savedCartId) {
          const cartData = await customerApi.getCart(publicSlug, parseInt(savedCartId, 10));
          setCart(cartData);
        }
      } catch (err: any) {
        setError("Could not load basket details.");
      } finally {
        setLoading(false);
      }
    }

    loadCartData();
  }, [publicSlug]);

  // Real-time Customer Recognition on Mobile Number input
  useEffect(() => {
    const cleanedNumber = mobileNumber.replace(/\D/g, "");
    if (cleanedNumber.length === 10) {
      customerApi.recognizeCustomer(publicSlug, `+91${cleanedNumber}`).then((res) => {
        if (res.recognized && res.customer) {
          setIsRecognized(true);
          setCustomerName(res.customer.name || "");
          if (res.customer.address_line) setAddressLine(res.customer.address_line);
          if (res.customer.area) setArea(res.customer.area);
          if (res.customer.city) setCity(res.customer.city);
          if (res.customer.state) setState(res.customer.state);
          if (res.customer.pincode) setPincode(res.customer.pincode);
        } else {
          setIsRecognized(false);
        }
      });
    } else {
      setIsRecognized(false);
    }
  }, [mobileNumber, publicSlug]);

  // Cart item mutations
  const handleUpdateQuantity = async (itemId: number, nextQty: number) => {
    if (!cart) return;
    try {
      if (nextQty <= 0) {
        const updated = await customerApi.removeCartItem(publicSlug, cart.id, itemId);
        setCart(updated);
      } else {
        const updated = await customerApi.updateCartItem(publicSlug, cart.id, itemId, nextQty);
        setCart(updated);
      }
    } catch {
      setError("Failed to update item quantity.");
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!cart) return;
    try {
      const updated = await customerApi.removeCartItem(publicSlug, cart.id, itemId);
      setCart(updated);
    } catch {
      setError("Failed to remove item.");
    }
  };

  // Bill Calculations
  const itemsSubtotal = parseFloat(cart?.total_amount || "0");
  const deliveryCharge =
    fulfillmentType === "HOME_DELIVERY"
      ? parseFloat(shop?.delivery_charge || "0")
      : 0;
  const grandTotal = itemsSubtotal + deliveryCharge;

  // Checkout submission
  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cart || cart.items.length === 0) return;
    setSubmitting(true);
    setError(null);

    const formattedMobile = mobileNumber.startsWith("+91")
      ? mobileNumber
      : `+91${mobileNumber.replace(/\D/g, "")}`;

    const payload: CheckoutPayload = {
      cart_id: cart.id,
      customer_name: customerName.trim(),
      whatsapp_number: formattedMobile.trim(),
      fulfillment_type: fulfillmentType,
    };

    if (fulfillmentType === "HOME_DELIVERY") {
      payload.delivery_address = {
        address_line: addressLine.trim(),
        area: area.trim(),
        city: city.trim(),
        state: state.trim(),
        pincode: pincode.trim(),
        landmark: landmark.trim() || undefined,
        delivery_notes: deliveryNotes.trim() || undefined,
      };
    }

    try {
      // 1. Validate cart first
      const val = await customerApi.validateCart(publicSlug, cart.id);
      if (!val.is_valid) {
        setError("Some items in your basket are out of stock. Please adjust quantities.");
        setSubmitting(false);
        return;
      }

      // 2. Submit order
      const orderRes = await customerApi.checkout(publicSlug, payload);

      // 3. Clear cart from localStorage
      localStorage.removeItem(cartStorageKey);

      // 4. Redirect to Order Confirmation page
      router.push(`/shop/${publicSlug}/orders/${orderRes.id}`);
    } catch (err: any) {
      const msg = err.response?.data
        ? JSON.stringify(err.response.data)
        : err.message || "Failed to place order. Please review your address and phone number.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center p-4">
        <RefreshCw className="w-8 h-8 text-[#1F5D42] animate-spin mb-3" />
        <p className="text-xs font-semibold text-slate-600">Reviewing your bag…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-28">
      {/* Top Header */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200 px-4 py-3">
        <div className="max-w-xl mx-auto flex items-center justify-between">
          <Link
            href={`/shop/${publicSlug}`}
            className="flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
            <span className="text-xs font-bold text-slate-900 truncate max-w-[200px]">
              {shop?.name || "Store"}
            </span>
          </Link>
          <span className="text-xs font-bold text-[#1F5D42]">
            {cart?.items_count || 0} {cart?.items_count === 1 ? "Item" : "Items"}
          </span>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-4 space-y-4">
        {/* Error Alert */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-start gap-2 shadow-sm">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* 1. Fulfillment Mode Selector */}
        <div className="bg-white p-1.5 rounded-2xl border border-slate-200 shadow-sm grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => setFulfillmentType("HOME_DELIVERY")}
            disabled={!shop?.is_home_delivery_enabled}
            className={`py-2 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
              fulfillmentType === "HOME_DELIVERY"
                ? "bg-[#1F5D42] text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            }`}
          >
            <Bike className="w-4 h-4" />
            <span>Home Delivery</span>
          </button>

          <button
            type="button"
            onClick={() => setFulfillmentType("STORE_PICKUP")}
            disabled={!shop?.is_pickup_enabled}
            className={`py-2 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
              fulfillmentType === "STORE_PICKUP"
                ? "bg-[#1F5D42] text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            }`}
          >
            <Store className="w-4 h-4" />
            <span>Store Pickup (Free)</span>
          </button>
        </div>

        {/* 2. Items in Basket */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Basket Items
            </h3>
            <Link
              href={`/shop/${publicSlug}`}
              className="text-xs font-bold text-[#1F5D42] hover:underline"
            >
              + Add More
            </Link>
          </div>

          {!cart?.items || cart.items.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              Your basket is empty. Browse the store to add items.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {cart.items.map((item) => (
                <div key={item.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="flex-1">
                    <h4 className="text-xs font-bold text-slate-900">{item.product.name}</h4>
                    {item.variant && (
                      <p className="text-[11px] text-slate-500">{item.variant.name}</p>
                    )}
                    <span className="text-xs font-semibold text-slate-700">
                      ₹{parseFloat(item.unit_price).toFixed(0)} × {item.quantity} = ₹
                      {parseFloat(item.total_price).toFixed(0)}
                    </span>
                  </div>

                  {/* Quantity Stepper */}
                  <div className="flex items-center bg-[#1F5D42] text-white rounded-lg px-1 py-0.5 shadow-sm">
                    <button
                      type="button"
                      onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}
                      className="p-1 hover:bg-[#164430] rounded transition-colors"
                    >
                      {item.quantity === 1 ? (
                        <Trash2 className="w-3.5 h-3.5" />
                      ) : (
                        <Minus className="w-3.5 h-3.5" />
                      )}
                    </button>
                    <span className="w-6 text-center text-xs font-bold font-mono">
                      {item.quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}
                      className="p-1 hover:bg-[#164430] rounded transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 3. Customer Contact & Recognition Form */}
        <form onSubmit={handleCheckout} className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Customer Details
              </h3>
              {isRecognized && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  Returning Customer
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  WhatsApp Number *
                </label>
                <input
                  type="tel"
                  required
                  placeholder="e.g. 9876543210"
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42] font-mono text-xs"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Your Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42] text-xs"
                />
              </div>
            </div>

            {/* Delivery Address fields (if Home Delivery selected) */}
            {fulfillmentType === "HOME_DELIVERY" && (
              <div className="pt-2 border-t border-slate-100 space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <MapPin className="w-3.5 h-3.5 text-[#1F5D42]" />
                  <span>Delivery Address</span>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-600 mb-1">
                      House / Flat / Street Address *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Flat 402, Sunshine Heights, 12th Main"
                      value={addressLine}
                      onChange={(e) => setAddressLine(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42]"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">Area / Locality *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Indiranagar"
                        value={area}
                        onChange={(e) => setArea(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42]"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">City *</label>
                      <input
                        type="text"
                        required
                        placeholder="Bengaluru"
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">State *</label>
                      <input
                        type="text"
                        required
                        placeholder="Karnataka"
                        value={state}
                        onChange={(e) => setState(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42]"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">PIN Code *</label>
                      <input
                        type="text"
                        required
                        placeholder="560038"
                        value={pincode}
                        onChange={(e) => setPincode(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42] font-mono"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-600 mb-1">
                      Landmark / Delivery Instructions (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Near Metro Pillar 140 / Leave with security"
                      value={landmark}
                      onChange={(e) => setLandmark(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-[#1F5D42]"
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center gap-1.5 text-[11px] text-slate-500 pt-1">
              <Lock className="w-3.5 h-3.5 text-emerald-600" />
              <span>Direct WhatsApp updates from shopkeeper. No promotional spam.</span>
            </div>
          </div>

          {/* 4. Bill Details Breakdown Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-2 text-xs">
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] pb-1 border-b border-slate-100">
              Bill Summary
            </h3>

            <div className="flex items-center justify-between text-slate-600">
              <span>Items Total</span>
              <span className="font-semibold text-slate-900 font-mono">
                ₹{itemsSubtotal.toFixed(0)}
              </span>
            </div>

            <div className="flex items-center justify-between text-slate-600">
              <span>Delivery Charge</span>
              <span className="font-semibold font-mono">
                {fulfillmentType === "STORE_PICKUP" || deliveryCharge === 0 ? (
                  <span className="text-emerald-700">FREE</span>
                ) : (
                  `₹${deliveryCharge.toFixed(0)}`
                )}
              </span>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-sm font-bold text-slate-900">
              <span>To Pay (Cash / UPI on Delivery)</span>
              <span className="text-base text-[#1F5D42] font-mono">
                ₹{grandTotal.toFixed(0)}
              </span>
            </div>
          </div>

          {/* 5. Sticky Bottom Action CTA */}
          <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-slate-200 p-4 shadow-2xl">
            <div className="max-w-xl mx-auto flex items-center justify-between gap-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 block">
                  Grand Total
                </span>
                <span className="text-lg font-bold text-slate-900 font-mono">
                  ₹{grandTotal.toFixed(0)}
                </span>
              </div>

              <button
                type="submit"
                disabled={submitting || !cart || cart.items.length === 0}
                className="flex-1 py-3 px-5 bg-[#1F5D42] hover:bg-[#164430] text-white font-bold text-xs rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 active:scale-[0.98]"
              >
                {submitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Placing Order…</span>
                  </>
                ) : (
                  <>
                    <MessageCircle className="w-4 h-4" />
                    <span>Place Order & Confirm on WhatsApp</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
