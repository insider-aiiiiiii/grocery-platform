"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { signOutAdmin } from "@/lib/api/client";
import {
  LayoutDashboard,
  Store,
  Boxes,
  ShieldAlert,
  BarChart3,
  Settings,
  Lock,
  Megaphone,
  LogOut,
  Languages,
  X,
  UserCheck,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  merchantCount?: number;
  catalogCount?: number;
  campaignCount?: number;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({
  activeTab,
  onTabChange,
  merchantCount = 0,
  catalogCount = 0,
  campaignCount = 0,
  mobileOpen = false,
  onCloseMobile,
}: SidebarProps) {
  const router = useRouter();
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [username, setUsername] = useState<string>("Super Admin");

  useEffect(() => {
    const saved = localStorage.getItem("super_admin_language") as "en" | "hi" | null;
    if (saved === "hi" || saved === "en") setLang(saved);

    const onStorageChange = () => {
      const current = localStorage.getItem("super_admin_language") as "en" | "hi" | null;
      if (current === "hi" || current === "en") setLang(current);
    };
    window.addEventListener("admin-lang-changed", onStorageChange);
    return () => window.removeEventListener("admin-lang-changed", onStorageChange);
  }, []);

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
        if (parsed?.username || parsed?.email) {
          setUsername(parsed.username || parsed.email);
          return;
        }
      } catch {
        // Fallback
      }
    }
  }, []);

  const toggleLanguage = () => {
    const next = lang === "hi" ? "en" : "hi";
    setLang(next);
    localStorage.setItem("super_admin_language", next);
    window.dispatchEvent(new Event("admin-lang-changed"));
  };

  const handleLogout = async () => {
    await signOutAdmin();
    router.push("/admin/login");
  };

  const navItems = [
    { id: "overview", labelEn: "Network Overview", labelHi: "नेटवर्क अवलोकन", icon: LayoutDashboard },
    { id: "merchants", labelEn: "Tenant Directory", labelHi: "दुकानदार डायरेक्टरी", icon: Store, badge: merchantCount },
    { id: "catalog", labelEn: "Master Catalog", labelHi: "मास्टर कैटलॉग", icon: Boxes, badge: catalogCount },
    { id: "campaigns", labelEn: "Marketing Campaigns", labelHi: "मार्केटिंग अभियान", icon: Megaphone, badge: campaignCount },
    { id: "analytics", labelEn: "Platform Analytics", labelHi: "प्लेटफॉर्म विश्लेषण", icon: BarChart3 },
    { id: "settings", labelEn: "Console Settings", labelHi: "कंसोल सेटिंग्स", icon: Settings },
  ];

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between p-4">
      <div className="space-y-4">
        {/* Brand Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4 px-2">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#E8A33D] text-[#123324] font-bold shadow-sm shrink-0">
              <Store size={20} />
            </div>
            <div>
              <p className="font-display text-xl font-bold tracking-tight text-white leading-tight">
                Dukandaar
              </p>
              <p className="text-[10px] font-medium uppercase tracking-[.18em] text-[#a2b5a8]">
                {lang === "hi" ? "सुपर एडमिन कंसोल" : "Super Admin Console"}
              </p>
            </div>
          </div>
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden text-[#a2b5a8] hover:text-white p-1 rounded-lg"
              aria-label={lang === "hi" ? "मेन्यू बंद करें" : "Close menu"}
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation Section */}
        <div>
          <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-[.18em] text-[#7d9688]">
            {lang === "hi" ? "प्रशासन नेविगेशन" : "Admin Navigation"}
          </p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onTabChange(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition ${isActive
                      ? "bg-[#2a684c] text-white shadow-xs border border-[#3e8464]"
                      : "text-[#b9c9c0] hover:bg-white/10 hover:text-white"
                    }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-[#E8A33D]" : "text-[#7d9688]"}`} />
                  <span>{lang === "hi" ? item.labelHi : item.labelEn}</span>
                  {item.badge !== undefined && (
                    <span
                      className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${isActive ? "bg-[#123324] text-[#E8A33D]" : "bg-white/10 text-[#dce6df]"
                        }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer User Profile & Sign Out (Matching Merchant Portal) */}
      <div className="border-t border-white/10 pt-4 space-y-3">
        {/* Admin User Card */}
        {/* <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-white/[0.06] border border-white/10">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#E8A33D] text-[#123324] font-bold text-xs shrink-0">
            <UserCheck size={16} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-white truncate">{username}</p>
            <p className="text-[10px] text-[#a2b5a8] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
              <span>{lang === "hi" ? "सुपर एडमिन" : "Super Admin"}</span>
            </p>
          </div>
        </div> */}

        {/* Sign Out Button */}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#f8a8a8] hover:bg-red-500/20 hover:text-white transition"
        >
          <LogOut size={16} />
          <span>{lang === "hi" ? "लॉग आउट करें" : "Sign out"}</span>
        </button>

        <div className="text-[10px] text-[#7d9688] flex items-center gap-1.5 px-3 pt-1">
          <Lock className="w-3 h-3 text-[#E8A33D]" />
          <span>{lang === "hi" ? "मल्टी-टेनेंट सुरक्षा सक्रिय" : "Multi-Tenant Node Secured"}</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:flex flex-col fixed inset-y-0 left-0 z-40 w-[240px] bg-[#123324] border-r border-[#1F5D42]/30">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-xs"
            onClick={onCloseMobile}
          />
          <aside className="relative flex h-full w-[280px] max-w-[85vw] flex-col bg-[#123324] shadow-2xl">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}
