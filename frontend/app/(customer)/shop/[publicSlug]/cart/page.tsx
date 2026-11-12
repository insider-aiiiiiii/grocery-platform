"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Plus,
  Minus,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ShoppingBag,
  MessageCircle,
} from "lucide-react";
import { formatPrice } from "@/lib/format";
import {
  customerApi,
  PublicShopInfo,
  PublicCart,
  CheckoutPayload,
  CheckoutResponse,
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

  // Fulfillment Selection (Delivery vs Pickup toggle matching visual board)
  const [fulfillmentType, setFulfillmentType] = useState<"HOME_DELIVERY" | "PICKUP">("HOME_DELIVERY");

  // 3 Fields Only
  const [customerName, setCustomerName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [addressLine, setAddressLine] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);

  // Load Shop & Cart Data
  useEffect(() => {
    if (!publicSlug) return;

    async function loadCartData() {
      setLoading(true);
      setError(null);
      try {
        const shopData = await customerApi.getShop(publicSlug);
        setShop(shopData);

        if (!shopData.is_home_delivery_enabled && shopData.is_pickup_enabled) {
          setFulfillmentType("PICKUP");
        }

        const savedCartId = localStorage.getItem(cartStorageKey);
        if (savedCartId) {
          const cartData = await customerApi.getCart(publicSlug, parseInt(savedCartId, 10));
          setCart(cartData);
        }
      } catch (err: any) {
        setError("Could not load your cart details.");
      } finally {
        setLoading(false);
      }
    }

    loadCartData();
  }, [publicSlug]);

  // Real-time Customer Recognition
  useEffect(() => {
    const cleanedNumber = mobileNumber.replace(/\D/g, "");
    if (cleanedNumber.length === 10) {
      customerApi.recognizeCustomer(publicSlug, `+91${cleanedNumber}`).then((res) => {
        if (res.recognized && res.customer) {
          if (!customerName) setCustomerName(res.customer.name || "");
          if (res.customer.address_line && !addressLine) {
            setAddressLine(
              [res.customer.address_line, res.customer.area, res.customer.city]
                .filter(Boolean)
                .join(", ")
            );
          }
        }
      }).catch(() => {});
    }
  }, [mobileNumber, publicSlug, customerName, addressLine]);

  // Cart item mutations
  const handleUpdateQuantity = async (itemId: number, nextQty: number) => {
    if (!cart) return;
    const cleanQty = Math.max(0, Math.round(Number(nextQty)));
    try {
      if (cleanQty <= 0) {
        const updated = await customerApi.removeCartItem(publicSlug, cart.id, itemId);
        setCart(updated);
      } else {
        const updated = await customerApi.updateCartItem(publicSlug, cart.id, itemId, cleanQty);
        setCart(updated);
      }
    } catch {
      setError("Failed to update item quantity.");
    }
  };

  // Bill Calculations
  const itemsSubtotal = parseFloat(cart?.total_amount || "0");
  const deliveryCharge =
    fulfillmentType === "HOME_DELIVERY"
      ? parseFloat(shop?.delivery_charge || "0")
      : 0;
  const grandTotal = itemsSubtotal + deliveryCharge;

  // Checkout submission with dual-action: creates merchant order + opens WhatsApp pre-filled draft
  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cart || cart.items.length === 0) return;
    if (!customerName.trim()) {
      setError("Please enter your name / कृपया अपना नाम दर्ज करें।");
      return;
    }
    const cleanDigits = mobileNumber.replace(/\D/g, "").slice(-10);
    if (cleanDigits.length !== 10) {
      setError("Please enter a valid 10-digit WhatsApp number / कृपया 10 अंकों का मोबाइल नंबर दर्ज करें।");
      return;
    }
    if (fulfillmentType === "HOME_DELIVERY" && !addressLine.trim()) {
      setError("Please enter your delivery address / डिलीवरी का पता दर्ज करें।");
      return;
    }
    if (!consentChecked) {
      setError("Please accept the agreement to proceed / कृपया आगे बढ़ने के लिए सहमति दें।");
      return;
    }

    setSubmitting(true);
    setError(null);

    const formattedMobile = `+91${cleanDigits}`;
    const payload: CheckoutPayload = {
      cart_id: cart.id,
      customer_name: customerName.trim(),
      whatsapp_number: formattedMobile,
      fulfillment_type: fulfillmentType,
    };

    if (fulfillmentType === "HOME_DELIVERY") {
      payload.delivery_address = {
        address_line: addressLine.trim(),
        area: shop?.area || "Local Area",
        city: shop?.city || "City",
        state: shop?.state || "State",
        pincode: shop?.pincode || "000000",
      };
    }

    try {
      // 1. Submit order to backend
      const orderRes = await customerApi.checkout(publicSlug, payload);

      // 2. Clear cart from localStorage
      localStorage.removeItem(cartStorageKey);

      // 3. Store order confirmation in sessionStorage
      if (typeof window !== "undefined" && orderRes?.id) {
        sessionStorage.setItem(`order_confirmation_${orderRes.id}`, JSON.stringify(orderRes));
      }

      // 4. Navigate directly to order confirmation page
      if (orderRes?.id) {
        router.push(`/shop/${publicSlug}/orders/${orderRes.id}`);
      } else {
        router.push(`/shop/${publicSlug}`);
      }
    } catch (err: any) {
      console.error("Order checkout error:", err);
      const errorMsg =
        err.response?.data?.detail ||
        err.response?.data?.items?.[0] ||
        err.message ||
        "Failed to place order. Please check your items and try again.";
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };


  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7f4ee] flex flex-col items-center justify-center p-4">
        <RefreshCw className="w-8 h-8 text-[#1F5D42] animate-spin mb-3" />
        <p className="text-xs font-semibold text-[#5e665f]">Opening your basket…</p>
      </div>
    );
  }

  const itemsCount = cart?.items.reduce((acc, i) => acc + i.quantity, 0) || 0;

  return (
    <div className="min-h-screen bg-[#f7f4ee] text-[#17251e] font-body pb-28">
      {/* Top Header */}
      <header className="bg-white border-b border-[#e2ddd4] sticky top-0 z-30 px-4 py-3.5">
        <div className="max-w-xl mx-auto flex items-center justify-between">
          <Link
            href={`/shop/${publicSlug}`}
            className="flex items-center gap-1.5 text-xs font-bold text-[#1F5D42] hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to shop</span>
          </Link>
          <span className="font-display font-bold text-xl text-[#123324]">Checkout</span>
          <span className="w-12 text-right text-xs font-semibold text-[#6d756f]">
            {itemsCount} {itemsCount === 1 ? "item" : "items"}
          </span>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-5 space-y-4">
        {/* Error Notification */}
        {error && (
          <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2 shadow-sm">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* 1. "Your Order" Card (Matching Visual Board Frame 4) */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-[#e2ddd4] shadow-sm space-y-3">
          <h2 className="font-display font-bold text-lg text-[#123324]">Your Order</h2>

          {(!cart?.items || cart.items.length === 0) ? (
            <div className="py-8 text-center space-y-2">
              <ShoppingBag className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs text-[#6d756f]">Your basket is empty.</p>
              <Link
                href={`/shop/${publicSlug}`}
                className="inline-block px-4 py-2 bg-[#1F5D42] text-white text-xs font-bold rounded-xl mt-2"
              >
                Browse Shop
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-[#eee9df]">
              {cart.items.map((item) => {
                const unitPrice = parseFloat(item.unit_price || "0");
                const itemTotal = formatPrice(unitPrice * item.quantity);
                return (
                  <div key={item.id} className="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-body font-semibold text-xs sm:text-sm text-[#17251e] leading-snug truncate">
                        {item.product.name}
                      </p>
                      <p className="text-[11px] text-[#7e857f] mt-0.5">
                        {item.quantity} × ₹{formatPrice(unitPrice)}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {/* Stepper */}
                      <div className="flex items-center border border-[#d9d2c6] rounded-lg overflow-hidden bg-[#faf8f3]">
                        <button
                          type="button"
                          onClick={() => handleUpdateQuantity(item.id, Math.round(Number(item.quantity) || 1) - 1)}
                          className="px-2.5 py-1 text-xs font-bold text-[#17251e] hover:bg-[#eee9df] transition-colors cursor-pointer"
                        >
                          −
                        </button>
                        <span className="px-2 text-xs font-bold font-mono text-[#1F5D42] bg-white">
                          {Math.round(Number(item.quantity) || 1)}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleUpdateQuantity(item.id, Math.round(Number(item.quantity) || 1) + 1)}
                          className="px-2.5 py-1 text-xs font-bold text-[#17251e] hover:bg-[#eee9df] transition-colors cursor-pointer"
                        >
                          +
                        </button>
                      </div>

                      <span className="font-display font-bold text-sm text-[#17251e] w-14 text-right">
                        ₹{itemTotal}
                      </span>
                    </div>
                  </div>
                );
              })}

              {/* Total Calculation Row */}
              <div className="pt-3.5 space-y-1.5 text-xs">
                <div className="flex justify-between text-[#6d756f]">
                  <span>Items Subtotal</span>
                  <span>₹{formatPrice(itemsSubtotal)}</span>
                </div>
                {fulfillmentType === "HOME_DELIVERY" && (
                  <div className="flex justify-between text-[#6d756f]">
                    <span>Delivery Charge</span>
                    <span className={shop?.delivery_fee_type === "CONFIRMED_ON_WHATSAPP" ? "text-[#1F5D42] font-semibold" : ""}>
                      {shop?.delivery_fee_type === "CONFIRMED_ON_WHATSAPP"
                        ? "To be confirmed on WhatsApp"
                        : deliveryCharge === 0
                        ? "Free"
                        : `₹${formatPrice(deliveryCharge)}`}
                    </span>
                  </div>
                )}
                <div className="pt-2 border-t border-[#eee9df] flex justify-between items-baseline font-bold">
                  <span className="text-sm font-body text-[#17251e]">Total Bill</span>
                  <span className="font-display font-bold text-2xl text-[#1F5D42]">
                    ₹{formatPrice(grandTotal)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 2. Customer Details Form (3 Fields Only: Visual Board Frame 4) */}
        {cart && cart.items.length > 0 && (
          <form onSubmit={handleCheckout} className="bg-white rounded-2xl p-4 sm:p-5 border border-[#e2ddd4] shadow-sm space-y-4">
            <h2 className="font-display font-bold text-lg text-[#123324]">Customer Details</h2>

            {/* Pickup vs Delivery Toggle */}
            <div className="flex bg-[#eee9df] rounded-xl p-1 shadow-inner">
              <button
                type="button"
                onClick={() => setFulfillmentType("HOME_DELIVERY")}
                disabled={!shop?.is_home_delivery_enabled}
                className={`flex-1 py-2 text-center rounded-lg text-xs font-semibold transition-all ${
                  fulfillmentType === "HOME_DELIVERY"
                    ? "bg-white text-[#1F5D42] font-bold shadow-sm"
                    : "text-[#5e665f] hover:text-[#17251e]"
                } ${!shop?.is_home_delivery_enabled ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                🛵 Home Delivery
              </button>
              <button
                type="button"
                onClick={() => setFulfillmentType("PICKUP")}
                disabled={!shop?.is_pickup_enabled}
                className={`flex-1 py-2 text-center rounded-lg text-xs font-semibold transition-all ${
                  fulfillmentType === "PICKUP"
                    ? "bg-white text-[#1F5D42] font-bold shadow-sm"
                    : "text-[#5e665f] hover:text-[#17251e]"
                } ${!shop?.is_pickup_enabled ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                🏪 Store Pickup
              </button>
            </div>

            {/* Field 1: Name */}
            <div>
              <label className="block text-xs font-bold text-[#17251e] mb-1">Your Full Name</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="e.g. Priya Sharma"
                className="w-full bg-[#faf8f3] border border-[#dcd5c9] rounded-xl px-3.5 py-2.5 text-xs sm:text-sm font-body text-[#17251e] outline-none focus:border-[#1F5D42] focus:bg-white transition"
                required
              />
            </div>

            {/* Field 2: WhatsApp Number */}
            <div>
              <label className="block text-xs font-bold text-[#17251e] mb-1">
                WhatsApp Mobile Number (10 Digits) *
              </label>
              <div className="flex items-center rounded-xl border border-[#dcd5c9] bg-[#faf8f3] overflow-hidden focus-within:border-[#1F5D42] focus-within:bg-white focus-within:ring-1 focus-within:ring-[#1F5D42]">
                <span className="px-3 py-2.5 bg-[#eee9df] text-slate-700 font-mono font-bold text-xs sm:text-sm border-r border-[#dcd5c9] select-none">
                  +91
                </span>
                <input
                  type="tel"
                  required
                  maxLength={10}
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value.replace(/\D/g, "").slice(0, 10))}
                  placeholder="9876543210"
                  className="w-full bg-transparent px-3 py-2.5 text-xs sm:text-sm font-body font-mono text-[#17251e] outline-none"
                />
              </div>
              <p className="text-[10px] text-[#7e857f] mt-1">You will receive live order confirmations & receipts on this WhatsApp number.</p>
            </div>

            {/* Field 3: Delivery Address (Shown only on Delivery) */}
            {fulfillmentType === "HOME_DELIVERY" && (
              <div>
                <label className="block text-xs font-bold text-[#17251e] mb-1">Complete Delivery Address</label>
                <textarea
                  value={addressLine}
                  onChange={(e) => setAddressLine(e.target.value)}
                  placeholder="House/Flat No, Landmark, Area name"
                  rows={2}
                  className="w-full bg-[#faf8f3] border border-[#dcd5c9] rounded-xl px-3.5 py-2 text-xs sm:text-sm font-body text-[#17251e] outline-none focus:border-[#1F5D42] focus:bg-white resize-none transition"
                  required
                />
              </div>
            )}

            {/* Consent Checkbox (Matching Visual Board) */}
            <div className="flex items-start gap-2.5 pt-1">
              <input
                type="checkbox"
                id="consentCheck"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-[#cfc7bb] text-[#1F5D42] focus:ring-[#1F5D42]"
              />
              <label htmlFor="consentCheck" className="text-[11px] text-[#5e665f] leading-snug cursor-pointer select-none">
                I agree that my name and WhatsApp number may be used to fulfil this order and send order updates via WhatsApp.
              </label>
            </div>

            {/* Sticky Action Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={submitting || !consentChecked}
                className="w-full bg-gradient-to-r from-[#123324] via-[#174b36] to-[#1F5D42] hover:brightness-110 active:scale-[0.99] disabled:opacity-50 text-white font-body font-bold text-sm sm:text-base py-3.5 rounded-xl shadow-[0_10px_25px_rgba(18,51,36,0.25)] transition flex items-center justify-center gap-2 cursor-pointer"
              >
                {submitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Placing order…</span>
                  </>
                ) : (
                  <>
                    <ShoppingBag className="w-5 h-5 text-emerald-300" />
                    <span>Place Order · ₹{formatPrice(grandTotal)}</span>
                  </>
                )}
              </button>
            </div>

          </form>
        )}
      </main>
    </div>
  );
}
