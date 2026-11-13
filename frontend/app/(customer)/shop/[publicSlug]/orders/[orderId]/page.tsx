"use client";

import React, { useEffect, useState, useSyncExternalStore } from "react";
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
import { formatPrice } from "@/lib/format";


// Shared language preference (localStorage "dukandaar_lang"), same value on storefront, cart and order pages
const LANG_KEY = "dukandaar_lang";
const LANG_EVENT = "dukandaar-lang-change";
function subscribeLang(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener(LANG_EVENT, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(LANG_EVENT, cb);
  };
}
function getLangSnapshot(): "en" | "hi" {
  try {
    return localStorage.getItem(LANG_KEY) === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
}
function getLangServerSnapshot(): "en" | "hi" {
  return "en";
}

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

  const language = useSyncExternalStore(subscribeLang, getLangSnapshot, getLangServerSnapshot);
  const isHindi = language === "hi";

  // Translate common backend error messages (falls back to the original text)
  const tr = (msg: string): string => {
    if (!isHindi) return msg;
    const m = msg.toLowerCase();
    if (m.includes("accepted") || m.includes("cannot be cancelled") || m.includes("can not be cancelled"))
      return "ऑर्डर रद्द नहीं हो सकता। दुकानदार इसे स्वीकार कर चुके हो सकते हैं।";
    if (m.includes("already") && m.includes("cancel")) return "यह ऑर्डर पहले ही रद्द हो चुका है।";
    if (m.includes("not found")) return "ऑर्डर नहीं मिला।";
    return msg;
  };
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
        tr(err.response?.data?.detail || "") ||
          (isHindi
            ? "ऑर्डर रद्द नहीं हो सका। हो सकता है दुकानदार इसे स्वीकार कर चुके हों।"
            : "Order could not be cancelled. It may have already been accepted by the shopkeeper.")
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
  const customerName = orderData?.customer_name || (isHindi ? "ग्राहक" : "Customer");
  const customerPhone = orderData?.customer_phone || "";
  const fulfillmentType = orderData?.fulfillment_type || "HOME_DELIVERY";
  const fulfillmentStr = isHindi
    ? fulfillmentType === "PICKUP"
      ? "दुकान से पिकअप"
      : "घर पर डिलीवरी"
    : fulfillmentType === "PICKUP"
    ? "Store Pickup (दुकान से पिकअप)"
    : "Home Delivery (घर पर डिलीवरी)";
  const addr = orderData?.delivery_address;
  const addrText = addr ? [addr.address_line, addr.area, addr.city, addr.pincode].filter(Boolean).join(", ") : "";

  const itemsLines = (orderData?.items || []).map(
    (item: any) => `• ${item.product_name}${item.variant_name ? ` (${item.variant_name})` : ""} × ${parseFloat(item.quantity || "1")} = ₹${formatPrice(item.line_total || "0")}`
  );
  const itemsText =
    itemsLines.length > 0
      ? itemsLines.join("\n")
      : isHindi
      ? "• दुकान से सामान"
      : "• Items from store";

  const messageLines = [
    isHindi ? `🛍️ *ऑर्डर #SK-${orderId}*` : `🛍️ *Order #SK-${orderId}*`,
    isHindi ? `दुकान: *${shopDisplayName}*` : `Dukaan: *${shopDisplayName}*`,
    ``,
    `👤 ${isHindi ? "ग्राहक" : "Customer"}: ${customerName}${customerPhone ? ` (${customerPhone})` : ""}`,
    `🚚 ${isHindi ? "डिलीवरी का तरीका" : "Fulfillment"}: ${fulfillmentStr}${addrText ? `\n📍 ${isHindi ? "पता" : "Address"}: ${addrText}` : ""}`,
    ``,
    isHindi ? `📦 *ऑर्डर किया हुआ सामान:*` : `📦 *Items Ordered:*`,
    itemsText,
    ``,
    isHindi ? `💰 *बिल का ब्यौरा:*` : `💰 *Bill Details:*`,
    orderData?.items_subtotal ? `• ${isHindi ? "सामान का कुल" : "Items Total"}: ₹${formatPrice(orderData.items_subtotal)}` : null,
    orderData?.delivery_charge && parseFloat(orderData.delivery_charge) > 0 ? `• ${isHindi ? "डिलीवरी शुल्क" : "Delivery Fee"}: ₹${formatPrice(orderData.delivery_charge)}` : null,
    `• *${isHindi ? "कुल देय" : "Total Payable"}: ₹${orderData?.total_amount ? formatPrice(orderData.total_amount) : "0"}*`,
    ``,
    isHindi
      ? `नमस्ते ${shopDisplayName}! मैंने दुकान से ऑर्डर किया है। कृपया देखकर कन्फर्म करें! 🙏`
      : `Namaste ${shopDisplayName}! Maine dukaan se order place kiya hai. Please check karke confirm karein! 🙏`,
  ].filter((line) => line !== null);

  const fullMessage = messageLines.join("\n");

  const whatsappUrl = cleanShopPhone
    ? `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(fullMessage)}`
    : (serverWaLink || "");

  const currentTime = new Date().toLocaleTimeString(isHindi ? "hi-IN" : [], { hour: "2-digit", minute: "2-digit" });

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
            <span className="text-xs font-bold font-display tracking-tight text-[#1F5D42]">{shop?.name || (isHindi ? "दुकान" : "Shop")}</span>
          </Link>
          <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-[#1F5D42] bg-[#e7f2eb] px-2.5 py-0.5 rounded-full border border-[#cde0d5]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1F5D42] animate-ping" />
            {isHindi ? "लाइव दुकान ऑर्डर" : "Live Storefront Order"}
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
                <span className="text-red-700 bg-red-100 px-2 py-0.5 rounded-full">{isHindi ? "ऑर्डर रद्द हुआ" : "Order Cancelled / रद्द किया गया"}</span>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#1F5D42]" />
                  <span>{isHindi ? "ऑर्डर दर्ज हो गया" : "Order Placed Successfully · ऑर्डर दर्ज हुआ"}</span>
                </>
              )}
            </div>

            <h1 className="font-display font-bold text-2xl sm:text-3xl text-[#123324] leading-tight">
              {cancelled
                ? isHindi
                  ? "ऑर्डर रद्द कर दिया गया है"
                  : "Order has been cancelled"
                : isHindi
                ? "आपका ऑर्डर पक्का हो गया!"
                : "Your order is confirmed!"}
            </h1>
            <p className="text-xs text-[#5e665f] mt-1 max-w-sm mx-auto leading-relaxed">
              {cancelled ? (
                isHindi
                  ? "यह ऑर्डर ग्राहक के कहने पर रद्द किया गया। रखा हुआ सामान वापस दुकान की शेल्फ में रख दिया गया है।"
                  : "This order was cancelled by customer request. Reserved items have been returned to the store shelf."
              ) : (
                <>
                  {isHindi ? (
                    <>
                      <strong className="text-[#123324] font-semibold">{shop?.name || "दुकान"}</strong> को आपका ऑर्डर{" "}
                      <b className="text-[#1F5D42]">#SK-{orderId}</b> मिल गया है।
                    </>
                  ) : (
                    <>
                      <strong className="text-[#123324] font-semibold">{shop?.name || "Shop"}</strong> has received your order{" "}
                      <b className="text-[#1F5D42]">#SK-{orderId}</b>.
                    </>
                  )}
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
              title={isHindi ? "ऑर्डर नंबर कॉपी करें" : "Copy Order ID"}
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
                    {isHindi ? "व्हाट्सएप पर दुकानदार को ऑर्डर भेजें" : "Send Details to Merchant via WhatsApp"}
                  </h3>
                  <span className="text-[9px] font-bold bg-[#25D366] text-white px-2 py-0.5 rounded-full">
                    {isHindi ? "सुझाया गया" : "Recommended"}
                  </span>
                </div>
                <p className="text-xs text-[#5e665f] mt-0.5 leading-snug">
                  {isHindi ? (
                    <>
                      व्यापारी <b>{shopDisplayName}</b> को तुरंत व्हाट्सएप पर ऑर्डर भेजें ताकि वो सामान पैक करके जल्दी भेज सकें।
                    </>
                  ) : (
                    <>
                      Send the order to <b>{shopDisplayName}</b> on WhatsApp right away so they can pack and dispatch it quickly.
                    </>
                  )}
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
                <span>{isHindi ? "व्हाट्सएप पर ऑर्डर भेजें" : "Send Order on WhatsApp · व्हाट्सएप पर भेजें"}</span>
                <ExternalLink className="w-4 h-4 opacity-90" />
              </a>
            ) : (
              <p className="text-xs text-amber-700 bg-amber-50 p-3 rounded-xl border border-amber-200">
                {isHindi
                  ? "दुकानदार का व्हाट्सएप नंबर उपलब्ध नहीं है। आपका ऑर्डर उनके लाइव डैशबोर्ड में दर्ज है।"
                  : "Shopkeeper contact number is not available for WhatsApp. The order is recorded in their live dashboard."}
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
                    <p className="text-[8px] text-white/80">{isHindi ? "पहले से भरे संदेश का प्रीव्यू" : "pre-filled message preview"}</p>
                  </div>
                </div>
                <span className="text-[9px] font-semibold bg-white/20 px-2 py-0.5 rounded text-white/90">
                  {isHindi ? "भेजने के लिए तैयार" : "Ready to send"}
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
              <span>{isHindi ? `सामान का ब्यौरा (${orderData?.items?.length || 0} सामान)` : `Items Breakdown (${orderData?.items?.length || 0} items)`}</span>
            </h3>
            <span className="text-xs font-bold text-[#1F5D42]">
              ₹{orderData?.total_amount ? formatPrice(orderData.total_amount) : "0"}
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
                    ₹{formatPrice(item.unit_price || "0")} × {parseFloat(item.quantity || "1")}
                  </p>
                </div>
                <span className="font-bold text-[#123324]">
                  ₹{formatPrice(item.line_total || "0")}
                </span>
              </div>
            ))}
          </div>

          {/* Pricing Totals */}
          <div className="pt-2 border-t border-[#eee8dc] space-y-1.5 text-xs text-[#5e665f]">
            <div className="flex justify-between">
              <span>{isHindi ? "सामान का कुल" : "Items Subtotal"}</span>
              <span>₹{orderData?.items_subtotal ? formatPrice(orderData.items_subtotal) : "0"}</span>
            </div>
            {orderData?.delivery_charge && parseFloat(orderData.delivery_charge) > 0 && (
              <div className="flex justify-between">
                <span>{isHindi ? "डिलीवरी शुल्क" : "Delivery Charge"}</span>
                <span>₹{formatPrice(orderData.delivery_charge)}</span>
              </div>
            )}
            <div className="flex justify-between pt-1 border-t border-[#eee8dc] text-sm font-bold text-[#123324]">
              <span>{isHindi ? "कुल बिल" : "Grand Total"}</span>
              <span className="text-[#1F5D42]">
                ₹{orderData?.total_amount ? formatPrice(orderData.total_amount) : "0"}
              </span>
            </div>
          </div>
        </div>

        {/* 4. Delivery & Customer Information Card */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-5 shadow-sm space-y-3">
          <h3 className="font-display font-bold text-xs uppercase tracking-wider text-[#123324] pb-2 border-b border-[#eee8dc]">
            {isHindi ? "डिलीवरी और ग्राहक की जानकारी" : "Fulfillment & Customer Details"}
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
            {isHindi ? "ऑर्डर की लाइव स्थिति" : "Live Order Progress"}
          </h3>

          <div className="space-y-4 relative pl-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#ddd6ca]">
            {/* Step 1: Placed */}
            <div className="relative">
              <span className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full ${cancelled ? "bg-red-500" : "bg-[#1F5D42]"} text-white flex items-center justify-center ring-4 ring-[#FFFDF8]`}>
                {cancelled ? <XCircle className="w-3 h-3" /> : <Check className="w-3 h-3" />}
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#123324]">{isHindi ? "ऑर्डर दर्ज हुआ" : "Order Placed"}</h4>
                <p className="text-[11px] text-[#6d756f]">{isHindi ? "दुकानदार के ऑर्डर डेस्क पर पहुंच गया।" : "Received in shopkeeper's order desk."}</p>
              </div>
            </div>

            {/* Step 2: Accepted */}
            <div className={`relative ${cancelled ? "opacity-40" : ""}`}>
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#E8A33D] text-white flex items-center justify-center ring-4 ring-[#FFFDF8] animate-pulse">
                <Store className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#123324]">{isHindi ? "दुकानदार की पुष्टि का इंतज़ार" : "Awaiting Dukandaar Confirmation"}</h4>
                <p className="text-[11px] text-[#6d756f]">{isHindi ? "दुकानदार शेल्फ पर सामान चेक करते हैं।" : "Shopkeeper verifies live stock on shelves."}</p>
              </div>
            </div>

            {/* Step 3: Packing */}
            <div className="relative opacity-50">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#ddd6ca] text-white flex items-center justify-center ring-4 ring-[#FFFDF8]">
                <Clock className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#6d756f]">{isHindi ? "सामान की पैकिंग" : "Packing Items"}</h4>
                <p className="text-[11px] text-[#8e9690]">{isHindi ? "आपके लिए ताज़ा सामान पैक हो रहा है।" : "Fresh products packed for you."}</p>
              </div>
            </div>

            {/* Step 4: Out for Delivery */}
            <div className="relative opacity-50">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#ddd6ca] text-white flex items-center justify-center ring-4 ring-[#FFFDF8]">
                <Bike className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#6d756f]">{isHindi ? "डिलीवरी के लिए निकला / पिकअप के लिए तैयार" : "Out for Delivery / Ready for Pickup"}</h4>
                <p className="text-[11px] text-[#8e9690]">{isHindi ? "आपके दरवाज़े तक भेजा जा रहा है।" : "Dispatched to your doorstep."}</p>
              </div>
            </div>
          </div>
        </div>

        {/* 6. Order Cancellation Action (Valid for 5 mins while pending) */}
        <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-2xl p-4 shadow-sm space-y-3">
          {cancelled ? (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>{isHindi ? "ऑर्डर रद्द हो गया है। रखा हुआ सामान वापस दुकान की शेल्फ में रख दिया गया है।" : "Order has been successfully cancelled. Reserved items were released back to the store shelf."}</span>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-[#123324]">{isHindi ? "ऑर्डर रद्द करना है?" : "Need to cancel?"}</h4>
                  <p className="text-[11px] text-[#6d756f]">
                    {isHindi
                      ? `पैकिंग शुरू होने से पहले आप ${timeFormatted} मिनट के अंदर ऑर्डर रद्द कर सकते हैं।`
                      : `You can cancel your order within ${timeFormatted} minutes before packing begins.`}
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
                      <span>{isHindi ? "ऑर्डर रद्द हो रहा है…" : "Cancelling order…"}</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3.5 h-3.5" />
                      <span>{isHindi ? `ऑर्डर रद्द करें (${timeFormatted} बाकी)` : `Cancel Order (${timeFormatted} remaining)`}</span>
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
            <span>{isHindi ? `हो गया · ${shop?.name || "दुकान"} पर वापस जाएं` : `Done · Return to ${shop?.name || "Shop"}`}</span>
          </Link>
        </div>
      </main>
    </div>
  );
}

