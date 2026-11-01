"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  HelpCircle,
  KeyRound,
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

  // Recovery modal
  const [recoveryModalOpen, setRecoveryModalOpen] = useState(false);
  const [recoveryContact, setRecoveryContact] = useState("");
  const [recoveryChannel, setRecoveryChannel] = useState<"EMAIL" | "SMS">("EMAIL");
  const [recoveryStatus, setRecoveryStatus] = useState<string | null>(null);
  const [recoveryLoading, setRecoveryLoading] = useState(false);

  // Language state synced with portal
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
        setErrorMessage("Authentication failed: No access token received from server.");
      }
    } catch (err: any) {
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

  const handleSelfRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryLoading(true);
    setRecoveryStatus(null);
    try {
      await adminApi.requestSelfRecovery({
        channel: recoveryChannel,
        contact: recoveryContact.trim(),
      });
      setRecoveryStatus(
        lang === "hi"
          ? "रिकवरी टोकन भेज दिया गया है। अपने इनबॉक्स या SMS की जांच करें।"
          : "Recovery token dispatched. Check your security inbox or SMS."
      );
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        (lang === "hi" ? "रिकवरी अनुरोध विफल रहा।" : "Recovery request failed. Verify your registered identifier.");
      setRecoveryStatus(`Error: ${detail}`);
    } finally {
      setRecoveryLoading(false);
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
                ? "प्लेटफॉर्म नेटवर्क गवर्नेंस व कंट्रोल"
                : "Platform Network Governance & Control"}
            </span>
          </div>

          <h1 className="text-4xl font-bold leading-[1.15] tracking-[-.03em] xl:text-[50px] font-display">
            {lang === "hi" ? (
              <>
                केंद्रीय नियंत्रण <br />
                समस्त <span className="text-[#E8A33D]">दुकानदार नेटवर्क</span> के लिए।
              </>
            ) : (
              <>
                Unified control for the <br />
                <span className="text-[#E8A33D]">Dukandaar network.</span>
              </>
            )}
          </h1>

          <p className="mt-5 max-w-md text-sm leading-relaxed text-[#b9cac0]">
            {lang === "hi"
              ? "सभी मर्चेंट टैलेंट्स, मास्टर कैटलॉग क्युरेशन, प्रचार अभियान और लाइव सुरक्षा टेलीमेट्री का संपूर्ण प्रशासन।"
              : "Enterprise governance across all retail tenants, master catalog curation, marketing campaigns, and real-time platform telemetry."}
          </p>

          {/* Value Highlights */}
          <div className="mt-8 space-y-3 max-w-md">
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <ShieldCheck size={16} className="text-[#E8A33D] shrink-0" />
              <span>
                {lang === "hi"
                  ? "मल्टी-टेनेंट दुकान डायरेक्टरी और स्टेटस एक्टिवेशन"
                  : "Multi-tenant shop directory & status activation"}
              </span>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <ShieldCheck size={16} className="text-[#E8A33D] shrink-0" />
              <span>
                {lang === "hi"
                  ? "यूनिवर्सल मास्टर कैटलॉग, JSON/Excel एक्सपोर्ट व बल्क इंपोर्ट"
                  : "Universal Master Catalog, JSON/Excel bulk import & exports"}
              </span>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <ShieldCheck size={16} className="text-[#E8A33D] shrink-0" />
              <span>
                {lang === "hi"
                  ? "रोल-आधारित ऑथराइजेशन और ऑटोमेटेड सेशन सिक्योरिटी"
                  : "Role-based token validation & emergency self-recovery"}
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
                ? "256-बिट सुरक्षित एन्क्रिप्शन व सत्र अलगाव सक्रिय।"
                : "Secured with JWT session validation & tenant isolation."}
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
                    Super Admin
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
                  ? "सुपर एडमिन क्रेडेंशियल्स दर्ज करके प्लेटफॉर्म कंसोल खोलें।"
                  : "Enter your Super Admin identifier and passphrase to access console."}
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
                  {lang === "hi" ? "एडमिनिस्ट्रेटिव पहचानकर्ता" : "Administrative identifier"}
                </span>
                <span className="flex h-12 items-center gap-3 rounded-xl border border-[#ddd6ca] bg-white px-3.5 focus-within:border-[#1F5D42] focus-within:ring-3 focus-within:ring-[#1F5D42]/10 transition shadow-2xs">
                  <Mail size={16} className="text-[#6d756f] shrink-0" />
                  <input
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="admin or admin@dukandaar.internal"
                    className="w-full bg-transparent text-sm text-[#123324] outline-none placeholder:text-[#a5ada7]"
                  />
                </span>
              </label>

              {/* Field 2: Password */}
              <label className="block">
                <div className="mb-1.5 flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#123324]">
                    {lang === "hi" ? "मास्टर पासफ़्रेज़" : "Passphrase"}
                  </span>
                  <button
                    type="button"
                    onClick={() => setRecoveryModalOpen(true)}
                    className="text-[#1F5D42] hover:text-[#123324] font-medium hover:underline text-[11px]"
                  >
                    {lang === "hi" ? "पासवर्ड भूल गए?" : "Forgot passphrase?"}
                  </button>
                </div>
                <span className="flex h-12 items-center gap-3 rounded-xl border border-[#ddd6ca] bg-white px-3.5 focus-within:border-[#1F5D42] focus-within:ring-3 focus-within:ring-[#1F5D42]/10 transition shadow-2xs">
                  <Lock size={16} className="text-[#6d756f] shrink-0" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={lang === "hi" ? "मास्टर पासवर्ड दर्ज करें" : "Enter master passphrase"}
                    className="w-full bg-transparent text-sm text-[#123324] outline-none placeholder:text-[#a5ada7]"
                  />
                  <button
                    type="button"
                    className="text-[#6d756f] hover:text-[#123324] p-1"
                    aria-label={showPassword ? "Hide password" : "Show password"}
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
                    {lang === "hi" ? "30 दिनों के लिए याद रखें" : "Remember workstation for 30 days"}
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
                      {lang === "hi" ? "सत्यापन हो रहा है…" : "Authenticating Super Admin…"}
                    </span>
                  </>
                ) : (
                  <>
                    <span>
                      {lang === "hi" ? "एडमिन कंसोल में प्रवेश करें" : "Access Admin Console"}
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
              <button
                type="button"
                onClick={() => setRecoveryModalOpen(true)}
                className="inline-flex items-center gap-1.5 text-xs text-[#E8A33D] hover:underline font-medium"
              >
                <HelpCircle size={13} />
                <span>
                  {lang === "hi" ? "आपातकालीन सुरक्षा रिकवरी" : "Emergency Access Recovery"}
                </span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Emergency Self-Recovery Modal */}
      {recoveryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-[#FFFDF8] border border-[#ddd6ca] rounded-3xl max-w-md w-full p-6 sm:p-7 shadow-2xl relative">
            <div className="flex items-center justify-between pb-3.5 border-b border-[#eee9df]">
              <div className="flex items-center gap-2.5">
                <div className="grid h-8 w-8 place-items-center rounded-xl bg-[#E8A33D]/20 text-[#E8A33D]">
                  <KeyRound size={16} />
                </div>
                <h2 className="text-base font-bold text-[#123324] font-display">
                  {lang === "hi" ? "आपातकालीन स्व-रिकवरी" : "Emergency Self-Recovery"}
                </h2>
              </div>
              <button
                onClick={() => {
                  setRecoveryModalOpen(false);
                  setRecoveryStatus(null);
                }}
                className="text-[#6d756f] hover:text-[#123324] text-sm px-2 py-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSelfRecovery} className="mt-4 space-y-3.5">
              <p className="text-xs text-[#5e665f] leading-relaxed">
                {lang === "hi"
                  ? "पंजीकृत एडमिनिस्ट्रेटर ईमेल या फोन पर एक बार का सुरक्षा टोकन (OTP) भेजें।"
                  : "Dispatch an out-of-band one-time verification challenge via registered administrator email or phone."}
              </p>

              <div>
                <label className="block text-xs font-semibold text-[#123324] mb-1.5">
                  {lang === "hi" ? "माध्यम चुनें" : "Channel"}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRecoveryChannel("EMAIL")}
                    className={`py-2 text-xs font-semibold rounded-xl border transition ${
                      recoveryChannel === "EMAIL"
                        ? "bg-[#1F5D42] border-[#1F5D42] text-white shadow-2xs"
                        : "bg-white border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
                    }`}
                  >
                    Email OTP
                  </button>
                  <button
                    type="button"
                    onClick={() => setRecoveryChannel("SMS")}
                    className={`py-2 text-xs font-semibold rounded-xl border transition ${
                      recoveryChannel === "SMS"
                        ? "bg-[#1F5D42] border-[#1F5D42] text-white shadow-2xs"
                        : "bg-white border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
                    }`}
                  >
                    SMS / WhatsApp
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#123324] mb-1.5">
                  {lang === "hi" ? "पंजीकृत ईमेल या मोबाइल नंबर" : "Registered Contact (Email or Mobile)"}
                </label>
                <input
                  type="text"
                  required
                  value={recoveryContact}
                  onChange={(e) => setRecoveryContact(e.target.value)}
                  placeholder="admin@platform.com or +91 98765 43210"
                  className="w-full h-11 px-3.5 bg-white border border-[#ddd6ca] rounded-xl text-xs text-[#123324] placeholder:text-[#a5ada7] focus:outline-none focus:border-[#1F5D42] focus:ring-2 focus:ring-[#1F5D42]/10"
                />
              </div>

              {recoveryStatus && (
                <div
                  className={`p-3 rounded-xl text-xs leading-relaxed ${
                    recoveryStatus.startsWith("Error")
                      ? "bg-red-50 border border-red-200 text-red-700"
                      : "bg-[#e7f2eb] border border-[#cbe1d5] text-[#1F5D42] flex items-center gap-2"
                  }`}
                >
                  {!recoveryStatus.startsWith("Error") && (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-[#1F5D42]" />
                  )}
                  <span>{recoveryStatus}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setRecoveryModalOpen(false);
                    setRecoveryStatus(null);
                  }}
                  className="px-3.5 py-2 rounded-xl border border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df] text-xs font-semibold"
                >
                  {lang === "hi" ? "रद्द करें" : "Cancel"}
                </button>
                <button
                  type="submit"
                  disabled={recoveryLoading}
                  className="px-4 py-2 bg-[#1F5D42] hover:bg-[#164732] text-white font-semibold rounded-xl text-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-60 shadow-xs"
                >
                  {recoveryLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{lang === "hi" ? "OTP भेजें" : "Dispatch OTP"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
