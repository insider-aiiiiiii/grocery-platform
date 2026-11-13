"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Languages,
  Lock,
  Mail,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Store,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";

export default function SuperAdminLoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);



  // Language state synced with portal
  const [lang, setLang] = useState<"en" | "hi">("en");

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

  const toggleLanguage = () => {
    const next = lang === "hi" ? "en" : "hi";
    setLang(next);
    localStorage.setItem("super_admin_language", next);
    window.dispatchEvent(new Event("admin-lang-changed"));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setLoading(true);

    try {
      const data = await adminApi.login({
        identifier: identifier.trim(),
        password,
      });

      if (data.access) {
        localStorage.setItem("admin_access_token", data.access);
        const adminName = data.user?.username || data.user?.email || identifier.trim();
        localStorage.setItem("admin_username", adminName);
        if (data.user) {
          localStorage.setItem("admin_user", JSON.stringify(data.user));
        }
        if (data.refresh) {
          localStorage.setItem("admin_refresh_token", data.refresh);
        }
        if (rememberMe) {
          localStorage.setItem("admin_remember", "true");
        }
        router.push("/admin");
      } else {
        setErrorMessage(
          lang === "hi"
            ? "लॉगिन नहीं हो पाया। कृपया दोबारा कोशिश करें।"
            : "Sign-in failed. Please try again."
        );
      }
    } catch (err: any) {
      const status = err?.response?.status;
      if (lang === "hi" && (status === 401 || status === 403)) {
        setErrorMessage("अमान्य लॉगिन विवरण, या इस खाते को सुपर एडमिन की अनुमति नहीं है।");
        return;
      }
      if (status === 429) {
        setErrorMessage(
          lang === "hi"
            ? "बहुत ज़्यादा कोशिशें हो गईं। कृपया थोड़ी देर बाद दोबारा कोशिश करें।"
            : "Too many attempts. Please wait a minute and try again."
        );
        return;
      }
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.response?.data?.non_field_errors?.[0] ||
        (lang === "hi"
          ? "अमान्य क्रेडेंशियल्स या सुपर एडमिन अनुमतियां अनुपलब्ध हैं।"
          : "Invalid credentials or insufficient Super Admin privileges.");
      setErrorMessage(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };



  return (
    <main className="grid min-h-screen bg-[#F6F0E6] lg:grid-cols-[1.05fr_.95fr] font-sans text-[#17251e]">
      {/* Left Brand Showcase Section */}
      <section className="relative hidden overflow-hidden bg-[#123324] px-14 py-12 text-white lg:flex lg:flex-col lg:justify-between xl:px-20 border-r border-[#1F5D42]/30">
        {/* Ambient Ring Elements */}
        <div className="absolute -right-28 top-20 h-[460px] w-[460px] rounded-full border border-white/10 pointer-events-none" />
        <div className="absolute -right-12 top-36 h-[320px] w-[320px] rounded-full border border-white/10 pointer-events-none" />
        <div className="absolute left-10 -bottom-24 h-[300px] w-[300px] rounded-full border border-white/5 pointer-events-none" />

        {/* Brand Header */}
        <div className="relative flex items-center gap-3.5 z-10">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#E8A33D] text-[#123324] font-bold shadow-md">
            <Store size={22} />
          </div>
          <div>
            <p className="font-display text-2xl font-bold tracking-tight text-white leading-tight">
              Dukandaar
            </p>
            <p className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#a2b5a8]">
              {lang === "hi" ? "सुपर एडमिन कंसोल" : "Super Admin Console"}
            </p>
          </div>
        </div>

        {/* Central Hero Pitch */}
        <div className="relative max-w-lg z-10 my-auto py-8">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[.08] px-3.5 py-1.5 text-xs text-[#dce7df] backdrop-blur-xs">
            <span className="h-2 w-2 rounded-full bg-[#E8A33D] animate-pulse" />
            <span>
              {lang === "hi"
                ? "हर दुकान के लिए आपका कंट्रोल रूम"
                : "Your control room for every shop"}
            </span>
          </div>

          <h1 className="text-4xl font-bold leading-[1.15] tracking-[-.03em] xl:text-[50px] font-display">
            {lang === "hi" ? (
              <>
                पूरा <span className="text-[#E8A33D]">Dukandaar नेटवर्क</span>, एक ही जगह से।
              </>
            ) : (
              <>
                Run the whole <br />
                <span className="text-[#E8A33D]">Dukandaar network</span> from one place.
              </>
            )}
          </h1>

          <p className="mt-5 max-w-md text-sm leading-relaxed text-[#b9cac0]">
            {lang === "hi"
              ? "सभी दुकानें, प्रोडक्ट और ऑफ़र संभालें, और पूरे नेटवर्क के ऑर्डर व बिक्री पर नज़र रखें।"
              : "Look after every shop, product and offer, and keep an eye on orders and sales across the whole network."}
          </p>

          {/* Value Highlights */}
          <div className="mt-8 space-y-3 max-w-md">
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <ShieldCheck size={16} className="text-[#E8A33D] shrink-0" />
              <span>
                {lang === "hi"
                  ? "नई दुकानें जोड़ें और एक क्लिक में चालू या बंद करें"
                  : "Add new shops and switch them on or off in one click"}
              </span>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <ShieldCheck size={16} className="text-[#E8A33D] shrink-0" />
              <span>
                {lang === "hi"
                  ? "एक प्रोडक्ट कैटलॉग जिसमें से हर दुकान चुन सके, एक्सेल से अपलोड करें"
                  : "One product catalog every shop can pick from, uploadable from Excel"}
              </span>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <ShieldCheck size={16} className="text-[#E8A33D] shrink-0" />
              <span>
                {lang === "hi"
                  ? "सभी दुकानों के लिए ऑफ़र और घोषणाएं चलाएं"
                  : "Run offers and announcements for all your shops"}
              </span>
            </div>
          </div>

          {/* Security Tag */}
          <div className="mt-10 flex items-center gap-3 border-t border-white/10 pt-6">
            <div className="grid h-8 w-8 place-items-center rounded-xl bg-white/10 text-[#E8A33D]">
              <Shield size={16} />
            </div>
            <p className="text-xs text-[#b4c3b9]">
              {lang === "hi"
                ? "आपका और हर दुकान का डेटा निजी और सुरक्षित रहता है।"
                : "Your data and every shop's data stay private and safe."}
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="relative text-[11px] text-[#81998b] z-10">
          © 2026 Dukandaar · {lang === "hi" ? "प्लेटफॉर्म प्रशासन" : "Super Admin Console"}
        </p>
      </section>

      {/* Right Form Section */}
      <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-[430px]">
          {/* Card Container */}
          <div className="rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 sm:p-9 shadow-sm">
            {/* Top Bar: Mobile Brand + Language Switcher */}
            <div className="mb-6 flex items-center justify-between">
              <div className="flex items-center gap-2.5 lg:hidden">
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#E8A33D] text-[#123324] font-bold shadow-xs">
                  <Store size={18} />
                </div>
                <div>
                  <p className="font-display font-bold text-base text-[#123324] leading-none">
                    Dukandaar
                  </p>
                  <p className="text-[9px] uppercase tracking-wider text-[#6d756f] mt-0.5">
                    {lang === "hi" ? "सुपर एडमिन" : "Super Admin"}
                  </p>
                </div>
              </div>

              {/* Language Switcher */}
              <button
                type="button"
                onClick={toggleLanguage}
                className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#ddd6ca] bg-white hover:bg-[#eee9df] text-xs font-semibold text-[#123324] transition shadow-2xs"
                title="Switch Language / भाषा बदलें"
              >
                <Languages size={14} className="text-[#1F5D42]" />
                <span>{lang === "hi" ? "English" : "हिंदी"}</span>
              </button>
            </div>

            {/* Header Titles */}
            <div className="mb-7">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#e7f2eb] border border-[#cbe1d5] text-[10px] font-bold text-[#1F5D42] tracking-wider uppercase mb-2">
                <Sparkles size={11} className="text-[#E8A33D]" />
                <span>{lang === "hi" ? "प्रशासनिक पहुंच" : "Administrative Access"}</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold font-display tracking-tight text-[#123324]">
                {lang === "hi" ? "कंसोल में लॉगिन करें" : "Sign in to console"}
              </h2>
              <p className="mt-1.5 text-xs text-[#5e665f] leading-relaxed">
                {lang === "hi"
                  ? "आगे बढ़ने के लिए अपना एडमिन ईमेल या यूज़रनेम और पासवर्ड दर्ज करें।"
                  : "Enter your admin email or username and password to continue."}
              </p>
            </div>

            {/* Error Alert */}
            {errorMessage && (
              <div
                role="alert"
                className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5 leading-relaxed"
              >
                <ShieldAlert className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Field 1: Identifier */}
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-[#123324]">
                  {lang === "hi" ? "एडमिन ईमेल या यूज़रनेम" : "Admin email or username"}
                </span>
                <span className="flex h-12 items-center gap-3 rounded-xl border border-[#ddd6ca] bg-white px-3.5 focus-within:border-[#1F5D42] focus-within:ring-3 focus-within:ring-[#1F5D42]/10 transition shadow-2xs">
                  <Mail size={16} className="text-[#6d756f] shrink-0" />
                  <input
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder={lang === "hi" ? "एडमिन ईमेल या यूज़रनेम" : "Admin email or username"}
                    className="w-full bg-transparent text-sm text-[#123324] outline-none placeholder:text-[#a5ada7]"
                  />
                </span>
              </label>

              {/* Field 2: Password */}
              <label className="block">
                <div className="mb-1.5 flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#123324]">
                    {lang === "hi" ? "पासवर्ड" : "Password"}
                  </span>
                </div>
                <span className="flex h-12 items-center gap-3 rounded-xl border border-[#ddd6ca] bg-white px-3.5 focus-within:border-[#1F5D42] focus-within:ring-3 focus-within:ring-[#1F5D42]/10 transition shadow-2xs">
                  <Lock size={16} className="text-[#6d756f] shrink-0" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={lang === "hi" ? "अपना पासवर्ड दर्ज करें" : "Enter your password"}
                    className="w-full bg-transparent text-sm text-[#123324] outline-none placeholder:text-[#a5ada7]"
                  />
                  <button
                    type="button"
                    className="text-[#6d756f] hover:text-[#123324] p-1"
                    aria-label={
                      showPassword
                        ? lang === "hi" ? "पासवर्ड छिपाएं" : "Hide password"
                        : lang === "hi" ? "पासवर्ड दिखाएं" : "Show password"
                    }
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </span>
              </label>

              {/* Remember Workstation Checkbox */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none text-[#5e665f]">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-[#ddd6ca] text-[#1F5D42] focus:ring-[#1F5D42]"
                  />
                  <span>
                    {lang === "hi" ? "30 दिनों तक साइन इन रखें" : "Keep me signed in for 30 days"}
                  </span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#1F5D42] text-sm font-semibold text-white shadow-xs transition hover:bg-[#164732] active:scale-[0.99] disabled:opacity-60 cursor-pointer mt-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>
                      {lang === "hi" ? "साइन इन हो रहा है…" : "Signing you in…"}
                    </span>
                  </>
                ) : (
                  <>
                    <span>
                      {lang === "hi" ? "एडमिन कंसोल खोलें" : "Open Admin Console"}
                    </span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* Portal Switcher & Footer */}
            <div className="mt-7 pt-5 border-t border-[#eee9df] text-center space-y-2.5">
              <p className="text-xs text-[#5e665f]">
                {lang === "hi" ? "दुकानदार / मर्चेंट पोर्टल चाहिए?" : "Looking for Merchant Portal?"}{" "}
                <Link
                  href="/merchant/login"
                  className="font-semibold text-[#1F5D42] hover:underline"
                >
                  {lang === "hi" ? "मर्चेंट लॉगिन करें" : "Sign in to Shop"}
                </Link>
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
