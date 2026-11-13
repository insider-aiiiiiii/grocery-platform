"use client";

import React, { useState, useMemo } from "react";
import {
  Receipt,
  Search,
  Calendar,
  Filter,
  ArrowRight,
  RefreshCw,
  ShoppingBag,
  Truck,
  Store,
  CheckCircle2,
  Clock,
  MessageCircle,
  X,
  Phone,
  Printer,
  ChevronDown,
} from "lucide-react";
import { MerchantOrder } from "@/lib/api/merchant";

const money = (value?: string | number | null, hi = false) =>
  `₹${Number(value ?? 0).toLocaleString(hi ? "hi-IN" : "en-IN", { maximumFractionDigits: 2 })}`;

const dateTime = (value: string, hi = false) =>
  new Date(value).toLocaleString(hi ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" });

const STATUS_HI: Record<string, string> = {
  PENDING: "नया",
  ACCEPTED: "स्वीकार किया",
  PREPARING: "पैक हो रहा है",
  READY: "तैयार",
  COMPLETED: "पूरा हुआ",
  REJECTED: "अस्वीकार",
};
const statusLabel = (status: string, hi: boolean) => (hi ? STATUS_HI[status] ?? status : status);

interface OrdersHistoryViewProps {
  orders: MerchantOrder[];
  loading: boolean;
  error: unknown;
  onRefresh: () => void;
  lang?: "en" | "hi";
}

export function OrdersHistoryView({
  orders,
  loading,
  error,
  onRefresh,
  lang = "en",
}: OrdersHistoryViewProps) {
  const isHi = lang === "hi";

  const [search, setSearch] = useState("");
  const [dateFilter, setDateFilter] = useState<"all" | "today" | "yesterday" | "7days" | "month" | "custom">("all");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [fulfillmentFilter, setFulfillmentFilter] = useState<"ALL" | "HOME_DELIVERY" | "PICKUP">("ALL");
  const [selectedOrder, setSelectedOrder] = useState<MerchantOrder | null>(null);
  const [expandedOrderItems, setExpandedOrderItems] = useState<Record<number, boolean>>({});

  // Filter orders by date, fulfillment mode, and search query
  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      // 1. Search filter
      const q = search.toLowerCase().trim();
      if (q) {
        const idMatch = `#sk-${order.id}`.includes(q) || String(order.id).includes(q);
        const nameMatch = (order.customer_name_snapshot || "").toLowerCase().includes(q);
        const phoneMatch = (order.customer_phone_snapshot || "").includes(q);
        const itemMatch = (order.items || []).some((it) =>
          it.product_name_snapshot.toLowerCase().includes(q)
        );
        if (!idMatch && !nameMatch && !phoneMatch && !itemMatch) return false;
      }

      // 2. Fulfillment type filter
      if (fulfillmentFilter !== "ALL" && order.fulfillment_type !== fulfillmentFilter) {
        return false;
      }

      // 3. Date filter
      if (dateFilter === "all") return true;

      const orderDate = new Date(order.created_at);
      const now = new Date();

      if (dateFilter === "today") {
        return (
          orderDate.getDate() === now.getDate() &&
          orderDate.getMonth() === now.getMonth() &&
          orderDate.getFullYear() === now.getFullYear()
        );
      }

      if (dateFilter === "yesterday") {
        const yesterday = new Date();
        yesterday.setDate(now.getDate() - 1);
        return (
          orderDate.getDate() === yesterday.getDate() &&
          orderDate.getMonth() === yesterday.getMonth() &&
          orderDate.getFullYear() === yesterday.getFullYear()
        );
      }

      if (dateFilter === "7days") {
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(now.getDate() - 7);
        return orderDate >= sevenDaysAgo;
      }

      if (dateFilter === "month") {
        return (
          orderDate.getMonth() === now.getMonth() &&
          orderDate.getFullYear() === now.getFullYear()
        );
      }

      if (dateFilter === "custom") {
        if (!customStart || !customEnd) return true;
        const start = new Date(customStart);
        start.setHours(0, 0, 0, 0);
        const end = new Date(customEnd);
        end.setHours(23, 59, 59, 999);
        return orderDate >= start && orderDate <= end;
      }

      return true;
    });
  }, [orders, search, dateFilter, customStart, customEnd, fulfillmentFilter]);

  // Aggregate metrics for active filter
  const metrics = useMemo(() => {
    const totalCount = filteredOrders.length;
    const totalAmount = filteredOrders.reduce(
      (sum, o) => sum + parseFloat(o.total_amount || "0"),
      0
    );
    const homeCount = filteredOrders.filter((o) => o.fulfillment_type === "HOME_DELIVERY").length;
    const pickupCount = filteredOrders.filter((o) => o.fulfillment_type === "PICKUP").length;
    const completedCount = filteredOrders.filter((o) => o.status === "COMPLETED").length;

    return { totalCount, totalAmount, homeCount, pickupCount, completedCount };
  }, [filteredOrders]);

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#eee9df] pb-5">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-[.18em] text-[#1F5D42]">
            {isHi ? "दुकान ऑर्डर रिकॉर्ड्स" : "Order History Desk"}
          </span>
          <h1 className="font-display text-2xl font-bold tracking-tight text-[#123324] sm:text-3xl mt-0.5">
            {isHi ? "ऑर्डर इतिहास व पक्का बिल" : "Orders History"}
          </h1>
          <p className="mt-1 text-xs text-[#6d756f]">
            {isHi
              ? "दुकान के सभी पिछले ऑर्डर्स, डिलीवरी माध्यम, खरीदे गए सामान और बिल का संपूर्ण विवरण।"
              : "Review past store orders, delivery modes, items purchased, and itemized billing snapshots."}
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[#ddd6ca] bg-white hover:bg-[#F6F0E6] text-xs font-semibold text-[#1F5D42] transition shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>{isHi ? "रिफ्रेश करें" : "Refresh Orders"}</span>
        </button>
      </div>

      {/* Aggregate KPI Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-[#6d756f]">
            {isHi ? "दर्ज ऑर्डर्स" : "Recorded Orders"}
          </span>
          <p className="font-display text-2xl font-bold text-[#123324] mt-1">
            {metrics.totalCount}
          </p>
          <span className="text-[10px] text-[#1F5D42] mt-0.5 block">
            {metrics.completedCount} {isHi ? "सफलतापूर्वक पूर्ण" : "fulfilled"}
          </span>
        </div>

        <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-[#6d756f]">
            {isHi ? "कुल बिक्री" : "Filtered Sales"}
          </span>
          <p className="font-display text-2xl font-bold text-[#1F5D42] mt-1">
            {money(metrics.totalAmount, isHi)}
          </p>
          <span className="text-[10px] text-[#869088] mt-0.5 block">
            {isHi ? "सभी ऑर्डर्स का योग" : "Gross order value"}
          </span>
        </div>

        <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-[#6d756f]">
            {isHi ? "होम डिलीवरी" : "Home Delivery"}
          </span>
          <p className="font-display text-2xl font-bold text-[#8a5b1d] mt-1">
            {metrics.homeCount}
          </p>
          <span className="text-[10px] text-[#8a5b1d] mt-0.5 block">
            {isHi ? "घर पहुंचाए गए ऑर्डर्स" : "Delivered to address"}
          </span>
        </div>

        <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-4 shadow-2xs">
          <span className="text-[11px] font-semibold text-[#6d756f]">
            {isHi ? "दुकान से पिकअप" : "Store Pickup"}
          </span>
          <p className="font-display text-2xl font-bold text-[#3d6072] mt-1">
            {metrics.pickupCount}
          </p>
          <span className="text-[10px] text-[#3d6072] mt-0.5 block">
            {isHi ? "काउंटर से उठाए गए" : "Collected in store"}
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="rounded-2xl border border-[#ddd6ca] bg-white p-4 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Search box */}
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#869088]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={
                isHi
                  ? "ऑर्डर #SK-, ग्राहक का नाम, फ़ोन या सामान खोजें..."
                  : "Search by Order ID, customer name, phone, or item..."
              }
              className="h-10 w-full rounded-xl bg-white border border-[#ddd6ca] pl-9 pr-3 text-xs outline-none focus:border-[#1F5D42]"
            />
          </div>

          {/* Fulfillment Mode Filter */}
          <div className="flex items-center gap-1.5 self-end md:self-auto">
            <select
              value={fulfillmentFilter}
              onChange={(e) => setFulfillmentFilter(e.target.value as any)}
              className="h-10 rounded-xl border border-[#ddd6ca] bg-white px-3 text-xs font-semibold text-[#123324] outline-none"
            >
              <option value="ALL">{isHi ? "सभी तरीके" : "All Fulfillment"}</option>
              <option value="HOME_DELIVERY">{isHi ? "घर पर डिलीवरी" : "Home Delivery"}</option>
              <option value="PICKUP">{isHi ? "दुकान से पिकअप" : "Store Pickup"}</option>
            </select>
          </div>
        </div>

        {/* Date Filter Badges */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-[#eee9df]">
          <span className="text-[11px] font-semibold text-[#6d756f] mr-1 flex items-center gap-1">
            <Calendar size={13} className="text-[#1F5D42]" />
            <span>{isHi ? "अवधि:" : "Time Filter:"}</span>
          </span>

          {[
            { id: "all", labelEn: "All Time", labelHi: "सभी समय" },
            { id: "today", labelEn: "Today", labelHi: "आज" },
            { id: "yesterday", labelEn: "Yesterday", labelHi: "कल" },
            { id: "7days", labelEn: "Past 7 Days", labelHi: "पिछले 7 दिन" },
            { id: "month", labelEn: "This Month", labelHi: "इस माह" },
            { id: "custom", labelEn: "Custom Date Range", labelHi: "कस्टम तारीख" },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setDateFilter(pill.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                dateFilter === pill.id
                  ? "bg-[#1F5D42] text-white shadow-2xs"
                  : "bg-[#faf8f3] border border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
              }`}
            >
              {isHi ? pill.labelHi : pill.labelEn}
            </button>
          ))}

          {dateFilter === "custom" && (
            <div className="flex items-center gap-2 mt-2 sm:mt-0 w-full sm:w-auto">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="h-8 rounded-lg border border-[#ddd6ca] px-2 text-xs bg-white outline-none"
              />
              <span className="text-xs text-[#6d756f]">{isHi ? "से" : "to"}</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="h-8 rounded-lg border border-[#ddd6ca] px-2 text-xs bg-white outline-none"
              />
            </div>
          )}
        </div>
      </div>

      {/* Orders Table */}
      {loading ? (
        <div className="p-12 text-center text-xs text-[#6d756f] bg-white rounded-2xl border border-[#ddd6ca]">
          <RefreshCw size={24} className="mx-auto text-[#1F5D42] animate-spin mb-2" />
          <p>{isHi ? "ऑर्डर्स लोड हो रहे हैं…" : "Loading past order history…"}</p>
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-[#ddd6ca] space-y-2">
          <Receipt size={36} className="mx-auto text-[#baa98a] opacity-60" />
          <h3 className="font-display font-bold text-sm text-[#123324]">
            {isHi ? "कोई ऑर्डर नहीं मिला" : "No orders found"}
          </h3>
          <p className="text-xs text-[#6d756f] max-w-sm mx-auto">
            {isHi
              ? "चुनी गई अवधि या खोज फ़िल्टर में कोई ऑर्डर मौजूद नहीं है।"
              : "No orders match your active search or date filter."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[#ddd6ca] bg-white shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#eee9df] bg-[#faf8f3] text-[10px] font-bold uppercase tracking-wider text-[#6d756f]">
                  <th className="py-3 px-4">{isHi ? "ऑर्डर नंबर" : "Order ID"}</th>
                  <th className="py-3 px-4">{isHi ? "तारीख व समय" : "Date & Time"}</th>
                  <th className="py-3 px-4">{isHi ? "ग्राहक" : "Customer"}</th>
                  <th className="py-3 px-4">{isHi ? "डिलीवरी प्रकार" : "Fulfillment"}</th>
                  <th className="py-3 px-4">{isHi ? "सामान" : "Items Summary"}</th>
                  <th className="py-3 px-4 text-right">{isHi ? "कुल बिल" : "Total Bill"}</th>
                  <th className="py-3 px-4 text-center">{isHi ? "स्थिति" : "Status"}</th>
                  <th className="py-3 px-4 text-right">{isHi ? "कार्रवाई" : "Action"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#eee9df]">
                {filteredOrders.map((order) => {
                  const isHome = order.fulfillment_type === "HOME_DELIVERY";
                  const itemsCount = (order.items || []).length;
                  const itemPreview = (order.items || [])
                    .slice(0, 2)
                    .map((it) => `${it.product_name_snapshot} (${it.quantity})`)
                    .join(", ");

                  return (
                    <tr
                      key={order.id}
                      onClick={() => setSelectedOrder(order)}
                      className="hover:bg-[#faf8f3] transition cursor-pointer"
                    >
                      {/* Order ID */}
                      <td className="py-3 px-4 font-mono font-bold text-[#1F5D42]">
                        #SK-{order.id}
                      </td>

                      {/* Date & Time */}
                      <td className="py-3 px-4 text-[#5e665f] whitespace-nowrap">
                        {dateTime(order.created_at, isHi)}
                      </td>

                      {/* Customer */}
                      <td className="py-3 px-4">
                        <p className="font-bold text-[#123324] leading-tight">
                          {order.customer_name_snapshot || (isHi ? "ग्राहक" : "Customer")}
                        </p>
                        <p className="text-[11px] font-mono text-[#869088] mt-0.5">
                          {order.customer_phone_snapshot}
                        </p>
                      </td>

                      {/* Fulfillment */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                            isHome
                              ? "bg-[#fff3db] text-[#8a5b1d] border-[#f5deb5]"
                              : "bg-[#e4edf2] text-[#456b7f] border-[#cbe1ed]"
                          }`}
                        >
                          {isHome ? <Truck size={11} /> : <Store size={11} />}
                          <span>{isHome ? (isHi ? "घर पर" : "Delivery") : (isHi ? "पिकअप" : "Pickup")}</span>
                        </span>
                      </td>

                      {/* Items */}
                      <td className="py-3 px-4 max-w-xs">
                        <span className="font-bold text-[#123324]">{itemsCount} {isHi ? "सामान" : "items"}</span>
                        <div className="text-[11px] text-[#6d756f] mt-0.5 space-y-0.5">
                          <p className="truncate">{itemPreview}</p>
                          {itemsCount > 2 && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedOrderItems((prev) => ({ ...prev, [order.id]: !prev[order.id] }));
                              }}
                              className="text-[10px] text-[#1F5D42] font-bold hover:underline block"
                            >
                              {expandedOrderItems[order.id]
                                ? (isHi ? "कम दिखाएं ▲" : "Show less ▲")
                                : (isHi ? `+${itemsCount - 2} और दिखाएं ▼` : `+${itemsCount - 2} more ▼`)}
                            </button>
                          )}
                          {expandedOrderItems[order.id] && (
                            <div className="mt-1 pl-2 border-l-2 border-[#1F5D42]/30 text-[10px] text-[#123324] space-y-0.5">
                              {(order.items || []).slice(2).map((it, idx) => (
                                <div key={idx} className="truncate">
                                  • {it.product_name_snapshot} ({it.quantity})
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Total Bill */}
                      <td className="py-3 px-4 text-right">
                        <span className="font-display font-bold text-sm text-[#123324]">
                          {money(order.total_amount, isHi)}
                        </span>
                        {order.delivery_charge_snapshot && parseFloat(order.delivery_charge_snapshot) > 0 && (
                          <span className="block text-[10px] text-[#869088]">
                            +{money(order.delivery_charge_snapshot, isHi)} {isHi ? "शुल्क" : "fee"}
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            order.status === "COMPLETED"
                              ? "bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5]"
                              : order.status === "REJECTED"
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : "bg-amber-50 text-amber-800 border border-amber-200"
                          }`}
                        >
                          {statusLabel(order.status, isHi)}
                        </span>
                      </td>

                      {/* Action */}
                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          {order.customer_phone_snapshot && (
                            <a
                              href={`https://wa.me/${(order.customer_phone_snapshot.replace(/\D/g, "").length === 10 ? `91${order.customer_phone_snapshot.replace(/\D/g, "")}` : order.customer_phone_snapshot.replace(/\D/g, ""))}?text=${encodeURIComponent(
                                isHi
                                  ? `नमस्ते ${order.customer_name_snapshot || "ग्राहक"} जी! आपके ऑर्डर #SK-${order.id} (कुल बिल ₹${parseFloat(order.total_amount || "0").toFixed(0)}) के संबंध में। धन्यवाद! 🙏`
                                  : `Namaste ${order.customer_name_snapshot || "Customer"}! Regarding your order #SK-${order.id} for ₹${parseFloat(order.total_amount || "0").toFixed(0)}. Thank you! 🙏`
                              )}`}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-[#25D366]/10 hover:bg-[#25D366] text-[#128C7E] hover:text-white font-bold text-[10px] transition shadow-2xs"
                              title={isHi ? "व्हाट्सएप पर भेजें" : "Send WhatsApp Message"}
                            >
                              <MessageCircle size={11} />
                              <span>{isHi ? "व्हाट्सएप" : "WhatsApp"}</span>
                            </a>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedOrder(order);
                            }}
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-[#1F5D42] hover:underline"
                          >
                            <span>{isHi ? "बिल देखें" : "View Bill"}</span>
                            <ArrowRight size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Order Detail & Itemized Bill Modal */}
      {selectedOrder && (
        <OrderDetailModal
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
          lang={lang}
        />
      )}
    </div>
  );
}

// -------------------------------------------------------------
// Helper Component: Full Itemized Order & Bill Modal
// -------------------------------------------------------------
function OrderDetailModal({
  order,
  onClose,
  lang = "en",
}: {
  order: MerchantOrder;
  onClose: () => void;
  lang?: "en" | "hi";
}) {
  const isHi = lang === "hi";
  const isHome = order.fulfillment_type === "HOME_DELIVERY";
  const shortId = `#SK-${order.id}`;
  const total = parseFloat(order.total_amount || "0").toFixed(0);

  // Pre-fill WhatsApp message
  const cleanPhone = (order.customer_phone_snapshot || "").replace(/\D/g, "");
  const phoneWithCountry = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-xl rounded-3xl bg-[#FFFDF8] border border-[#ddd6ca] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#eee9df] px-6 py-4 bg-white">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#e7f2eb] font-mono text-sm font-bold text-[#1F5D42]">
              #{order.id}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display font-bold text-base text-[#123324]">
                  {shortId} · {order.customer_name_snapshot || (isHi ? "ग्राहक" : "Customer")}
                </h3>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    order.status === "COMPLETED"
                      ? "bg-[#e7f2eb] text-[#1F5D42]"
                      : "bg-amber-50 text-amber-800"
                  }`}
                >
                  {statusLabel(order.status, isHi)}
                </span>
              </div>
              <p className="text-[11px] text-[#6d756f] mt-0.5">
                {dateTime(order.created_at, isHi)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="p-1.5 rounded-xl border border-[#ddd6ca] text-[#6d756f] hover:text-[#123324] hover:bg-[#faf8f3]"
              title={isHi ? "रसीद प्रिंट करें" : "Print Receipt"}
            >
              <Printer size={16} />
            </button>
            <button
              onClick={onClose}
              aria-label={isHi ? "बंद करें" : "Close"}
              className="p-1.5 rounded-xl text-[#6d756f] hover:text-[#123324] hover:bg-[#eee9df]"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto text-xs">
          {/* Customer & Fulfillment Info Card */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 rounded-2xl bg-[#faf8f3] border border-[#eee9df]">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#6d756f] block">
                {isHi ? "ग्राहक संपर्क" : "Customer Contact"}
              </span>
              <p className="font-bold text-sm text-[#123324] mt-1">
                {order.customer_name_snapshot || (isHi ? "ग्राहक" : "Customer")}
              </p>
              <p className="font-mono text-xs text-[#1F5D42] mt-0.5 flex items-center gap-1">
                <Phone size={12} />
                <span>{order.customer_phone_snapshot}</span>
              </p>
            </div>

            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#6d756f] block">
                {isHi ? "डिलीवरी का तरीका" : "Fulfillment Mode"}
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <span
                  className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                    isHome
                      ? "bg-[#fff3db] text-[#8a5b1d] border-[#f5deb5]"
                      : "bg-[#e4edf2] text-[#456b7f] border-[#cbe1ed]"
                  }`}
                >
                  {isHome ? <Truck size={12} /> : <Store size={12} />}
                  <span>{isHome ? (isHi ? "घर पर होम डिलीवरी" : "Home Delivery") : (isHi ? "दुकान से पिकअप" : "Store Pickup")}</span>
                </span>
              </div>
              {isHome && order.delivery_address && (
                <p className="text-[11px] text-[#5e665f] mt-1.5 leading-relaxed">
                  📍 {[order.delivery_address.address_line, order.delivery_address.area, order.delivery_address.city, order.delivery_address.pincode].filter(Boolean).join(", ")}
                </p>
              )}
            </div>
          </div>

          {/* Itemized Bill Breakdown */}
          <div className="rounded-2xl border border-[#ddd6ca] bg-white overflow-hidden shadow-2xs">
            <div className="bg-[#faf8f3] px-4 py-2.5 border-b border-[#eee9df] font-bold text-xs text-[#123324]">
              {isHi ? "आइटम अनुसार विवरण" : "Itemized Order Items"}
            </div>
            <div className="divide-y divide-[#eee9df] p-4 space-y-2">
              {order.items?.map((item) => (
                <div key={item.id} className="flex items-center justify-between pt-2 first:pt-0">
                  <div className="min-w-0 pr-3">
                    <p className="font-semibold text-xs text-[#123324]">
                      {item.product_name_snapshot}
                      {item.variant_name_snapshot ? ` (${item.variant_name_snapshot})` : ""}
                    </p>
                    <p className="text-[10px] text-[#6d756f] mt-0.5">
                      {money(item.unit_price_snapshot, isHi)} × {item.quantity}
                    </p>
                  </div>
                  <span className="font-mono font-bold text-xs text-[#123324]">
                    {money(item.line_total, isHi)}
                  </span>
                </div>
              ))}
            </div>

            {/* Bill Financial Summary */}
            <div className="bg-[#faf8f3] p-4 border-t border-[#eee9df] space-y-1.5 text-xs">
              <div className="flex justify-between text-[#6d756f]">
                <span>{isHi ? "सामान का कुल मूल्य" : "Items Subtotal"}</span>
                <span className="font-mono">{money(order.items_subtotal, isHi)}</span>
              </div>

              {order.delivery_charge_snapshot && parseFloat(order.delivery_charge_snapshot) > 0 ? (
                <div className="flex justify-between text-[#6d756f]">
                  <span>{isHi ? "डिलीवरी शुल्क" : "Delivery Charge"}</span>
                  <span className="font-mono">{money(order.delivery_charge_snapshot, isHi)}</span>
                </div>
              ) : (
                <div className="flex justify-between text-[#1F5D42]">
                  <span>{isHi ? "डिलीवरी शुल्क" : "Delivery Charge"}</span>
                  <span className="font-bold">{isHi ? "मुफ़्त" : "FREE"}</span>
                </div>
              )}

              <div className="flex justify-between pt-2 border-t border-[#ddd6ca] text-sm font-bold text-[#123324]">
                <span>{isHi ? "कुल देय राशि" : "Total Bill Amount"}</span>
                <span className="font-mono text-base text-[#1F5D42]">{money(order.total_amount, isHi)}</span>
              </div>

              <div className="pt-1 flex items-center justify-between text-[11px] text-[#6d756f]">
                <span>{isHi ? "भुगतान स्थिति" : "Payment Status"}</span>
                <span className="font-bold text-[#123324]">
                  {order.payment_status === "PAID"
                    ? isHi
                      ? "ऑनलाइन भुगतान पूर्ण ✓"
                      : "Paid Online ✓"
                    : isHi
                    ? "कैश ऑन डिलीवरी / लंबित"
                    : "Cash on Delivery / Pending"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer WhatsApp Actions */}
        <div className="border-t border-[#eee9df] px-6 py-4 bg-white flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-[#6d756f] hover:text-[#123324]"
          >
            {isHi ? "बंद करें" : "Close"}
          </button>

          {phoneWithCountry && (
            <div className="flex flex-wrap items-center gap-2">
              <a
                href={`https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(
                  isHi
                    ? `नमस्ते ${order.customer_name_snapshot || "ग्राहक"} जी! आपके ऑर्डर ${shortId} (₹${total}) के संबंध में। हमारे यहां खरीदारी के लिए धन्यवाद! 🙏`
                    : `Namaste ${order.customer_name_snapshot || "Customer"}! Regarding your order ${shortId} for ₹${total}. Thank you for shopping with us! 🙏`
                )}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#25D366] hover:bg-[#1fb858] text-white text-xs font-bold shadow-xs transition active:scale-95"
              >
                <MessageCircle size={14} className="fill-white" />
                <span>{isHi ? "व्हाट्सएप चैट" : "WhatsApp"}</span>
              </a>

              <a
                href={`https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(
                  isHi
                    ? `🛍️ *ऑर्डर ${shortId} का बिल*\nग्राहक: ${order.customer_name_snapshot}\nकुल देय राशि: ₹${total}\nधन्यवाद! 🙏`
                    : `🛍️ *Order ${shortId} Bill*\nCustomer: ${order.customer_name_snapshot}\nTotal Payable: ₹${total}\nThank you! 🙏`
                )}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[#cde0d5] bg-[#f0f7f3] hover:bg-[#e2efe7] text-[#1F5D42] text-xs font-bold shadow-xs transition active:scale-95"
              >
                <Receipt size={14} />
                <span>{isHi ? "बिल भेजें 🧾" : "Share Bill 🧾"}</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
