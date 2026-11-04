"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import {
  BarChart3,
  Boxes,
  ClipboardList,
  ExternalLink,
  LogOut,
  Menu,
  QrCode,
  Settings2,
  ShoppingBag,
  Store,
  UsersRound,
  Languages,
  Receipt,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { merchantApi } from "@/lib/api/merchant";

const links = [
  { href: "/merchant", labelEn: "My QR", labelHi: "मेरा QR", icon: QrCode },
  { href: "/merchant/inventory", labelEn: "Inventory", labelHi: "स्टॉक व बैच", icon: Boxes },
  { href: "/merchant/orders", labelEn: "Live Orders", labelHi: "लाइव ऑर्डर्स", icon: ClipboardList },
  { href: "/merchant/analytics", labelEn: "Analytics", labelHi: "बिक्री रिपोर्ट", icon: BarChart3 },
  { href: "/merchant/catalog", labelEn: "Products", labelHi: "कैटलॉग प्रोडक्ट्स", icon: ShoppingBag },
  { href: "/merchant/customers", labelEn: "Orders History", labelHi: "ऑर्डर इतिहास", icon: Receipt },
  { href: "/merchant/settings", labelEn: "Shop settings", labelHi: "दुकान सेटिंग्स", icon: Settings2 },
];

const subscribeToHydration = () => () => {};
const getHydratedSnapshot = () => true;
const getServerSnapshot = () => false;

