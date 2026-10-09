"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { QrCode, Search, LogOut } from "lucide-react";

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

  const [username, setUsername] = useState<string>("Super Admin");

  useEffect(() => {
    const explicitUsername = localStorage.getItem("admin_username");
    if (explicitUsername && explicitUsername.trim() !== "") {
      setUsername(explicitUsername);
      return;
    }

    const storedUser = localStorage.getItem("admin_user");
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        if (parsed && typeof parsed === "object") {
          const resolved = parsed.username || parsed.email || parsed.mobile_number || (parsed.id ? `Admin #${parsed.id}` : null);
          if (resolved) {
            setUsername(resolved);
            return;
          }
        }
      } catch {
        if (storedUser.trim()) {
          setUsername(storedUser);
          return;
        }
      }
    }

    const token = localStorage.getItem("admin_access_token");
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        if (payload?.username) {
          setUsername(payload.username);
        } else if (payload?.user_id) {
          setUsername(`Admin #${payload.user_id}`);
        }
      } catch {
        // Token decode fallback
      }
    }
  }, []);

  const initials = username
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("") || "SA";

  return (
    <header className="h-14 w-full px-6 flex items-center justify-between z-40 bg-white border-b border-slate-200 shadow-sm fixed top-0 left-0 right-0">
      {/* Brand */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded bg-[#1F5D42] flex items-center justify-center text-white font-bold shadow-sm">
          <QrCode className="w-5 h-5" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-[#00452D]">DukaanQR</span>
          <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 tracking-wider">
            ADMIN
          </span>
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
        </div>
      </div>

      {/* User & Actions */}
      <div className="flex items-center gap-3">
        {/* Super Admin Profile - Clearly visible */}
        <div className="flex items-center gap-2.5 px-3 py-1 bg-slate-50 border border-slate-200 rounded-lg shadow-sm">
          <div className="w-7 h-7 rounded-full bg-[#1F5D42] text-white flex items-center justify-center font-bold text-xs shadow-inner">
            {initials}
          </div>
          <div className="text-left leading-tight">
            <div className="font-semibold text-xs text-slate-900 flex items-center gap-1.5">
              <span>{username}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" title="Online" />
            </div>
            <div className="text-[10px] text-emerald-700 font-semibold tracking-wide">Super Admin</div>
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
