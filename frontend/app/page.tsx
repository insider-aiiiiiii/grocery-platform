"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Boxes,
  Languages,
  MessageCircle,
  ShieldCheck,
  Sparkles,
  Store,
  CheckCircle2,
} from "lucide-react";

export default function Home() {
  const [lang, setLang] = useState<"en" | "hi">("en");

  useEffect(() => {
    const saved = localStorage.getItem("portal_language") as "en" | "hi" | null;
    if (saved === "hi" || saved === "en") {
      setLang(saved);
    }

    const onStorageChange = () => {
      const current = localStorage.getItem("portal_language") as "en" | "hi" | null;
      if (current === "hi" || current === "en") {
        setLang(current);
      }
    };
    window.addEventListener("portal-lang-changed", onStorageChange);
    return () => window.removeEventListener("portal-lang-changed", onStorageChange);
  }, []);

  const toggleLanguage = () => {
    const nextLang = lang === "en" ? "hi" : "en";
    setLang(nextLang);
    localStorage.setItem("portal_language", nextLang);
    window.dispatchEvent(new Event("portal-lang-changed"));
  };

  const t = {
    platformTitle: lang === "hi" ? "दुकानदार" : "Dukandaar",
    platformSubtitle: lang === "hi" ? "हाइपरलोकल ग्रॉसरी प्लेटफॉर्म" : "Grocery Platform",
    platformActive: lang === "hi" ? "प्लेटफॉर्म सक्रिय" : "Platform Active",
    signIn: lang === "hi" ? "लॉगिन करें" : "Sign In",
    badge: lang === "hi" ? "स्थानीय किराना दुकानों के लिए आधुनिक मंच · आपकी अपनी दुकान" : "Tools for local grocery · आपकी अपनी दुकान",
    heroHeading1: lang === "hi" ? "आपकी दुकान," : "Your shop,",
    heroHeading2: lang === "hi" ? "आसानी से डिजिटल।" : "running smoothly.",
    heroDescription:
      lang === "hi"
        ? "उत्पादों को प्रबंधित करें, इन्वेंटरी स्टॉक संभालें और व्हाट्सएप ग्राहकों के ऑर्डर्स को एक शांत, व्यवस्थित वर्कस्पेस से पूरा करें।"
        : "Manage products, stock inventory, and fulfill WhatsApp customer orders from one calm, unified workspace designed for neighborhood retail.",
    portalMerchantTitle: lang === "hi" ? "व्यापारी वर्कस्पेस" : "Merchant Workspace",
    portalMerchantDesc:
      lang === "hi"
        ? "ऑर्डर्स, मास्टर कैटलॉग, इन्वेंटरी और दुकान की सेटिंग्स"
        : "Orders, catalog, inventory & shop settings",
    portalAdminTitle: lang === "hi" ? "सुपर एडमिन कंसोल" : "Super Admin Console",
    portalAdminDesc:
      lang === "hi"
        ? "सभी दुकानें, प्रोडक्ट लिस्ट और ऑफ़र एक ही जगह से संभालें"
        : "Manage all shops, the product catalog and offers in one place",
    dailyOpsTitle: lang === "hi" ? "दैनिक संचालन" : "Daily Operations",
    dailyOpsSubtitle: lang === "hi" ? "सब कुछ एक ही जगह पर" : "Everything in one place",
    orderDeskTitle: lang === "hi" ? "ऑर्डर डेस्क" : "Order Desk",
    orderDeskHeadline: lang === "hi" ? "लाइव व्हाट्सएप ऑर्डर्स" : "Live WhatsApp Orders",
    orderDeskStat: lang === "hi" ? "94% समय पर पूरे किए गए" : "94% fulfilled on time",
    inventoryTitle: lang === "hi" ? "इन्वेंटरी" : "Inventory",
    inventoryHeadline: lang === "hi" ? "स्टॉक व शेल्फ स्थिति" : "Stock & Shelf Health",
    inventoryStat: lang === "hi" ? "स्वचालित लो-स्टॉक अलर्ट" : "Auto low-stock alerts",
    modularOpsTitle: lang === "hi" ? "विश्वसनीय स्थानीय संचालन" : "Focused Local Operations",
    feature1: lang === "hi" ? "दुकान प्रोफाइल व होम डिलीवरी नियंत्रण" : "Shop Profile & Home Delivery Controls",
    feature2: lang === "hi" ? "मास्टर कैटलॉग व बारकोड खोज" : "Master Catalog Curation & Barcode Lookup",
    feature3: lang === "hi" ? "क्यूआर कोड स्टोरफ्रंट व व्हाट्सएप कार्ट" : "QR Code Storefront & WhatsApp Cart",
    footerText: lang === "hi" ? "· ग्रॉसरी ऑर्डरिंग व व्यापारी प्रबंधन" : "· Grocery Ordering & Merchant Management",
    merchantLogin: lang === "hi" ? "व्यापारी लॉगिन" : "Merchant Login",
    superAdmin: lang === "hi" ? "सुपर एडमिन" : "Super Admin",
  };

  return (
    <main className="min-h-screen bg-[#F6F0E6] text-[#17251e] font-body selection:bg-[#E8A33D]/30 selection:text-[#123324]">
      {/* Background Ambient Glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-32 -left-24 h-96 w-96 rounded-full bg-[#1F5D42]/10 blur-3xl" />
        <div className="absolute top-1/4 -right-20 h-96 w-96 rounded-full bg-[#E8A33D]/15 blur-3xl" />
        <div className="absolute -bottom-24 left-1/3 h-96 w-96 rounded-full bg-[#1F5D42]/5 blur-3xl" />
      </div>

      {/* Top Header */}
      <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 sm:px-10">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#123324] text-[#E8A33D] shadow-md border border-[#1F5D42]/40">
            <Store size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-2xl font-bold tracking-tight text-[#123324] leading-tight">
                {t.platformTitle}
              </span>
            </div>
            <p className="text-[10px] font-semibold uppercase tracking-[.18em] text-[#6d756f]">
              {t.platformSubtitle}
            </p>
          </div>
        </div>

        {/* Right Header Navigation & Pill */}
        <div className="flex items-center gap-3">
          {/* Dual Language Switcher Button */}
          <button
            onClick={toggleLanguage}
            className="inline-flex items-center gap-1.5 rounded-xl border border-[#ddd6ca] bg-[#FFFDF8] px-3.5 py-1.5 text-xs font-semibold text-[#123324] shadow-2xs transition hover:bg-[#eee8dc]"
            title="Switch Language / भाषा बदलें"
          >
            <Languages size={14} className="text-[#1F5D42]" />
            <span>{lang === "hi" ? "English" : "हिंदी"}</span>
          </button>

          <span className="hidden sm:inline-flex items-center gap-2 rounded-full border border-[#ddd6ca] bg-[#FFFDF8] px-3.5 py-1.5 text-xs font-semibold text-[#5e665f] shadow-2xs">
            <span className="h-2 w-2 rounded-full bg-[#E8A33D] animate-pulse" />
            <span>{t.platformActive}</span>
          </span>

          <Link
            href="/merchant/login"
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#1F5D42] px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-[#164732] active:scale-[0.98]"
          >
            <span>{t.signIn}</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>
      </header>

      {/* Hero & Portal Grid Section */}
      <section className="relative z-10 mx-auto grid min-h-[calc(100vh-92px)] max-w-7xl items-center gap-12 px-6 py-8 sm:px-10 lg:grid-cols-[1fr_.9fr] lg:py-14">
        {/* Left Column: Headlines & Portal Links */}
        <div>
          {/* Badge */}
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#cbe1d5] bg-[#e7f2eb] px-3.5 py-1.5 text-xs font-semibold text-[#1F5D42] shadow-2xs">
            <Sparkles size={13} className="text-[#E8A33D]" />
            <span>{t.badge}</span>
          </div>

          {/* Title */}
          <h1 className="max-w-xl font-display text-5xl font-bold leading-[1.08] tracking-tight text-[#123324] sm:text-6xl">
            {t.heroHeading1} <br />
            <span className="text-[#E8A33D]">{t.heroHeading2}</span>
          </h1>

          {/* Description */}
          <p className="mt-5 max-w-lg text-sm sm:text-base leading-relaxed text-[#5e665f]">
            {t.heroDescription}
          </p>

          {/* Quick Portal Cards Grid */}
          <div className="mt-9 grid gap-3 sm:grid-cols-2">
            {/* 1. Merchant Workspace */}
            <Link
              href="/merchant/login"
              className="group relative flex min-h-[155px] flex-col justify-between overflow-hidden rounded-2xl bg-[#123324] p-5 text-white border border-[#1F5D42]/40 shadow-sm transition hover:bg-[#16402d] hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#E8A33D] text-[#123324] shadow-xs">
                  <Store size={20} />
                </span>
                <span className="rounded-full bg-white/10 p-1.5 text-white/70 transition group-hover:bg-[#E8A33D] group-hover:text-[#123324] group-hover:-translate-y-0.5 group-hover:translate-x-0.5">
                  <ArrowUpRight size={16} />
                </span>
              </div>
              <div>
                <p className="font-display text-base font-bold text-white tracking-tight">
                  {t.portalMerchantTitle}
                </p>
                <p className="mt-1 text-xs text-[#b9cac0]">
                  {t.portalMerchantDesc}
                </p>
              </div>
            </Link>

            {/* 2. Platform Administration */}
            <Link
              href="/admin/login"
              className="group relative flex min-h-[155px] flex-col justify-between overflow-hidden rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-5 text-[#17251e] shadow-2xs transition hover:border-[#1F5D42] hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f2eb] text-[#1F5D42]">
                  <ShieldCheck size={20} />
                </span>
                <span className="rounded-full bg-[#f4f1ea] p-1.5 text-[#6d756f] transition group-hover:bg-[#1F5D42] group-hover:text-white group-hover:-translate-y-0.5 group-hover:translate-x-0.5">
                  <ArrowUpRight size={16} />
                </span>
              </div>
              <div>
                <p className="font-display text-base font-bold text-[#123324] tracking-tight">
                  {t.portalAdminTitle}
                </p>
                <p className="mt-1 text-xs text-[#6d756f]">
                  {t.portalAdminDesc}
                </p>
              </div>
            </Link>
          </div>
        </div>

        {/* Right Column: Live Operations Desk Preview Widget */}
        <div className="relative mx-auto w-full max-w-[500px]">
          {/* Decorative Card Container */}
          <div className="relative rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 shadow-xl sm:p-7">
            {/* Card Header */}
            <div className="flex items-center justify-between border-b border-[#eee9df] pb-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#8a968d]">
                  {t.dailyOpsTitle}
                </p>
                <p className="font-display text-xl font-bold tracking-tight text-[#123324] mt-0.5">
                  {t.dailyOpsSubtitle}
                </p>
              </div>
              <span className="rounded-full bg-[#e7f2eb] border border-[#cbe1d5] px-3 py-1 text-[11px] font-bold text-[#1F5D42]">
                Dukandaar UI
              </span>
            </div>

            {/* Quick Stats Grid */}
            <div className="mt-5 grid grid-cols-2 gap-3">
              {/* Order Desk Preview */}
              <div className="rounded-2xl border border-[#cbe1d5]/80 bg-[#e7f2eb]/60 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#1F5D42]">
                    {t.orderDeskTitle}
                  </p>
                  <MessageCircle size={13} className="text-[#1F5D42]" />
                </div>
                <p className="mt-3 font-display text-sm font-bold text-[#123324]">
                  {t.orderDeskHeadline}
                </p>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/80 border border-[#cbe1d5]">
                  <div className="h-full w-3/4 rounded-full bg-[#1F5D42]" />
                </div>
                <p className="mt-1.5 text-[10px] font-medium text-[#5e665f]">
                  {t.orderDeskStat}
                </p>
              </div>

              {/* Inventory Tracker Preview */}
              <div className="rounded-2xl border border-[#ddd6ca] bg-[#F6F0E6] p-4">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#9b4d16]">
                    {t.inventoryTitle}
                  </p>
                  <Boxes size={13} className="text-[#E8A33D]" />
                </div>
                <p className="mt-3 font-display text-sm font-bold text-[#123324]">
                  {t.inventoryHeadline}
                </p>
                <div className="mt-3 flex gap-1">
                  <span className="h-2 w-1/2 rounded-full bg-[#E8A33D]" />
                  <span className="h-2 w-1/4 rounded-full bg-[#1F5D42]" />
                  <span className="h-2 w-1/4 rounded-full bg-[#ddd6ca]" />
                </div>
                <p className="mt-1.5 text-[10px] font-medium text-[#5e665f]">
                  {t.inventoryStat}
                </p>
              </div>
            </div>

            {/* Modular Features List */}
            <div className="mt-4 rounded-2xl border border-[#eee9df] bg-[#fbf9f4] p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs font-bold text-[#123324] font-display">
                  {t.modularOpsTitle}
                </p>
              </div>

              {[
                { label: t.feature1, tag: "Shops" },
                { label: t.feature2, tag: "Catalog" },
                { label: t.feature3, tag: "Orders" },
              ].map((item, index) => (
                <div
                  key={item.label}
                  className="flex items-center gap-3 border-t border-[#eee9df] py-3 first:border-0"
                >
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#e7f2eb] font-display text-[11px] font-bold text-[#1F5D42]">
                    0{index + 1}
                  </span>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-[#17251e]">{item.label}</p>
                  </div>
                  <span className="h-2 w-2 rounded-full bg-[#E8A33D]" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[#ddd6ca] bg-[#FFFDF8]/70 py-6 px-6 sm:px-10">
        <div className="mx-auto flex max-w-7xl flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#6d756f]">
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-sm text-[#123324]">Dukandaar</span>
            <span>{t.footerText}</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/merchant/login" className="hover:text-[#1F5D42] transition">
              {t.merchantLogin}
            </Link>
            <Link href="/admin/login" className="hover:text-[#1F5D42] transition">
              {t.superAdmin}
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