export function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
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

  const ready = useSyncExternalStore(subscribeToHydration, getHydratedSnapshot, getServerSnapshot);
  const shopQuery = useQuery({
    queryKey: ["merchant", "shop"],
    queryFn: merchantApi.shop,
    retry: false,
    enabled: ready,
  });

  useEffect(() => {
    const expire = () => router.replace("/merchant/login");
    window.addEventListener("merchant-session-expired", expire);
    return () => window.removeEventListener("merchant-session-expired", expire);
  }, [router]);

  useEffect(() => {
    const access = sessionStorage.getItem("merchant_access_token");
    const mustChange = sessionStorage.getItem("merchant_must_change_password") === "true";
    if (!access) {
      router.replace("/merchant/login");
      return;
    }
    if (mustChange && pathname !== "/merchant/change-password") {
      router.replace("/merchant/change-password");
      return;
    }
    if (!mustChange && pathname === "/merchant/change-password") {
      router.replace("/merchant");
      return;
    }
  }, [pathname, router]);

  useEffect(() => {
    if (!ready || shopQuery.isLoading || pathname === "/merchant/setup") return;
    if (shopQuery.isError) {
      const status = (shopQuery.error as { response?: { status?: number } })?.response?.status;
      if (status === 404) router.replace("/merchant/setup");
    }
  }, [ready, shopQuery.isLoading, shopQuery.isError, shopQuery.error, pathname, router]);

  const signOut = async () => {
    try {
      await merchantApi.logout();
    } finally {
      sessionStorage.removeItem("merchant_access_token");
      sessionStorage.removeItem("merchant_refresh_token");
      sessionStorage.removeItem("merchant_must_change_password");
      router.replace("/merchant/login");
    }
  };

  const accountOnlyRoute = pathname === "/merchant/setup" || pathname === "/merchant/change-password";
  if (!ready || ((shopQuery.isLoading || shopQuery.isError) && !accountOnlyRoute)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F6F0E6] text-sm text-[#123324] font-medium font-sans">
        <div className="flex items-center gap-2">
          <Store className="w-5 h-5 animate-pulse text-[#1F5D42]" />
          <span>Opening your shop workspace…</span>
        </div>
      </div>
    );
  }

  const shop = shopQuery.data;

  const sidebar = (
    <>
      {/* Brand Header */}
      <div className="flex h-[76px] items-center gap-3 border-b border-white/10 px-6">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#E8A33D] text-[#123324] font-bold shadow-sm">
          <Store size={20} />
        </div>
        <div>
          <p className="font-display text-xl font-bold tracking-tight text-white leading-tight">
            Dukandaar
          </p>
          <p className="text-[10px] font-medium uppercase tracking-[.18em] text-[#a2b5a8]">
            Merchant Workspace
          </p>
        </div>
      </div>

      {/* Navigation */}
      <div className="px-4 pt-6">
        <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[.18em] text-[#7d9688]">
          {lang === "hi" ? "नेविगेशन" : "Navigation"}
        </p>
        <nav className="space-y-1" aria-label="Merchant navigation">
          {links.map(({ href, labelEn, labelHi, icon: Icon }) => {
            const active =
              href === "/merchant"
                ? pathname === "/merchant"
                : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition ${
                  active
                    ? "bg-[#2a684c] text-white shadow-sm border border-[#3e8464]"
                    : "text-[#b9c9c0] hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon size={16} strokeWidth={active ? 2.4 : 1.8} className={active ? "text-[#E8A33D]" : ""} />
                <span>{lang === "hi" ? labelHi : labelEn}</span>
                {labelEn === "Orders" && (
                  <span
                    className={`ml-auto rounded-full px-2 py-0.5 text-[10px] ${
                      active ? "bg-[#123324] text-[#E8A33D]" : "bg-white/10 text-[#dce6df]"
                    }`}
                  >
                    {lang === "hi" ? "लाइव" : "Live"}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info & Sign out */}
      <div className="mt-auto p-4">
        {shop?.public_slug && (
          <div className="mb-3 rounded-2xl border border-white/10 bg-white/[.06] p-3 text-xs">
            <div className="mb-1 flex items-center justify-between text-white font-medium">
              <span className="text-[11px] text-[#a2b5a8]">Customer View</span>
              <span className="text-[9px] bg-[#E8A33D]/20 text-[#E8A33D] px-1.5 py-0.5 rounded font-mono font-bold">
                Live
              </span>
            </div>
            <Link
              href={`/shop/${shop.public_slug}`}
              target="_blank"
              className="inline-flex items-center gap-1.5 text-xs text-[#E8A33D] hover:underline font-medium mt-1"
            >
              <span>Open customer store</span>
              <ExternalLink size={12} />
            </Link>
          </div>
        )}

        <button
          onClick={signOut}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold text-[#b9c9c0] hover:bg-white/10 hover:text-white transition"
        >
          <LogOut size={16} />
          <span>Sign out</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[#F6F0E6] text-[#17251e] font-sans">
      {/* Sidebar Desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[240px] flex-col bg-[#123324] lg:flex border-r border-[#1F5D42]/30">
        {sidebar}
      </aside>

      {/* Mobile Sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Close menu"
            className="absolute inset-0 bg-black/50 backdrop-blur-xs"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-[270px] flex-col bg-[#123324] shadow-2xl">
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main Container */}
      <div className="lg:pl-[240px]">
        {/* Top Navbar */}
        <header className="sticky top-0 z-30 flex h-[70px] items-center justify-between border-b border-[#ddd6ca] bg-white/80 px-4 backdrop-blur md:px-8">
          <div className="flex items-center gap-3">
            <button
              className="rounded-lg p-2 text-[#5e665f] hover:bg-[#eee9df] lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div>
              <h2 className="font-display font-bold text-lg md:text-xl text-[#123324] leading-tight">
                {shop?.name ?? "Sharma Kirana"}
              </h2>
              <p className="text-[11px] text-[#6d756f]">
                My shop • {shop?.city ?? "Local"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Language Switcher */}
            <button
              onClick={toggleLanguage}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#ddd6ca] bg-white hover:bg-[#eee9df] text-xs font-semibold text-[#123324] transition shadow-2xs"
              title="Switch Language / भाषा बदलें"
            >
              <Languages size={14} className="text-[#1F5D42]" />
              <span>{lang === "hi" ? "English" : "हिंदी"}</span>
            </button>

            {shop?.public_slug && (
              <Link
                href={`/shop/${shop.public_slug}`}
                target="_blank"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#E8A33D] hover:bg-[#d6902b] text-[#123324] font-bold text-xs shadow-xs transition"
              >
                <span>{lang === "hi" ? "ग्राहक स्टोर खोलें" : "View My Store"}</span>
                <ExternalLink size={12} />
              </Link>
            )}

            <div className="flex items-center gap-2 pl-2 border-l border-[#ddd6ca]">
              <div className="grid h-8 w-8 place-items-center rounded-full bg-[#1F5D42] text-xs font-bold text-white shadow-xs">
                {shop?.name?.slice(0, 1).toUpperCase() ?? "S"}
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="mx-auto max-w-[1400px] p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
