"use client";

import React from "react";
import {
  LayoutDashboard,
  Store,
  Boxes,
  UserPlus,
  ShieldAlert,
  BarChart3,
  Settings,
  Lock,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  onOpenOnboard: () => void;
  merchantCount?: number;
  catalogCount?: number;
}

export function Sidebar({
  activeTab,
  onTabChange,
  onOpenOnboard,
  merchantCount = 142,
  catalogCount = 820,
}: SidebarProps) {
  const navItems = [
    { id: "overview", label: "Network Overview", icon: LayoutDashboard },
    { id: "merchants", label: "Tenant Directory", icon: Store, badge: merchantCount },
    { id: "catalog", label: "Master Catalog", icon: Boxes, badge: catalogCount },
    { id: "analytics", label: "Platform Analytics", icon: BarChart3 },
    { id: "security", label: "Security & Audit", icon: ShieldAlert },
    { id: "settings", label: "Console Settings", icon: Settings },
  ];

  return (
    <aside className="flex flex-col justify-between p-4 w-64 fixed left-0 top-14 bottom-0 z-30 bg-white border-r border-slate-200">
      <div className="space-y-4">
        {/* Ops Title */}
        <div className="px-2 py-1 border-b border-slate-100 pb-3">
          <div className="text-sm font-bold text-slate-900">DukaanQR Global</div>
          <div className="text-xs text-slate-500">Pan-India Network Operations</div>
        </div>

        {/* Primary CTA: Onboard New Merchant */}
        <button
          onClick={onOpenOnboard}
          className="w-full flex items-center justify-center gap-2 bg-[#1F5D42] text-white px-3 py-2 rounded font-medium text-xs shadow-sm hover:bg-[#164430] active:scale-[0.98] transition-all"
        >
          <UserPlus className="w-4 h-4" />
          <span>Onboard New Merchant</span>
        </button>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-slate-100 text-[#00452D] font-semibold"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#1F5D42]" : "text-slate-400"}`} />
                <span>{item.label}</span>
                {item.badge !== undefined && (
                  <span className="ml-auto text-[10px] bg-slate-100 px-1.5 py-0.5 rounded font-mono text-slate-500">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="border-t border-slate-100 pt-3 text-[11px] text-slate-400 flex items-center gap-1.5 px-2">
        <Lock className="w-3.5 h-3.5" />
        <span>Multi-Tenant Node Scoped</span>
      </div>
    </aside>
  );
}
