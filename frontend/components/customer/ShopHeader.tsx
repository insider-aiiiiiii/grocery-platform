"use client";

import React from "react";
import { MapPin, Phone, Bike, ShoppingBag, ShieldCheck, Languages } from "lucide-react";
import { PublicShopInfo } from "@/lib/api/customer";

interface ShopHeaderProps {
  shop: PublicShopInfo;
  language?: "en" | "hi";
  onToggleLanguage?: () => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export function ShopHeader({
  shop,
  language = "en",
  onToggleLanguage,
  searchQuery = "",
  onSearchChange,
}: ShopHeaderProps) {
  const isClosed = shop.is_temporarily_closed;
  const isHindi = language === "hi";

  const timingText = isClosed
    ? isHindi
      ? "अस्थायी रूप से बंद"
      : "Temporarily Closed"
    : shop.closing_time
    ? isHindi
      ? `${shop.closing_time.slice(0, 5)} तक खुला`
      : `Open until ${shop.closing_time.slice(0, 5)}`
    : isHindi
    ? "आज खुला है"
    : "Open Today";

  const initials = shop.name
    .split(" ")
    .map((word) => word[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase() || "SP";

  return (
    <header className="bg-gradient-to-r from-[#1F5D42] via-[#174b36] to-[#123324] rounded-b-[32px] text-white shadow-lg relative z-20 pb-5">
      {/* Closed store alert banner */}
      {isClosed && (
        <div className="bg-[#E8A33D] text-[#123324] px-4 py-2 text-xs font-bold text-center flex items-center justify-center gap-1.5 shadow-sm">
          <span>⚠️ {isHindi ? "यह दुकान अभी ऑर्डर नहीं ले रही है।" : "This store is currently not taking orders. Browsing catalog only."}</span>
        </div>
      )}

      <div className="max-w-xl mx-auto px-4 sm:px-6 pt-4 space-y-4">
        {/* Brand, Logo, Verification and Language toggle */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3.5">
            {shop.logo ? (
              <img
                src={shop.logo}
                alt={shop.name}
                className="w-14 h-14 rounded-2xl object-cover bg-white p-0.5 border border-white/20 shadow-md shrink-0"
              />
            ) : (
              <div className="w-14 h-14 rounded-2xl bg-white shadow-md flex items-center justify-center text-[#1F5D42] font-display font-bold text-xl shrink-0">
                {initials}
              </div>
            )}

            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="font-display font-bold text-2xl text-white leading-tight tracking-tight">
                  {shop.name}
                </h1>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/15 text-emerald-200 border border-white/20 backdrop-blur-sm">
                  <ShieldCheck className="w-3 h-3 text-[#E8A33D]" />
                  <span>{isHindi ? "वेरिफाइड दुकान" : "Verified Dukaan"}</span>
                </span>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-white/80 mt-1">
                <MapPin className="w-3.5 h-3.5 text-[#E8A33D] shrink-0" />
                <span className="truncate">
                  {shop.area ? `${shop.area}, ` : ""}{shop.city || "Local Market"} • {isHindi ? "15 मिनट में डिलीवरी" : "Delivery in 15 mins"}
                </span>
              </div>
            </div>
          </div>

          {/* Header Action Buttons (Language & Phone) */}
          <div className="flex items-center gap-2 shrink-0">
            {onToggleLanguage && (
              <button
                onClick={onToggleLanguage}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white text-xs font-semibold transition backdrop-blur-sm"
                title="Switch Language"
              >
                <Languages className="w-3.5 h-3.5 text-[#E8A33D]" />
                <span>{isHindi ? "English" : "हिंदी"}</span>
              </button>
            )}

            {shop.contact_number && (
              <a
                href={`tel:${shop.contact_number}`}
                className="p-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white transition backdrop-blur-sm shadow-sm"
                title={isHindi ? "दुकानदार को कॉल करें" : "Call Dukaan"}
              >
                <Phone className="w-4 h-4 text-[#E8A33D]" />
              </a>
            )}
          </div>
        </div>

        {/* Operational & Delivery Status Badges */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1 text-xs">
          {/* Timing Pill */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-semibold ${
              isClosed
                ? "bg-white/10 text-white/70 border-white/10"
                : "bg-emerald-500/20 text-emerald-200 border-emerald-400/30 backdrop-blur-sm"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isClosed ? "bg-white/40" : "bg-[#E8A33D] animate-pulse"
              }`}
            />
            <span>{timingText}</span>
          </div>

          {/* Home Delivery Pill */}
          {shop.is_home_delivery_enabled && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white border border-white/15 text-[11px] font-medium backdrop-blur-sm">
              <Bike className="w-3.5 h-3.5 text-[#E8A33D]" />
              <span>
                {parseFloat(shop.delivery_charge) === 0
                  ? isHindi
                    ? "मुफ्त डिलीवरी"
                    : "Free Delivery"
                  : `${isHindi ? "डिलीवरी" : "Delivery"} ₹${shop.delivery_charge}`}
              </span>
            </div>
          )}

          {/* Pickup Pill */}
          {shop.is_pickup_enabled && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white border border-white/15 text-[11px] font-medium backdrop-blur-sm">
              <ShoppingBag className="w-3.5 h-3.5 text-white/80" />
              <span>{isHindi ? "दुकान से पिकअप" : "Store Pickup"}</span>
            </div>
          )}
        </div>

        {/* Embedded Search Bar (matching visual board) */}
        {onSearchChange && (
          <div className="pt-1">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder={isHindi ? "आटा, बिस्कुट, साबुन खोजें…" : "Search atta, biscuit, soap…"}
                className="w-full bg-white text-[#17251e] placeholder-slate-400 rounded-2xl py-3 pl-10 pr-4 text-xs sm:text-sm font-body outline-none shadow-md focus:ring-2 focus:ring-[#E8A33D] transition"
              />
              <span className="absolute left-3.5 top-3 text-slate-400">⌕</span>
              {searchQuery && (
                <button
                  onClick={() => onSearchChange("")}
                  className="absolute right-3.5 top-3 text-xs text-slate-400 hover:text-slate-600 font-bold"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
