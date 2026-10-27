"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import {
  BarChart3,
  Boxes,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageSearch,
  Settings2,
  ShoppingBag,
  Store,
  UsersRound,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { merchantApi } from "@/lib/api/merchant";

const links = [
  { href: "/merchant", label: "Overview", icon: LayoutDashboard },
  { href: "/merchant/orders", label: "Orders", icon: ClipboardList },
  { href: "/merchant/catalog", label: "Products", icon: ShoppingBag },
  { href: "/merchant/inventory", label: "Inventory", icon: Boxes },
  { href: "/merchant/customers", label: "Customers", icon: UsersRound },
  { href: "/merchant/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/merchant/settings", label: "Shop settings", icon: Settings2 },
];
const subscribeToHydration = () => () => {};
const getHydratedSnapshot = () => true;
const getServerSnapshot = () => false;

export function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
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
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f7f4] text-sm text-[#66736b]">Opening your shop workspace…</div>;
  }

  const sidebar = (
    <>
      <div className="flex h-[76px] items-center gap-3 border-b border-white/10 px-6">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#d3ef6a] text-[#193a2c]"><Store size={21} /></div>
        <div><p className="text-[15px] font-semibold tracking-tight text-white">dukana</p><p className="text-[10px] font-medium uppercase tracking-[.18em] text-[#a2b5a8]">Merchant studio</p></div>
      </div>
      <div className="px-4 pt-7">
        <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[.18em] text-[#8da398]">Workspace</p>
        <nav className="space-y-1" aria-label="Merchant navigation">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/merchant" && pathname.startsWith(`${href}/`));
            return <Link key={href} href={href} onClick={() => setMobileOpen(false)} className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] transition ${active ? "bg-[#d3ef6a] font-semibold text-[#193a2c]" : "text-[#c5d1ca] hover:bg-white/10 hover:text-white"}`}><Icon size={17} strokeWidth={active ? 2.2 : 1.8} /><span>{label}</span>{label === "Orders" && <span className={`ml-auto rounded-full px-2 py-0.5 text-[10px] ${active ? "bg-[#193a2c]/10" : "bg-white/10 text-[#dce6df]"}`}>Live</span>}</Link>;
          })}
        </nav>
      </div>
      <div className="mt-auto p-4">
        <div className="mb-3 rounded-2xl border border-white/10 bg-white/[.06] p-4">
          <div className="mb-2 flex items-center gap-2 text-[#d3ef6a]"><CircleHelp size={15} /><span className="text-xs font-semibold text-white">Need a hand?</span></div>
          <p className="text-[11px] leading-5 text-[#adbbb2]">Your shop data stays private to your merchant account.</p>
        </div>
        <button onClick={signOut} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] text-[#c5d1ca] hover:bg-white/10 hover:text-white"><LogOut size={17} />Sign out</button>
      </div>
    </>
  );

  return <div className="min-h-screen bg-[#f6f7f4] text-[#1b2a22]">
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[252px] flex-col bg-[#173b2c] lg:flex">{sidebar}</aside>
    {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button aria-label="Close menu" className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} /><aside className="relative flex h-full w-[280px] flex-col bg-[#173b2c]">{sidebar}</aside></div>}
    <div className="lg:pl-[252px]">
      <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-[#e7eae5] bg-white/90 px-4 backdrop-blur md:px-8">
        <div className="flex items-center gap-3"><button className="rounded-lg p-2 text-[#53645a] hover:bg-[#f1f4ef] lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={20} /></button><div className="hidden items-center gap-2 text-xs text-[#87938b] sm:flex"><span>Workspace</span><span>/</span><span className="font-medium text-[#33483b]">{links.find((link) => link.href === pathname)?.label ?? (pathname.endsWith("setup") ? "Shop setup" : "Account")}</span></div><div className="sm:hidden flex items-center gap-2"><PackageSearch size={17} className="text-[#284d3a]"/><span className="text-sm font-semibold">{shopQuery.data?.name ?? "Your shop"}</span></div></div>
        <div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-xs font-semibold text-[#28392e]">{shopQuery.data?.name}</p><p className="mt-0.5 text-[10px] text-[#87938b]">Shop owner</p></div><div className="grid h-9 w-9 place-items-center rounded-full bg-[#e8f0e7] text-xs font-bold text-[#315f43]">{shopQuery.data?.name?.slice(0, 1).toUpperCase() ?? "S"}</div><ChevronDown size={15} className="hidden text-[#87938b] sm:block" /></div>
      </header>
      <main className="mx-auto max-w-[1440px] px-4 py-7 md:px-8 md:py-9">{children}</main>
    </div>
  </div>;
}
