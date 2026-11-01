"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Store, Search, LogOut, Languages } from "lucide-react";

interface NavbarProps {
  adminEmail?: string;
  onSearch?: (query: string) => void;
}

export function Navbar({ adminEmail = "admin@platform.com", onSearch }: NavbarProps) {
  const router = useRouter();
  const [lang, setLang] = useState<"en" | "hi">("en");

  useEffect(() => {
    const saved = localStorage.getItem("portal_language") as "en" | "hi" | null;
    if (saved === "hi" || saved === "en") setLang(saved);

    const onStorageChange = () => {
      const current = localStorage.getItem("portal_language") as "en" | "hi" | null;
      if (current === "hi" || current === "en") setLang(current);
    };
    window.addEventListener("portal-lang-changed", onStorageChange);
    return () => window.removeEventListener("portal-lang-changed", onStorageChange);
  }, []);

  const toggleLanguage = () => {
    const next = lang === "hi" ? "en" : "hi";
    setLang(next);
    localStorage.setItem("portal_language", next);
    window.dispatchEvent(new Event("portal-lang-changed"));
  };

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
    <header className="h-14 w-full px-6 flex items-center justify-between z-40 bg-[#123324] border-b border-[#1F5D42]/30 shadow-sm fixed top-0 left-0 right-0">
      {/* Brand */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-[#E8A33D] flex items-center justify-center text-[#123324] font-bold shadow-xs">
          <Store className="w-5 h-5" />
        </div>
        <div>
          <span className="text-base font-display font-bold tracking-tight text-white">Dukandaar</span>
          <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#2a684c] text-emerald-200 border border-[#3e8464] tracking-wider">
            ADMIN
          </span>
        </div>
      </div>

      {/* Global Tenancy Search Bar */}
      <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#a2b5a8]" />
          <input
            type="text"
            placeholder={lang === "hi" ? "ग्लोबल सर्च (दुकान ID, मोबाइल, SKU, मर्चेंट)..." : "Global search (Shop ID, Mobile, SKU, Merchant)..."}
            onChange={(e) => onSearch?.(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-white/10 text-white placeholder-white/50 border border-white/15 rounded-xl focus:bg-white/15 focus:border-[#E8A33D] focus:ring-1 focus:ring-[#E8A33D] transition-all outline-none"
          />
        </div>
      </div>

      {/* User & Actions */}
      <div className="flex items-center gap-3">
        {/* Language Switcher */}
        <button
          onClick={toggleLanguage}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-white/10 hover:bg-white/20 rounded-xl transition-colors border border-white/20 backdrop-blur-xs"
          title="Switch Language / भाषा बदलें"
        >
          <Languages className="w-3.5 h-3.5 text-[#E8A33D]" />
          <span>{lang === "hi" ? "हिंदी" : "English"}</span>
        </button>

        {/* Super Admin Profile */}
        <div className="flex items-center gap-2.5 px-3 py-1 bg-white/10 border border-white/15 rounded-xl shadow-2xs">
          <div className="w-7 h-7 rounded-full bg-[#E8A33D] text-[#123324] flex items-center justify-center font-bold text-xs shadow-inner">
            {initials}
          </div>
          <div className="text-left leading-tight">
            <div className="font-semibold text-xs text-white flex items-center gap-1.5">
              <span>{username}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" title="Online" />
            </div>
            <div className="text-[10px] text-[#a2b5a8] font-medium tracking-wide">
              {lang === "hi" ? "सुपर एडमिन" : "Super Admin"}
            </div>
          </div>
        </div>

        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-[#b9c9c0] hover:text-white hover:bg-red-500/20 border border-white/15 rounded-xl transition-colors"
          title="Logout from Super Admin session"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{lang === "hi" ? "लॉगआउट" : "Logout"}</span>
        </button>
      </div>
    </header>
  );
}
