"use client";

import { useRouter } from "next/navigation";
import { QrCode, Search, Bell, Activity, ShieldAlert, UserCheck, LogOut } from "lucide-react";

interface NavbarProps {
  adminEmail?: string;
  onSearch?: (query: string) => void;
}

export function Navbar({ adminEmail = "admin@platform.com", onSearch }: NavbarProps) {
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem("admin_access_token");
    localStorage.removeItem("admin_refresh_token");
    localStorage.removeItem("admin_user");
    localStorage.removeItem("admin_remember");
    router.push("/admin/login");
  };

  return (
    <header className="h-14 w-full px-6 flex items-center justify-between z-40 bg-white border-b border-slate-200 shadow-sm fixed top-0 left-0 right-0">
      {/* Brand & Live Status */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-[#1F5D42] flex items-center justify-center text-white font-bold shadow-sm">
            <QrCode className="w-5 h-5" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-[#00452D]">DukaanQR</span>
            <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 tracking-wider">
              GOVERNANCE
            </span>
          </div>
        </div>

        {/* Live Heartbeat Status Pill */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full text-xs text-slate-600">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
          </span>
          <span className="text-slate-800 font-semibold">System Operational • 99.98% uptime</span>
          <span className="text-slate-300">|</span>
          <span className="font-mono text-slate-500">DB: 18ms</span>
        </div>
      </div>

      {/* Global Tenancy Search Bar */}
      <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Global search (Shop ID, Mobile, SKU, Merchant)..."
            onChange={(e) => onSearch?.(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] transition-all outline-none"
          />
          <kbd className="absolute right-2.5 top-2 px-1.5 py-0.5 text-[9px] font-mono text-slate-400 bg-white border border-slate-200 rounded">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* User & Actions */}
      <div className="flex items-center gap-3">
        <button
          className="p-1.5 rounded text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
          title="Platform Health"
        >
          <Activity className="w-4 h-4" />
        </button>
        <button
          className="p-1.5 rounded text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors relative"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-600 rounded-full"></span>
        </button>

        <div className="h-6 w-px bg-slate-200"></div>

        {/* Super Admin Profile */}
        <div className="flex items-center gap-2 pl-1">
          <div className="w-8 h-8 rounded-full border border-[#1F5D42] bg-[#0F172A] text-white flex items-center justify-center font-bold text-xs">
            SA
          </div>
          <div className="hidden xl:block text-left text-xs">
            <div className="font-semibold text-slate-900 leading-tight">Super Admin</div>
            <div className="text-[10px] text-slate-500 leading-tight">{adminEmail}</div>
          </div>
        </div>

        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:text-red-700 hover:bg-red-50 border border-slate-200 rounded-md transition-colors"
          title="Logout from Super Admin session"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
