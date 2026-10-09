"use client";

import React from "react";
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string;
  delta?: string;
  isPositive?: boolean;
  contextText?: string;
  icon: LucideIcon;
  accentColor?: "green" | "emerald" | "slate" | "amber";
  sparkline?: number[];
}

export function MetricCard({
  title,
  value,
  delta,
  isPositive = true,
  contextText,
  icon: Icon,
  accentColor = "green",
  sparkline,
}: MetricCardProps) {
  const colorMap = {
    green: "bg-[#1F5D42]",
    emerald: "bg-emerald-600",
    slate: "bg-slate-900",
    amber: "bg-amber-500",
  };

  return (
    <div className="bg-white border border-slate-200 rounded p-4 relative overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Top Accent Stroke */}
      <div className={`h-1 ${colorMap[accentColor]} absolute top-0 left-0 right-0`} />

      <div className="flex justify-between items-start">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{title}</span>
        <div className="p-1 rounded bg-slate-50 text-slate-700">
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-2 text-2xl font-bold text-slate-900 font-mono tracking-tight">{value}</div>

      <div className="mt-2 flex items-center justify-between text-xs">
        {delta && (
          <span
            className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold ${
              isPositive ? "text-emerald-800 bg-emerald-50" : "text-red-700 bg-red-50"
            }`}
          >
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {delta}
          </span>
        )}
        {contextText && <span className="text-[11px] text-slate-400">{contextText}</span>}
      </div>

      {/* Micro Sparkline */}
      {sparkline && sparkline.length > 0 && (
        <div className="mt-3 flex items-end gap-1 h-5 pt-1 border-t border-slate-100">
          {sparkline.map((h, i) => (
            <span
              key={i}
              style={{ height: `${h}%` }}
              className={`w-full ${colorMap[accentColor]} opacity-25 hover:opacity-100 rounded-t-sm transition-all`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
