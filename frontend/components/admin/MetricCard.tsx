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
  accentColor?: "green" | "emerald" | "slate" | "amber" | "blue";
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
    blue: "bg-sky-600",
  };

  return (
    <div className="bg-white border border-[#ddd6ca] rounded-2xl p-3 sm:p-4 relative overflow-hidden shadow-2xs hover:shadow-xs transition-all flex flex-col justify-between">
      {/* Top Accent Stroke */}
      <div className={`h-1 ${colorMap[accentColor]} absolute top-0 left-0 right-0`} />

      <div>
        <div className="flex justify-between items-start gap-1">
          <span className="text-[10px] sm:text-[11px] font-bold text-[#6d756f] uppercase tracking-wider line-clamp-1">{title}</span>
          <div className="p-1 rounded-lg bg-[#FAF8F3] text-[#123324] shrink-0 border border-[#eee9df]">
            <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </div>
        </div>

        <div className="mt-1.5 sm:mt-2 text-lg sm:text-2xl font-bold text-[#123324] font-mono tracking-tight truncate">{value}</div>
      </div>

      <div className="mt-2 flex items-center justify-between text-xs gap-1">
        {delta && (
          <span
            className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold shrink-0 ${
              isPositive ? "text-emerald-800 bg-emerald-50" : "text-red-700 bg-red-50"
            }`}
          >
            {isPositive ? <TrendingUp className="w-2.5 h-2.5 sm:w-3 sm:h-3" /> : <TrendingDown className="w-2.5 h-2.5 sm:w-3 sm:h-3" />}
            {delta}
          </span>
        )}
        {contextText && <span className="text-[10px] sm:text-[11px] text-[#869088] truncate">{contextText}</span>}
      </div>

      {/* Micro Sparkline */}
      {sparkline && sparkline.length > 0 && (
        <div className="mt-2 sm:mt-3 flex items-end gap-1 h-4 sm:h-5 pt-1 border-t border-[#eee9df]">
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
