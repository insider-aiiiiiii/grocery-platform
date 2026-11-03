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
          setOrderData(JSON.parse(raw));
          return;
        } catch {
          // ignore
        }
      }
      // If not in sessionStorage or refreshed, fetch from public API
      if (publicSlug) {
        customerApi
          .getOrder(publicSlug, parseInt(orderId, 10))
          .then((data) => {
            setOrderData(data);
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
    if (!orderId) return;
    setCancelling(true);
    setCancelError(null);
    try {
      await customerApi.cancelOrder(parseInt(orderId, 10));
      setCancelled(true);
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

  // Use server-generated canonical Click-to-Chat notification link if available
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
    `Namaste ${shopDisplayName}! Maine Dukaan se order place kiya hai. Please check karke confirm karein!`,
  ].filter((line) => line !== null);

  const fullMessage = messageLines.join("\n");

  const whatsappUrl = cleanShopPhone
    ? `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(fullMessage)}`
    : (serverWaLink || "");

  const currentTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="min-h-screen bg-[#F6F0E6] text-[#17251e] font-sans pb-16">
      {/* Top Bar */}
      <header className="bg-white/80 backdrop-blur border-b border-[#ddd6ca] px-4 py-3 sticky top-0 z-30">
        <div className="max-w-xl mx-auto flex items-center justify-between">
          <Link
            href={`/shop/${publicSlug}`}
            className="flex items-center gap-2 text-[#17251e] hover:text-[#1F5D42] transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-[#1F5D42]" />
            <span className="text-xs font-bold font-display tracking-tight text-[#1F5D42]">{shop?.name || "Shop"}</span>
          </Link>
          <span className="text-[10px] font-bold text-[#1F5D42] bg-[#e7f2eb] px-2.5 py-0.5 rounded-full border border-[#cde0d5]">
            ● Live Dukaan Order
          </span>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-4">
        {/* 1. Hero Celebration Card (Visual Board Style) */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-3xl p-6 text-center space-y-3 shadow-md relative overflow-hidden">
          <div className="text-4xl animate-bounce select-none">🎉</div>

          <div>
            <h1 className="font-display font-bold text-3xl text-[#123324] leading-tight">
              Order confirmed!
            </h1>
            <p className="text-xs text-[#5e665f] mt-1 max-w-sm mx-auto leading-relaxed">
              <strong className="text-[#123324] font-semibold">{shop?.name || "Shop"}</strong> has received order{" "}
              <b className="text-[#1F5D42]">#SK-{orderId}</b>.<br />
              You’ll get updates directly on WhatsApp.
            </p>
          </div>

          {/* Copyable Order ID Pill */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F6F0E6] border border-[#ddd6ca] font-mono text-xs font-bold text-[#123324]">
            <span>#SK-{orderId}</span>
            <button
              onClick={handleCopyOrderId}
              className="text-[#6d756f] hover:text-[#123324] transition-colors"
              title="Copy Order ID"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#1F5D42]" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* 2. Embedded WhatsApp Preview Card (Authentic Visual Board Frame) */}
        <div className="rounded-2xl overflow-hidden border border-[#cfc8bc] shadow-md bg-[#efeae2]">
          {/* WhatsApp Chrome Header */}
          <div className="bg-[#075E54] text-white px-4 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#d7c49d] text-[#123324] font-bold text-xs flex items-center justify-center shadow-sm">
                🛍️
              </div>
              <div>
                <h3 className="text-xs font-bold leading-tight">{shop?.name || "QR Local"}</h3>
                <p className="text-[9px] text-white/80">business account • verified</p>
              </div>
            </div>
            <span className="text-[10px] font-semibold bg-white/20 px-2 py-0.5 rounded text-white/90">
              WhatsApp Preview
            </span>
          </div>

          {/* Chat wallpaper & bubble */}
          <div
            className="p-4 space-y-3"
            style={{
              backgroundColor: "#efeae2",
              backgroundImage:
                "radial-gradient(#ddd5c9 1px, transparent 1px), radial-gradient(#ddd5c9 1px, transparent 1px)",
              backgroundPosition: "0 0, 8px 8px",
              backgroundSize: "16px 16px",
            }}
          >
            {/* Timestamp pill */}
            <div className="text-center">
              <span className="bg-[#fff2c9] text-[#6d5a2c] text-[9px] font-semibold px-2.5 py-0.5 rounded-full shadow-xs">
                TODAY
              </span>
            </div>

            {/* Outgoing Message Bubble with Pre-filled Content */}
            <div className="max-w-[94%] ml-auto bg-[#dcf8c6] rounded-2xl rounded-tr-xs p-3.5 text-xs text-[#17251e] shadow-sm border border-[#cbe4b7] space-y-1.5">
              <div className="flex items-center justify-between pb-1 border-b border-[#c2deb0]">
                <span className="font-bold text-[#123324] text-[11px]">To: {shopDisplayName}</span>
                <span className="text-[9px] font-bold text-[#1F5D42] bg-white/70 px-2 py-0.5 rounded-full">
                  All Details Pre-filled ✓
                </span>
              </div>
              <p className="text-[11px] leading-relaxed font-body whitespace-pre-line text-[#17251e]">
                {fullMessage}
              </p>
              <div className="text-right text-[9px] text-[#6f7b72] flex items-center justify-end gap-1 pt-1">
                <span>{currentTime}</span>
                <span className="text-[#38a8d1] font-bold">✓✓</span>
              </div>
            </div>

            {/* WhatsApp CTA Action */}
            {whatsappUrl && (
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full mt-3 py-3.5 px-4 bg-[#25D366] hover:bg-[#128C7E] text-white text-xs sm:text-sm font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2 active:scale-[0.99]"
              >
                <MessageCircle className="w-5 h-5 fill-white" />
                <span>Send Order on WhatsApp</span>
                <ExternalLink className="w-4 h-4 opacity-90" />
              </a>
            )}
          </div>
        </div>

        {/* 3. 4-Stage Live Order Status Timeline */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="font-display font-bold text-sm text-[#123324] uppercase tracking-wider pb-2 border-b border-[#eee8dc]">
            Live Order Progress
          </h3>

          <div className="space-y-4 relative pl-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#ddd6ca]">
            {/* Step 1: Placed */}
            <div className="relative">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#1F5D42] text-white flex items-center justify-center ring-4 ring-[#FFFDF8]">
                <Check className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#123324]">Order Placed</h4>
                <p className="text-[11px] text-[#6d756f]">Received at shopkeeper's order desk.</p>
              </div>
            </div>

            {/* Step 2: Accepted */}
            <div className="relative">
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

        {/* 4. Cancellation Action (Valid for 5 mins while pending) */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-4 shadow-sm space-y-3">
          {cancelled ? (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>Order has been successfully cancelled. Reserved items were released.</span>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-[#123324]">Need to make changes?</h4>
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
                  className="mt-3 w-full py-2 border border-red-200 text-red-600 hover:bg-red-50 text-xs font-semibold rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
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

        {/* 5. Return to Shop CTA */}
        <div className="text-center pt-2">
          <Link
            href={`/shop/${publicSlug}`}
            className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-xl bg-[#1F5D42] text-white text-xs font-bold font-display hover:bg-[#123324] shadow-sm transition-all"
          >
            <span>Done · Return to {shop?.name || "Shop"}</span>
          </Link>
        </div>
      </main>
    </div>
  );
}
