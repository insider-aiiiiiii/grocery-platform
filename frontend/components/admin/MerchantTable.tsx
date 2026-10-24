"use client";

import React, { useState } from "react";
import { QrCode, RefreshCw, Power, PowerOff, ShieldCheck, Clock, Ban } from "lucide-react";
import { adminApi } from "@/lib/api/admin";

export interface MerchantShopItem {
  id: number;
  shopId: number;
  shopName: string;
  merchantName: string;
  mobileNumber: string;
  city: string;
  status: "ACTIVE" | "PENDING_PASSWORD_CHANGE" | "SUSPENDED" | "DEACTIVATED";
  catalogItemsCount: number;
  monthlyVolume: string;
  publicSlug: string;
}

interface MerchantTableProps {
  merchants: MerchantShopItem[];
  onRefresh?: () => void;
  token?: string;
}

export function MerchantTable({ merchants, onRefresh, token }: MerchantTableProps) {
  const [filter, setFilter] = useState<string>("ALL");
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  const filteredMerchants = merchants.filter((m) => {
    if (filter === "ALL") return true;
    if (filter === "ACTIVE") return m.status === "ACTIVE";
    if (filter === "PENDING") return m.status === "PENDING_PASSWORD_CHANGE";
    if (filter === "SUSPENDED") return m.status === "SUSPENDED" || m.status === "DEACTIVATED";
    return true;
  });

  const handleDeactivate = async (shopId: number) => {
    setActionLoadingId(shopId);
    try {
      await adminApi.deactivateShop(shopId, token);
      onRefresh?.();
    } catch (e: any) {
      alert(`Deactivation failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReactivate = async (shopId: number) => {
    setActionLoadingId(shopId);
    try {
      await adminApi.reactivateShop(shopId, token);
      onRefresh?.();
    } catch (e: any) {
      alert(`Reactivation failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRegenerateQR = async (shopId: number) => {
    setActionLoadingId(shopId);
    try {
      await adminApi.regenerateShopQR(shopId, token);
      alert("QR code regenerated with fresh public slug.");
      onRefresh?.();
    } catch (e: any) {
      alert(`Regenerate QR failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
      {/* Table Header Control Panel */}
      <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/50">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Tenant Governance Directory</h2>
          <p className="text-xs text-slate-500">
            Active merchant nodes, authentication status, and shop security controls.
          </p>
        </div>

        {/* Filter Chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "ALL"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            All Merchants ({merchants.length})
          </button>
          <button
            onClick={() => setFilter("ACTIVE")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "ACTIVE"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setFilter("PENDING")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "PENDING"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Pending Password Reset
          </button>
          <button
            onClick={() => setFilter("SUSPENDED")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "SUSPENDED"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Suspended
          </button>
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#0F172A] text-slate-100 text-[10px] uppercase font-bold tracking-wider">
              <th className="py-2.5 px-3">Shop & Tenant ID</th>
              <th className="py-2.5 px-3">Merchant / Contact</th>
              <th className="py-2.5 px-3">Location</th>
              <th className="py-2.5 px-3">Catalog Items</th>
              <th className="py-2.5 px-3">30-Day Sales</th>
              <th className="py-2.5 px-3">Operational State</th>
              <th className="py-2.5 px-3 text-right">Governance Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredMerchants.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  No merchants found matching the selected filter.
                </td>
              </tr>
            ) : (
              filteredMerchants.map((m) => {
                const isLoading = actionLoadingId === m.shopId;
                return (
                  <tr key={m.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                      <div className="flex items-center gap-1.5">
                        <QrCode className="w-3.5 h-3.5 text-slate-400" />
                        <span>QR-{m.publicSlug.slice(0, 8).toUpperCase()}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900">{m.shopName}</div>
                      <div className="text-[11px] font-mono text-slate-500">{m.mobileNumber}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{m.city}</td>
                    <td className="py-2.5 px-3 tabular-nums font-medium text-slate-800">
                      {m.catalogItemsCount} SKUs
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900 tabular-nums">
                      {m.monthlyVolume}
                    </td>
                    <td className="py-2.5 px-3">
                      {m.status === "ACTIVE" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                          Active
                        </span>
                      ) : m.status === "PENDING_PASSWORD_CHANGE" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800">
                          <Clock className="w-3 h-3 text-amber-600" />
                          Pending Pwd
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-800">
                          <Ban className="w-3 h-3 text-red-600" />
                          Suspended
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        {/* Regenerate QR */}
                        <button
                          onClick={() => handleRegenerateQR(m.shopId)}
                          disabled={isLoading}
                          title="Rotate QR Slug"
                          className="p-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-600"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                        </button>

                        {/* Deactivate or Reactivate */}
                        {m.status === "ACTIVE" ? (
                          <button
                            onClick={() => handleDeactivate(m.shopId)}
                            disabled={isLoading}
                            className="px-2 py-1 rounded text-[10px] font-bold bg-red-50 border border-red-200 text-red-700 hover:bg-red-600 hover:text-white transition-colors"
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            onClick={() => handleReactivate(m.shopId)}
                            disabled={isLoading}
                            className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-50 border border-emerald-200 text-emerald-800 hover:bg-emerald-600 hover:text-white transition-colors"
                          >
                            Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
