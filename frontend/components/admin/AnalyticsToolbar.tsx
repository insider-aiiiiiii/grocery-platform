"use client";

import React from "react";
import {
  Calendar,
  Store,
  RotateCcw,
  SlidersHorizontal,
  ChevronDown,
  X,
} from "lucide-react";
import { useAdminLang } from "./useAdminLang";
import { MerchantShopItem } from "@/components/admin/MerchantTable";

interface AnalyticsToolbarProps {
  selectedPeriod: string;
  onPeriodChange: (period: string) => void;
  selectedShopId: number | null;
  onShopChange: (shopId: number | null) => void;
  customStartDate: string;
  customEndDate: string;
  onCustomDatesChange: (start: string, end: string) => void;
  merchants: MerchantShopItem[];
  loading?: boolean;
  onRefresh: () => void;
}

export function AnalyticsToolbar({
  selectedPeriod,
  onPeriodChange,
  selectedShopId,
  onShopChange,
  customStartDate,
  customEndDate,
  onCustomDatesChange,
  merchants,
  loading = false,
  onRefresh,
}: AnalyticsToolbarProps) {
  const hi = useAdminLang() === "hi";
  const periods = [
    { id: "today", label: hi ? "आज" : "Today" },
    { id: "yesterday", label: hi ? "कल" : "Yesterday" },
    { id: "this_week", label: hi ? "इस हफ्ते" : "This Week" },
    { id: "this_month", label: hi ? "इस महीने" : "This Month" },
    { id: "custom", label: hi ? "अपनी तारीख़ें" : "Custom Range" },
  ];

  const selectedShop = merchants.find((m) => m.shopId === selectedShopId);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm space-y-3">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Left: Period Quick Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 w-full lg:w-auto">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider shrink-0">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>{hi ? "समय अवधि:" : "Time Horizon:"}</span>
          </div>

          <div className="overflow-x-auto pb-1 sm:pb-0 max-w-full">
            <div className="inline-flex rounded-md border border-slate-200 p-0.5 bg-slate-50 text-xs shrink-0">
              {periods.map((p) => {
                const isActive = selectedPeriod === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => onPeriodChange(p.id)}
                    className={`px-3 py-1 rounded text-xs font-semibold whitespace-nowrap transition-all ${
                      isActive
                        ? "bg-[#1F5D42] text-white shadow-xs"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Tenant Node Filter & Refresh */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap justify-between sm:justify-end w-full lg:w-auto">
          <div className="flex items-center gap-1.5 text-xs flex-1 sm:flex-initial min-w-0">
            <label className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 bg-slate-50 hover:bg-white rounded text-xs font-medium text-slate-700 cursor-pointer focus-within:border-[#1F5D42] focus-within:ring-1 focus-within:ring-[#1F5D42] transition-colors w-full sm:w-auto min-w-0">
              <Store className="w-3.5 h-3.5 text-[#1F5D42] shrink-0" />
              <span className="text-[11px] font-bold text-slate-400 uppercase shrink-0">{hi ? "दुकान:" : "Tenant:"}</span>
              <select
                value={selectedShopId ?? ""}
                onChange={(e) => {
                  const val = e.target.value;
                  onShopChange(val === "" ? null : parseInt(val, 10));
                }}
                className="bg-transparent text-xs font-semibold text-slate-900 outline-none cursor-pointer pr-1 truncate flex-1 min-w-0 max-w-[170px] sm:max-w-[240px]"
              >
                <option value="">{hi ? "सभी दुकानें (पूरा प्लेटफॉर्म)" : "All Merchant Nodes (Platform-wide)"}</option>
                {merchants.filter((m) => m.shopId > 0).map((m) => (
                  <option key={m.shopId} value={m.shopId}>
                    {m.shopName} ({hi ? "आईडी" : "ID"} #{m.shopId} {m.city ? `· ${m.city}` : ""})
                  </option>
                ))}
              </select>
            </label>

            {selectedShopId !== null && (
              <button
                type="button"
                onClick={() => onShopChange(null)}
                title={hi ? "दुकान फ़िल्टर हटाएं" : "Clear tenant filter"}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 border border-slate-200 shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded shadow-2xs transition-all disabled:opacity-50 shrink-0"
          >
            <RotateCcw className={`w-3.5 h-3.5 text-slate-500 ${loading ? "animate-spin text-emerald-600" : ""}`} />
            <span>{loading ? (hi ? "रीफ्रेश हो रहा है..." : "Refreshing...") : (hi ? "रीफ्रेश" : "Refresh")}</span>
          </button>
        </div>
      </div>

      {/* Conditional: Custom Date Range Selector */}
      {selectedPeriod === "custom" && (
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-3 text-xs bg-slate-50/70 p-2.5 rounded border">
          <div className="flex items-center gap-1.5 font-bold text-slate-600 text-[11px] uppercase">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
            <span>{hi ? "अपनी तारीख़ सीमा:" : "Custom Date Boundaries:"}</span>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-[11px] text-slate-500 font-medium">{hi ? "से:" : "From:"}</label>
            <input
              type="date"
              value={customStartDate}
              onChange={(e) => onCustomDatesChange(e.target.value, customEndDate)}
              className="px-2 py-1 bg-white border border-slate-200 rounded text-xs font-mono text-slate-800 outline-none focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42]"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-[11px] text-slate-500 font-medium">{hi ? "तक:" : "To:"}</label>
            <input
              type="date"
              value={customEndDate}
              onChange={(e) => onCustomDatesChange(customStartDate, e.target.value)}
              className="px-2 py-1 bg-white border border-slate-200 rounded text-xs font-mono text-slate-800 outline-none focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42]"
            />
          </div>

          {(!customStartDate || !customEndDate) && (
            <span className="text-[11px] text-amber-600 font-medium">
              {hi ? "* कृपया शुरू और अंत की दोनों तारीख़ें चुनें" : "* Please select both Start and End dates"}
            </span>
          )}
        </div>
      )}

      {/* Active Filter Pill feedback */}
      <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-500">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        <span>
          {hi ? "चालू दायरा:" : "Active Scope:"}{" "}
          <strong className="text-slate-800">
            {selectedShop ? `${selectedShop.shopName} (${hi ? "दुकान" : "Shop"} #${selectedShop.shopId})` : (hi ? "सभी दुकानों का कुल योग" : "Cross-Tenant Global Aggregate")}
          </strong>{" "}
          · {hi ? "अवधि" : "Period"}: <strong className="text-slate-800 capitalize">{hi ? (periods.find((p) => p.id === selectedPeriod)?.label ?? selectedPeriod) : selectedPeriod.replace("_", " ")}</strong>
        </span>
      </div>
    </div>
  );
}
