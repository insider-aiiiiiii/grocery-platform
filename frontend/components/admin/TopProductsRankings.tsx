"use client";

import React from "react";
import { Package, TrendingUp, Sparkles } from "lucide-react";

export interface TopProductItem {
  product_id: number;
  variant_id: number | null;
  product_name: string;
  variant_name: string;
  sku: string;
  units_sold: string;
  total_revenue: string;
}

interface TopProductsRankingsProps {
  products?: TopProductItem[];
}

export function TopProductsRankings({ products = [] }: TopProductsRankingsProps) {
  const displayProducts = products;

  return (
    <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Network Top Performing SKUs
          </h3>
        </div>
        <span className="text-[11px] text-slate-500">Cross-Tenant Sales Telemetry</span>
      </div>

      <div className="divide-y divide-slate-100">
        {displayProducts.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            No product sales telemetry recorded yet.
          </div>
        ) : (
          displayProducts.map((p, idx) => (
            <div key={`${p.product_id}-${p.variant_id ?? idx}`} className="p-3.5 flex items-center justify-between hover:bg-slate-50/70 transition-colors">
              <div className="flex items-center gap-3">
                <span className="w-5 text-center text-xs font-mono font-bold text-slate-400">
                  #{idx + 1}
                </span>
                <div className="p-2 bg-slate-100 text-slate-700 rounded">
                  <Package className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">{p.product_name}</div>
                  <div className="text-[11px] text-slate-500 flex items-center gap-2">
                    <span>{p.variant_name}</span>
                    <span>•</span>
                    <span className="font-mono text-slate-400">{p.sku}</span>
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-xs font-mono font-bold text-[#1F5D42]">
                  ₹{parseFloat(p.total_revenue).toLocaleString("en-IN")}
                </div>
                <div className="text-[10px] text-slate-500 flex items-center gap-1 justify-end">
                  <TrendingUp className="w-3 h-3 text-emerald-600" />
                  <span>{p.units_sold} units sold</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
