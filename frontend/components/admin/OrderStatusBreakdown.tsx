"use client";

import React from "react";
import { Activity, Clock, CheckCircle2, XCircle, PackageCheck, Truck } from "lucide-react";

interface OrderStatusDistribution {
  PENDING: number;
  ACCEPTED: number;
  PREPARING: number;
  READY: number;
  COMPLETED: number;
  REJECTED: number;
}

interface OrderStatusBreakdownProps {
  distribution?: OrderStatusDistribution;
  totalOrders: number;
}

export function OrderStatusBreakdown({
  distribution,
  totalOrders = 0,
}: OrderStatusBreakdownProps) {
  const statuses = [
    {
      key: "PENDING" as const,
      label: "Pending Acceptance",
      color: "bg-amber-500",
      lightBg: "bg-amber-50 text-amber-700 border-amber-200",
      icon: Clock,
      count: distribution?.PENDING ?? 0,
    },
    {
      key: "ACCEPTED" as const,
      label: "Accepted in Queue",
      color: "bg-sky-500",
      lightBg: "bg-sky-50 text-sky-700 border-sky-200",
      icon: Activity,
      count: distribution?.ACCEPTED ?? 0,
    },
    {
      key: "PREPARING" as const,
      label: "Packaging in Progress",
      color: "bg-indigo-500",
      lightBg: "bg-indigo-50 text-indigo-700 border-indigo-200",
      icon: Activity,
      count: distribution?.PREPARING ?? 0,
    },
    {
      key: "READY" as const,
      label: "Ready for Pickup",
      color: "bg-purple-500",
      lightBg: "bg-purple-50 text-purple-700 border-purple-200",
      icon: PackageCheck,
      count: distribution?.READY ?? 0,
    },
    {
      key: "COMPLETED" as const,
      label: "Completed & Fulfilled",
      color: "bg-emerald-500",
      lightBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: CheckCircle2,
      count: distribution?.COMPLETED ?? 0,
    },
    {
      key: "REJECTED" as const,
      label: "Rejected / Declined",
      color: "bg-rose-500",
      lightBg: "bg-rose-50 text-rose-700 border-rose-200",
      icon: XCircle,
      count: distribution?.REJECTED ?? 0,
    },
  ];

  return (
    <div className="bg-white border border-slate-200 rounded p-4 shadow-sm">
      <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-600" />
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Order Fulfillment Pipeline
          </h3>
        </div>
        <span className="text-[11px] text-slate-500">
          Total: <span className="font-bold text-slate-700 font-mono">{totalOrders}</span> orders
        </span>
      </div>

      <div className="space-y-3">
        {statuses.map((s) => {
          const Icon = s.icon;
          const percentage = totalOrders > 0 ? Math.round((s.count / totalOrders) * 100) : 0;

          return (
            <div key={s.key} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className={`p-1 rounded border text-[10px] ${s.lightBg}`}>
                    <Icon className="w-3 h-3" />
                  </span>
                  <span className="font-semibold text-slate-700">{s.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-slate-900">{s.count}</span>
                  <span className="text-[10px] text-slate-400 font-mono w-9 text-right">
                    {percentage}%
                  </span>
                </div>
              </div>

              {/* Visual Progress Bar */}
              <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${s.color} transition-all duration-300 rounded-full`}
                  style={{ width: `${Math.max(percentage, s.count > 0 ? 3 : 0)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
