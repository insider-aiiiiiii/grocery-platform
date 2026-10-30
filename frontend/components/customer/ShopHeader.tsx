"use client";

import React from "react";
import { Store, MapPin, Clock, ShieldCheck, Phone, Bike, ShoppingBag } from "lucide-react";
import { PublicShopInfo } from "@/lib/api/customer";

interface ShopHeaderProps {
  shop: PublicShopInfo;
}

export function ShopHeader({ shop }: ShopHeaderProps) {
  const isClosed = shop.is_temporarily_closed;
  const timingText = isClosed
    ? "Temporarily Closed"
    : shop.closing_time
    ? `Open until ${shop.closing_time.slice(0, 5)}`
    : "Open Today";

  return (
    <header className="bg-white border-b border-slate-200">
      {/* Top Banner Alert if Shop is Closed */}
      {isClosed && (
        <div className="bg-amber-500 text-slate-900 px-4 py-2 text-xs font-semibold text-center flex items-center justify-center gap-2">
          <Clock className="w-3.5 h-3.5" />
          <span>This store is currently not taking orders. Browsing catalog only.</span>
        </div>
      )}

      <div className="max-w-xl mx-auto px-4 py-4 space-y-3">
        {/* Brand & Identity Row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {shop.logo ? (
              <img
                src={shop.logo}
                alt={shop.name}
                className="w-14 h-14 rounded-2xl object-cover border border-slate-200 shadow-sm"
              />
            ) : (
              <div className="w-14 h-14 rounded-2xl bg-[#1F5D42] text-white flex items-center justify-center font-bold text-xl shadow-sm">
                <Store className="w-7 h-7 text-emerald-200" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-tight">
                  {shop.name}
                </h1>
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  Verified Dukaan
                </span>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span className="truncate">
                  {shop.area ? `${shop.area}, ` : ""}{shop.city || "Local Market"}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Contact Button */}
          {shop.contact_number && (
            <a
              href={`tel:${shop.contact_number}`}
              className="p-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors shadow-sm shrink-0"
              title="Call Dukaan"
            >
              <Phone className="w-4 h-4 text-[#1F5D42]" />
            </a>
          )}
        </div>

        {/* Operational & Delivery Status Badges */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1 text-[11px] font-medium">
          {/* Timing Pill */}
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${
              isClosed
                ? "bg-slate-100 text-slate-600 border-slate-200"
                : "bg-emerald-50 text-emerald-800 border-emerald-200"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isClosed ? "bg-slate-400" : "bg-emerald-500 animate-pulse"
              }`}
            />
            <span className="font-semibold">{timingText}</span>
          </div>

          {/* Home Delivery Pill */}
          {shop.is_home_delivery_enabled && (
            <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              <Bike className="w-3.5 h-3.5 text-[#1F5D42]" />
              <span>
                {parseFloat(shop.delivery_charge) === 0
                  ? "Free Delivery"
                  : `Delivery ₹${shop.delivery_charge}`}
              </span>
            </div>
          )}

          {/* Pickup Pill */}
          {shop.is_pickup_enabled && (
            <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              <ShoppingBag className="w-3.5 h-3.5 text-slate-600" />
              <span>Self Pickup</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
