"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  Clock,
  MessageCircle,
  Copy,
  Check,
  Store,
  Bike,
  ArrowLeft,
  XCircle,
  RefreshCw,
  ExternalLink,
  ShoppingBag,
  MapPin,
  Phone,
  User,
  ShieldCheck,
} from "lucide-react";
import { customerApi, PublicShopInfo } from "@/lib/api/customer";

export default function OrderConfirmationPage() {
  const params = useParams();
  const publicSlug = Array.isArray(params?.publicSlug)
    ? params.publicSlug[0]
    : (params?.publicSlug as string);
  const orderId = Array.isArray(params?.orderId)
    ? params.orderId[0]
    : (params?.orderId as string);

  const [shop, setShop] = useState<PublicShopInfo | null>(null);
  const [orderData, setOrderData] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  // 5-minute countdown timer state (300 seconds)
  const [secondsLeft, setSecondsLeft] = useState(300);

  useEffect(() => {
    if (typeof window !== "undefined" && orderId) {
      const raw = sessionStorage.getItem(`order_confirmation_${orderId}`);
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          setOrderData(parsed);
          if (parsed.status === "REJECTED") {
            setCancelled(true);
          }
        } catch {
          // ignore
        }
      }
      // Fetch fresh order details from public API
      if (publicSlug) {
        customerApi
          .getOrder(publicSlug, parseInt(orderId, 10))
          .then((data) => {
            setOrderData(data);
            if (data.status === "REJECTED") {
              setCancelled(true);
            }
            try {
              sessionStorage.setItem(`order_confirmation_${orderId}`, JSON.stringify(data));
            } catch {}
          })
          .catch(console.error);
      }
    }
  }, [orderId, publicSlug]);

  useEffect(() => {
    if (!publicSlug) return;
    customerApi.getShop(publicSlug).then(setShop).catch(console.error);
  }, [publicSlug]);

  useEffect(() => {
    if (orderData?.status === "REJECTED") {
      setCancelled(true);
    }
  }, [orderData?.status]);

  useEffect(() => {
    if (secondsLeft <= 0 || cancelled) return;
    const interval = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [secondsLeft, cancelled]);

  const handleCopyOrderId = () => {
    navigator.clipboard.writeText(`#SK-${orderId}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCancelOrder = async () => {
    if (!orderId || !publicSlug) return;
    setCancelling(true);
    setCancelError(null);
    try {
      const res = await customerApi.cancelOrder(publicSlug, parseInt(orderId, 10));
      setCancelled(true);
      const updated = { ...(orderData || {}), ...res, status: "REJECTED" };
      setOrderData(updated);
      try {
        sessionStorage.setItem(`order_confirmation_${orderId}`, JSON.stringify(updated));
      } catch {}
    } catch (err: any) {
      setCancelError(
        err.response?.data?.detail || "Order could not be cancelled. It may have already been accepted by the shopkeeper."
      );
    } finally {
      setCancelling(false);
    }
  };

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const timeFormatted = `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;

  const cleanShopPhone = (orderData?.shop_contact_number || shop?.contact_number)?.replace(/\D/g, "") || "";
  const phoneWithCountry = cleanShopPhone.length === 10 ? `91${cleanShopPhone}` : cleanShopPhone;

  // Server-generated canonical Click-to-Chat notification link if available
  const serverWaLink = orderData?.whatsapp_notification_links?.hinglish || orderData?.whatsapp_notification_links?.en;

  const shopDisplayName = orderData?.shop_name || shop?.name || "Dukandaar";
  const customerName = orderData?.customer_name || "Customer";
  const customerPhone = orderData?.customer_phone || "";
  const fulfillmentType = orderData?.fulfillment_type || "HOME_DELIVERY";
  const fulfillmentStr = fulfillmentType === "PICKUP" ? "Store Pickup (दुकान से पिकअप)" : "Home Delivery (घर पर डिलीवरी)";
  const addr = orderData?.delivery_address;
  const addrText = addr ? [addr.address_line, addr.area, addr.city, addr.pincode].filter(Boolean).join(", ") : "";

  const itemsLines = (orderData?.items || []).map(
    (item: any) => `• ${item.product_name}${item.variant_name ? ` (${item.variant_name})` : ""} × ${parseFloat(item.quantity || "1")} = ₹${parseFloat(item.line_total || "0").toFixed(0)}`
  );
  const itemsText = itemsLines.length > 0 ? itemsLines.join("\n") : "• Items from store";

  const messageLines = [
    `🛍️ *Order #SK-${orderId}*`,
    `Dukaan: *${shopDisplayName}*`,
    ``,
    `👤 Customer: ${customerName}${customerPhone ? ` (${customerPhone})` : ""}`,
    `🚚 Fulfillment: ${fulfillmentStr}${addrText ? `\n📍 Address: ${addrText}` : ""}`,
    ``,
    `📦 *Items Ordered:*`,
    itemsText,
    ``,
    `💰 *Bill Details:*`,
    orderData?.items_subtotal ? `• Items Total: ₹${parseFloat(orderData.items_subtotal).toFixed(0)}` : null,
    orderData?.delivery_charge && parseFloat(orderData.delivery_charge) > 0 ? `• Delivery Fee: ₹${parseFloat(orderData.delivery_charge).toFixed(0)}` : null,
    `• *Total Payable: ₹${orderData?.total_amount ? parseFloat(orderData.total_amount).toFixed(0) : "0"}*`,
    ``,
    `Namaste ${shopDisplayName}! Maine dukaan se order place kiya hai. Please check karke confirm karein! 🙏`,
  ].filter((line) => line !== null);

  const fullMessage = messageLines.join("\n");

  const whatsappUrl = cleanShopPhone
    ? `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(fullMessage)}`
    : (serverWaLink || "");

  const currentTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="min-h-screen bg-[#F6F0E6] text-[#17251e] font-sans pb-16">
      {/* Top Navigation Bar */}
      <header className="bg-white/90 backdrop-blur border-b border-[#ddd6ca] px-4 py-3 sticky top-0 z-30">
        <div className="max-w-xl mx-auto flex items-center justify-between">
          <Link
            href={`/shop/${publicSlug}`}
            className="flex items-center gap-2 text-[#17251e] hover:text-[#1F5D42] transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-[#1F5D42]" />
            <span className="text-xs font-bold font-display tracking-tight text-[#1F5D42]">{shop?.name || "Shop"}</span>
          </Link>
          <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-[#1F5D42] bg-[#e7f2eb] px-2.5 py-0.5 rounded-full border border-[#cde0d5]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1F5D42] animate-ping" />
            Live Storefront Order
          </span>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-4">
        {/* 1. Order Status Header Card */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-3xl p-6 text-center space-y-3 shadow-md relative overflow-hidden">
          <div className="text-4xl animate-bounce select-none">
            {cancelled ? "🛑" : "🎉"}
          </div>

          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold tracking-wide uppercase mb-2 bg-[#e7f2eb] text-[#1F5D42] border border-[#cde0d5]">
              {cancelled ? (
                <span className="text-red-700 bg-red-100 px-2 py-0.5 rounded-full">Order Cancelled / रद्द किया गया</span>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#1F5D42]" />
                  <span>Order Placed Successfully · ऑर्डर दर्ज हुआ</span>
                </>
              )}
            </div>

            <h1 className="font-display font-bold text-2xl sm:text-3xl text-[#123324] leading-tight">
              {cancelled ? "Order has been cancelled" : "Your order is confirmed!"}
            </h1>
            <p className="text-xs text-[#5e665f] mt-1 max-w-sm mx-auto leading-relaxed">
              {cancelled ? (
                "This order was cancelled by customer request. Reserved items have been returned to the store shelf."
              ) : (
                <>
                  <strong className="text-[#123324] font-semibold">{shop?.name || "Shop"}</strong> has received your order{" "}
                  <b className="text-[#1F5D42]">#SK-{orderId}</b>.
                </>
              )}
            </p>
          </div>

          {/* Copyable Order ID Pill */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F6F0E6] border border-[#ddd6ca] font-mono text-xs font-bold text-[#123324]">
            <span>#SK-{orderId}</span>
            <button
              onClick={handleCopyOrderId}
              className="text-[#6d756f] hover:text-[#123324] transition-colors cursor-pointer"
              title="Copy Order ID"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#1F5D42]" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* 2. Prominent WhatsApp Action Card */}
        {!cancelled && (
          <div className="bg-[#FFFDF8] border-2 border-[#25D366]/40 rounded-3xl p-5 shadow-lg space-y-4 relative overflow-hidden">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-2xl bg-[#25D366]/15 flex items-center justify-center shrink-0 text-[#128C7E]">
                <MessageCircle className="w-6 h-6 fill-[#25D366] text-[#25D366]" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-display font-bold text-sm text-[#123324]">
                    Send Details to Merchant via WhatsApp
                  </h3>
                  <span className="text-[9px] font-bold bg-[#25D366] text-white px-2 py-0.5 rounded-full">
                    Recommended
                  </span>
                </div>
                <p className="text-xs text-[#5e665f] mt-0.5 leading-snug">
                  व्यापारी <b>{shopDisplayName}</b> को तुरंत व्हाट्सएप पर ऑर्डर भेजें ताकि वो सामान पैक करके जल्दी भेज सकें।
                </p>
              </div>
            </div>

            {whatsappUrl ? (
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-4 px-5 bg-gradient-to-r from-[#25D366] via-[#1eb858] to-[#128C7E] hover:brightness-105 active:scale-[0.99] text-white font-body font-bold text-sm sm:text-base rounded-2xl shadow-[0_8px_20px_rgba(37,211,102,0.35)] transition flex items-center justify-center gap-2.5 cursor-pointer"
              >
                <MessageCircle className="w-5 h-5 fill-white" />
                <span>Send Order on WhatsApp · व्हाट्सएप पर भेजें</span>
                <ExternalLink className="w-4 h-4 opacity-90" />
              </a>
            ) : (
              <p className="text-xs text-amber-700 bg-amber-50 p-3 rounded-xl border border-amber-200">
                Shopkeeper contact number is not available for WhatsApp. The order is recorded in their live dashboard.
              </p>
            )}

            {/* Embedded WhatsApp Chat Preview */}
            <div className="rounded-2xl overflow-hidden border border-[#cfc8bc] shadow-sm bg-[#efeae2]">
              <div className="bg-[#075E54] text-white px-3.5 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-[#d7c49d] text-[#123324] font-bold text-[10px] flex items-center justify-center">
                    🛍️
                  </div>
                  <div>
                    <h4 className="text-[11px] font-bold leading-tight">{shopDisplayName}</h4>
                    <p className="text-[8px] text-white/80">pre-filled message preview</p>
                  </div>
                </div>
                <span className="text-[9px] font-semibold bg-white/20 px-2 py-0.5 rounded text-white/90">
                  Ready to send
                </span>
              </div>

              <div
                className="p-3"
                style={{
                  backgroundColor: "#efeae2",
                  backgroundImage:
                    "radial-gradient(#ddd5c9 1px, transparent 1px), radial-gradient(#ddd5c9 1px, transparent 1px)",
                  backgroundPosition: "0 0, 8px 8px",
                  backgroundSize: "16px 16px",
                }}
              >
                <div className="max-w-[96%] ml-auto bg-[#dcf8c6] rounded-xl rounded-tr-xs p-3 text-[11px] text-[#17251e] shadow-xs border border-[#cbe4b7] space-y-1">
                  <p className="leading-relaxed font-body whitespace-pre-line text-[#17251e]">
                    {fullMessage}
                  </p>
                  <div className="text-right text-[8px] text-[#6f7b72] flex items-center justify-end gap-1 pt-0.5">
                    <span>{currentTime}</span>
                    <span className="text-[#38a8d1] font-bold">✓✓</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. Order Items Summary Breakdown */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#eee8dc]">
            <h3 className="font-display font-bold text-xs uppercase tracking-wider text-[#123324] flex items-center gap-1.5">
              <ShoppingBag className="w-4 h-4 text-[#1F5D42]" />
              <span>Items Breakdown ({orderData?.items?.length || 0} items)</span>
            </h3>
            <span className="text-xs font-bold text-[#1F5D42]">
              ₹{orderData?.total_amount ? parseFloat(orderData.total_amount).toFixed(0) : "0"}
            </span>
          </div>

          <div className="divide-y divide-[#eee8dc]">
            {(orderData?.items || []).map((item: any, idx: number) => (
              <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                <div>
                  <p className="font-medium text-[#123324]">
                    {item.product_name}
                    {item.variant_name && (
                      <span className="text-[#6d756f] ml-1">({item.variant_name})</span>
                    )}
                  </p>
                  <p className="text-[11px] text-[#6d756f]">
                    ₹{parseFloat(item.unit_price || "0").toFixed(0)} × {parseFloat(item.quantity || "1")}
                  </p>
                </div>
                <span className="font-bold text-[#123324]">
                  ₹{parseFloat(item.line_total || "0").toFixed(0)}
                </span>
              </div>
            ))}
          </div>

          {/* Pricing Totals */}
          <div className="pt-2 border-t border-[#eee8dc] space-y-1.5 text-xs text-[#5e665f]">
            <div className="flex justify-between">
              <span>Items Subtotal</span>
              <span>₹{orderData?.items_subtotal ? parseFloat(orderData.items_subtotal).toFixed(0) : "0"}</span>
            </div>
            {orderData?.delivery_charge && parseFloat(orderData.delivery_charge) > 0 && (
              <div className="flex justify-between">
                <span>Delivery Charge</span>
                <span>₹{parseFloat(orderData.delivery_charge).toFixed(0)}</span>
              </div>
            )}
            <div className="flex justify-between pt-1 border-t border-[#eee8dc] text-sm font-bold text-[#123324]">
              <span>Grand Total</span>
              <span className="text-[#1F5D42]">
                ₹{orderData?.total_amount ? parseFloat(orderData.total_amount).toFixed(0) : "0"}
              </span>
            </div>
          </div>
        </div>

        {/* 4. Delivery & Customer Information Card */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-5 shadow-sm space-y-3">
          <h3 className="font-display font-bold text-xs uppercase tracking-wider text-[#123324] pb-2 border-b border-[#eee8dc]">
            Fulfillment & Customer Details
          </h3>
          <div className="space-y-2 text-xs">
            <div className="flex items-start gap-2 text-[#17251e]">
              <User className="w-4 h-4 text-[#1F5D42] shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">{customerName}</p>
                <p className="text-[11px] text-[#6d756f]">{customerPhone}</p>
              </div>
            </div>

            <div className="flex items-start gap-2 text-[#17251e] pt-1">
              {fulfillmentType === "PICKUP" ? (
                <Store className="w-4 h-4 text-[#1F5D42] shrink-0 mt-0.5" />
              ) : (
                <MapPin className="w-4 h-4 text-[#1F5D42] shrink-0 mt-0.5" />
              )}
              <div>
                <p className="font-semibold">{fulfillmentStr}</p>
                {addrText && <p className="text-[11px] text-[#6d756f]">{addrText}</p>}
              </div>
            </div>
          </div>
        </div>

        {/* 5. 4-Stage Live Order Status Timeline */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="font-display font-bold text-xs uppercase tracking-wider text-[#123324] pb-2 border-b border-[#eee8dc]">
            Live Order Progress
          </h3>

          <div className="space-y-4 relative pl-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#ddd6ca]">
            {/* Step 1: Placed */}
            <div className="relative">
              <span className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full ${cancelled ? "bg-red-500" : "bg-[#1F5D42]"} text-white flex items-center justify-center ring-4 ring-[#FFFDF8]`}>
                {cancelled ? <XCircle className="w-3 h-3" /> : <Check className="w-3 h-3" />}
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#123324]">Order Placed</h4>
                <p className="text-[11px] text-[#6d756f]">Received in shopkeeper's order desk.</p>
              </div>
            </div>

            {/* Step 2: Accepted */}
            <div className={`relative ${cancelled ? "opacity-40" : ""}`}>
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#E8A33D] text-white flex items-center justify-center ring-4 ring-[#FFFDF8] animate-pulse">
                <Store className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#123324]">Awaiting Dukandaar Confirmation</h4>
                <p className="text-[11px] text-[#6d756f]">Shopkeeper verifies live stock on shelves.</p>
              </div>
            </div>

            {/* Step 3: Packing */}
            <div className="relative opacity-50">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#ddd6ca] text-white flex items-center justify-center ring-4 ring-[#FFFDF8]">
                <Clock className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#6d756f]">Packing Items</h4>
                <p className="text-[11px] text-[#8e9690]">Fresh products packed for you.</p>
              </div>
            </div>

            {/* Step 4: Out for Delivery */}
            <div className="relative opacity-50">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#ddd6ca] text-white flex items-center justify-center ring-4 ring-[#FFFDF8]">
                <Bike className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#6d756f]">Out for Delivery / Ready for Pickup</h4>
                <p className="text-[11px] text-[#8e9690]">Dispatched to your doorstep.</p>
              </div>
            </div>
          </div>
        </div>

        {/* 6. Order Cancellation Action (Valid for 5 mins while pending) */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-4 shadow-sm space-y-3">
          {cancelled ? (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>Order has been successfully cancelled. Reserved items were released back to the store shelf.</span>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-[#123324]">Need to cancel?</h4>
                  <p className="text-[11px] text-[#6d756f]">
                    You can cancel your order within {timeFormatted} minutes before packing begins.
                  </p>
                </div>
              </div>

              {cancelError && (
                <div className="mt-2 p-2 bg-red-50 text-red-700 text-xs rounded-lg">
                  {cancelError}
                </div>
              )}

              {secondsLeft > 0 && (
                <button
                  type="button"
                  onClick={handleCancelOrder}
                  disabled={cancelling}
                  className="mt-3 w-full py-2.5 border border-red-200 text-red-600 hover:bg-red-50 text-xs font-semibold rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  {cancelling ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Cancelling order…</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Cancel Order ({timeFormatted} remaining)</span>
                    </>
                  )}
                </button>
              )}
            </div>
          )}
        </div>

        {/* 7. Return to Shop CTA */}
        <div className="text-center pt-2">
          <Link
            href={`/shop/${publicSlug}`}
            className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-xl bg-[#123324] hover:bg-[#1F5D42] text-white text-xs font-bold font-display shadow-sm transition-all"
          >
            <span>Done · Return to {shop?.name || "Shop"}</span>
          </Link>
        </div>
      </main>
    </div>
  );
}

