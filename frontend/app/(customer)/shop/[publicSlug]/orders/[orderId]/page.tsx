"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  Clock,
  MessageCircle,
  Copy,
  Check,
  Store,
  Bike,
  AlertCircle,
  ArrowLeft,
  XCircle,
  RefreshCw,
} from "lucide-react";
import { customerApi, PublicShopInfo } from "@/lib/api/customer";

export default function OrderConfirmationPage() {
  const params = useParams();
  const router = useRouter();
  const publicSlug = Array.isArray(params?.publicSlug)
    ? params.publicSlug[0]
    : (params?.publicSlug as string);
  const orderId = Array.isArray(params?.orderId)
    ? params.orderId[0]
    : (params?.orderId as string);

  const [shop, setShop] = useState<PublicShopInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  // 5-minute countdown timer state (300 seconds)
  const [secondsLeft, setSecondsLeft] = useState(300);

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
    navigator.clipboard.writeText(`#ORD-${orderId}`);
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

  const cleanShopPhone = shop?.contact_number?.replace(/\D/g, "") || "";
  const whatsappUrl = `https://wa.me/${cleanShopPhone}?text=Namaste!%20I%20have%20placed%20Order%20%23ORD-${orderId}%20on%20your%20dukaan.%20Please%20confirm!`;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-16">
      {/* Top Bar */}
      <header className="bg-white border-b border-slate-200 px-4 py-3">
        <div className="max-w-xl mx-auto flex items-center justify-between">
          <Link
            href={`/shop/${publicSlug}`}
            className="flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
            <span className="text-xs font-bold text-slate-900">{shop?.name || "Store"}</span>
          </Link>
          <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
            Order Confirmed
          </span>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-4">
        {/* 1. Hero Celebration Card */}
        <div className="bg-white border border-slate-200 rounded-3xl p-6 text-center space-y-3 shadow-sm relative overflow-hidden">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border-2 border-emerald-200 shadow-inner">
            <CheckCircle2 className="w-9 h-9" />
          </div>

          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">
              Order Received & Sent to Dukaan!
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Your order has reached {shop?.name || "the shopkeeper"}. Preparing fresh items for you.
            </p>
          </div>

          {/* Order ID Token Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs font-bold text-slate-800">
            <span>Order #ORD-{orderId}</span>
            <button
              onClick={handleCopyOrderId}
              className="text-slate-400 hover:text-slate-700 transition-colors"
              title="Copy Order ID"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* 2. Direct WhatsApp Communication Card */}
        {cleanShopPhone && (
          <div className="bg-[#25D366]/10 border border-[#25D366]/30 rounded-2xl p-4 space-y-3 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#25D366] text-white flex items-center justify-center shrink-0 shadow-sm">
                <MessageCircle className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="text-xs font-bold text-slate-900 leading-tight">
                  Instant WhatsApp Confirmation
                </h3>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Send a 1-tap message to {shop?.name} on WhatsApp to get real-time packing photos and updates.
                </p>
              </div>
            </div>

            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-2.5 px-4 bg-[#25D366] hover:bg-[#1EBE5D] text-white text-xs font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
            >
              <MessageCircle className="w-4 h-4" />
              <span>Chat with Shopkeeper on WhatsApp</span>
            </a>
          </div>
        )}

        {/* 3. 4-Stage Vertical Order Timeline Tracker */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider pb-2 border-b border-slate-100">
            Live Order Status
          </h3>

          <div className="space-y-4 relative pl-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {/* Step 1: Placed */}
            <div className="relative">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center ring-4 ring-white">
                <Check className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Order Placed</h4>
                <p className="text-[11px] text-slate-500">Sent directly to shopkeeper's order terminal.</p>
              </div>
            </div>

            {/* Step 2: Accepted */}
            <div className="relative">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#1F5D42] text-white flex items-center justify-center ring-4 ring-white animate-pulse">
                <Store className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Awaiting Dukandaar Acceptance</h4>
                <p className="text-[11px] text-slate-500">Shopkeeper is checking live stock and accepting.</p>
              </div>
            </div>

            {/* Step 3: Packing */}
            <div className="relative opacity-50">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-slate-300 text-white flex items-center justify-center ring-4 ring-white">
                <Clock className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Packing Items</h4>
                <p className="text-[11px] text-slate-500">Fresh produce packed in your bag.</p>
              </div>
            </div>

            {/* Step 4: Out for Delivery */}
            <div className="relative opacity-50">
              <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-slate-300 text-white flex items-center justify-center ring-4 ring-white">
                <Bike className="w-3 h-3" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Out for Delivery / Ready for Pickup</h4>
                <p className="text-[11px] text-slate-500">On the way to your address.</p>
              </div>
            </div>
          </div>
        </div>

        {/* 4. Cancellation Action (Valid for 5 mins while pending) */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
          {cancelled ? (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>Order has been successfully cancelled. Reserved items were released.</span>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">Need to make changes?</h4>
                  <p className="text-[11px] text-slate-500">
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

        {/* 5. Back to Catalog Button */}
        <div className="text-center pt-2">
          <Link
            href={`/shop/${publicSlug}`}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1F5D42] hover:underline"
          >
            <span>← Return to {shop?.name || "Shop"} Catalog</span>
          </Link>
        </div>
      </main>
    </div>
  );
}
