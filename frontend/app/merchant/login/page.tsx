"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Languages,
  LockKeyhole,
  Phone,
  Store,
  Sparkles,
} from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

const schema = z.object({
  mobile_number: z
    .string()
    .trim()
    .min(10, "Enter 10-digit mobile number / 10 अंकों का मोबाइल नंबर दर्ज करें")
    .max(14, "Invalid mobile number"),
  password: z.string().min(1, "Enter your password"),
});
type Values = z.infer<typeof schema>;

export default function MerchantLoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
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

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: Values) => {
    setError("");
    setSubmitting(true);
    try {
      const digits = values.mobile_number.replace(/\D/g, "");
      const clean10 = digits.slice(-10);
      const formattedPhone = `+91${clean10}`;
      const result = await merchantApi.login(formattedPhone, values.password);
      if (result.user.role !== "MERCHANT") {
        throw new Error("This sign-in is for merchant accounts.");
      }
      sessionStorage.setItem("merchant_access_token", result.access);
      sessionStorage.setItem("merchant_refresh_token", result.refresh);
      sessionStorage.setItem("merchant_must_change_password", String(result.must_change_password));
      router.replace(
        result.must_change_password
          ? "/merchant/change-password"
          : result.user.shop_id
            ? "/merchant"
            : "/merchant/setup"
      );
    } catch (err) {
      setError(err instanceof Error && !("response" in err) ? err.message : getApiError(err));
    } finally {
      setSubmitting(false);
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
              {lang === "hi" ? "व्यापारी वर्कस्पेस" : "Merchant Workspace"}
            </p>
          </div>
        </div>

        {/* Central Hero Pitch */}
        <div className="relative max-w-lg z-10 my-auto py-8">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[.08] px-3.5 py-1.5 text-xs text-[#dce7df] backdrop-blur-xs">
            <span className="h-2 w-2 rounded-full bg-[#E8A33D] animate-pulse" />
            <span>
              {lang === "hi" ? "आपकी दुकान, अब डिजिटल व ऑनलाइन" : "Your neighborhood retail store, online"}
            </span>
          </div>

          <h1 className="text-4xl font-bold leading-[1.15] tracking-[-.03em] xl:text-[50px] font-display">
            {lang === "hi" ? (
              <>
                सुविधा और भरोसा <br />
                आपकी <span className="text-[#E8A33D]">अपनी दुकान</span> पर।
              </>
            ) : (
              <>
                Good things happen <br />
                at your <span className="text-[#E8A33D]">local dukaan.</span>
              </>
            )}
          </h1>

          <p className="mt-5 max-w-md text-sm leading-relaxed text-[#b9cac0]">
            {lang === "hi"
              ? "दुकान का इन्वेंटरी स्टॉक, व्हाट्सएप ऑर्डर और मास्टर कैटलॉग संभालें आसान तरीके से — बिना किसी झंझट के।"
              : "A calm, powerful way to manage inventory, fulfill customer orders, and grow your local retail business."}
          </p>

          {/* Value Highlights */}
          <div className="mt-8 space-y-3 max-w-md">
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <CheckCircle2 size={16} className="text-[#E8A33D] shrink-0" />
              <span>{lang === "hi" ? "व्हाट्सएप पर तुरंत ऑर्डर नोटिफिकेशन" : "Instant WhatsApp customer order notifications"}</span>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <CheckCircle2 size={16} className="text-[#E8A33D] shrink-0" />
              <span>{lang === "hi" ? "मास्टर कैटलॉग से 1-क्लिक में प्रोडक्ट्स जोड़ें" : "One-click product add from platform Master Catalog"}</span>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[.05] border border-white/10 px-3.5 py-2.5 text-xs text-[#dce6df]">
              <CheckCircle2 size={16} className="text-[#E8A33D] shrink-0" />
              <span>{lang === "hi" ? "दुकान का सीधा QR कोड व डिलीवरी नियंत्रण" : "Direct storefront QR code & home delivery controls"}</span>
            </div>
          </div>

          {/* Social Proof */}
          <div className="mt-10 flex items-center gap-4 border-t border-white/10 pt-6">
            <div className="flex -space-x-2">
              <span className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#123324] bg-[#E8A33D] text-[11px] font-bold text-[#123324]">
                N
              </span>
              <span className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#123324] bg-[#b8cfad] text-[11px] font-bold text-[#274132]">
                S
              </span>
              <span className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#123324] bg-[#d6e4da] text-[11px] font-bold text-[#1F5D42]">
                G
              </span>
            </div>
            <p className="text-xs text-[#b4c3b9]">
              {lang === "hi" ? "भारत के स्थानीय किराना व जनरल स्टोर्स का भरोसा।" : "Built for the everyday heroes behind local retail."}
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="relative text-[11px] text-[#81998b] z-10">
          © 2026 Dukandaar · {lang === "hi" ? "मर्चेंट वर्कस्पेस" : "Merchant Workspace"}
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
                    Merchant
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
                <span>{lang === "hi" ? "स्वागत है" : "Welcome Back"}</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold font-display tracking-tight text-[#123324]">
                {lang === "hi" ? "दुकान में लॉगिन करें" : "Sign in to your shop"}
              </h2>
              <p className="mt-1.5 text-xs text-[#5e665f] leading-relaxed">
                {lang === "hi"
                  ? "अपने रजिस्टर्ड मोबाइल नंबर व पासवर्ड से दुकान वर्कस्पेस खोलें।"
                  : "Use the mobile number registered for your merchant account."}
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Mobile Number */}
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-[#123324]">
                  {lang === "hi" ? "रजिस्टर्ड मोबाइल नंबर" : "Mobile number"}
                </span>
                <span className="flex h-12 items-center gap-2 rounded-xl border border-[#ddd6ca] bg-white px-3 focus-within:border-[#1F5D42] focus-within:ring-3 focus-within:ring-[#1F5D42]/10 transition shadow-2xs">
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#F6F0E6] text-xs font-bold text-[#1F5D42] border border-[#e5dfd2] select-none shrink-0">
                    <Phone size={13} />
                    <span>+91</span>
                  </span>
                  <input
                    {...register("mobile_number")}
                    autoComplete="tel"
                    inputMode="numeric"
                    maxLength={10}
                    placeholder="98765 43210"
                    className="w-full bg-transparent text-sm font-semibold tracking-wide text-[#123324] outline-none placeholder:text-[#a5ada7]"
                  />
                </span>
                {errors.mobile_number && (
                  <span className="mt-1.5 block text-xs font-medium text-red-600">
                    {errors.mobile_number.message}
                  </span>
                )}
              </label>

              {/* Password */}
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-[#123324]">
                  {lang === "hi" ? "पासवर्ड" : "Password"}
                </span>
                <span className="flex h-12 items-center gap-3 rounded-xl border border-[#ddd6ca] bg-white px-3.5 focus-within:border-[#1F5D42] focus-within:ring-3 focus-within:ring-[#1F5D42]/10 transition shadow-2xs">
                  <LockKeyhole size={16} className="text-[#6d756f] shrink-0" />
                  <input
                    {...register("password")}
                    autoComplete="current-password"
                    type={showPassword ? "text" : "password"}
                    placeholder={lang === "hi" ? "आपका पासवर्ड" : "Your password"}
                    className="w-full bg-transparent text-sm text-[#123324] outline-none placeholder:text-[#a5ada7]"
                  />
                  <button
                    type="button"
                    className="text-[#6d756f] hover:text-[#123324] p-1"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </span>
                {errors.password && (
                  <span className="mt-1.5 block text-xs font-medium text-red-600">
                    {errors.password.message}
                  </span>
                )}
                <div className="flex justify-between items-center mt-1.5 px-0.5">
                  <span className="text-[11px] text-[#6d756f]">
                    {lang === "hi" ? "पासवर्ड भूल गए?" : "Forgot password?"}
                  </span>
                  <Link
                    href="/merchant/recover"
                    className="text-[11px] font-semibold text-[#1F5D42] hover:underline"
                  >
                    {lang === "hi" ? "सुपर एडमिन से रीसेट कराएं" : "Contact Super Admin"}
                  </Link>
                </div>
              </label>

              {/* Error Alert */}
              {error && (
                <div
                  role="alert"
                  className="rounded-xl bg-red-50 border border-red-200 px-3.5 py-3 text-xs text-red-700 leading-relaxed"
                >
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <button
                disabled={submitting}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#1F5D42] text-sm font-semibold text-white shadow-xs transition hover:bg-[#164732] active:scale-[0.99] disabled:opacity-60 cursor-pointer mt-2"
              >
                <span>
                  {submitting
                    ? lang === "hi"
                      ? "लॉगिन हो रहा है…"
                      : "Signing in…"
                    : lang === "hi"
                      ? "वर्कस्पेस में प्रवेश करें"
                      : "Continue to workspace"}
                </span>
                <ArrowRight size={16} />
              </button>
            </form>

            {/* Portal Switcher & Footer */}
            <div className="mt-7 pt-5 border-t border-[#eee9df] text-center space-y-2.5">
              <p className="text-[10px] text-[#848c85]">
                {lang === "hi"
                  ? "सुरक्षित सत्र प्रबंधन व डेटा एन्क्रिप्शन सक्रिय है।"
                  : "Protected by Dukandaar verified multi-tenant security."}
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
