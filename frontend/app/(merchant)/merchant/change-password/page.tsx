"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { KeyRound, ShieldCheck } from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

const buildSchema = (hi: boolean) =>
  z
    .object({
      current_password: z.string().min(1, hi ? "अस्थायी पासवर्ड डालें" : "Enter the temporary password"),
      new_password: z.string().min(8, hi ? "कम से कम 8 अक्षर रखें" : "Use at least 8 characters"),
      confirm_password: z.string(),
    })
    .refine((data) => data.new_password === data.confirm_password, {
      path: ["confirm_password"],
      message: hi ? "पासवर्ड मेल नहीं खाते" : "Passwords do not match",
    });
type Values = z.infer<ReturnType<typeof buildSchema>>;

function usePortalLang() {
  const [lang, setLang] = useState<"en" | "hi">("en");
  useEffect(() => {
    const read = () => {
      const v = localStorage.getItem("portal_language");
      if (v === "hi" || v === "en") setLang(v);
    };
    const t = setTimeout(read, 0);
    window.addEventListener("portal-lang-changed", read);
    return () => {
      clearTimeout(t);
      window.removeEventListener("portal-lang-changed", read);
    };
  }, []);
  return lang;
}

export default function ChangePasswordPage() {
  const router = useRouter();
  const lang = usePortalLang();
  const isHi = lang === "hi";
  const schema = useMemo(() => buildSchema(isHi), [isHi]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const submit = async ({ current_password, new_password }: Values) => {
    setSaving(true);
    setError("");
    try {
      await merchantApi.changePassword(current_password, new_password);
      sessionStorage.removeItem("merchant_access_token");
      sessionStorage.removeItem("merchant_refresh_token");
      sessionStorage.removeItem("merchant_must_change_password");
      router.replace("/merchant/login");
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-[650px] py-6">
      <div className="mb-7">
        <div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5]">
          <KeyRound size={22} />
        </div>
        <p className="text-[11px] font-bold uppercase tracking-[.18em] text-[#6d756f]">
          {isHi ? "एक बार का सेटअप" : "One-time setup"}
        </p>
        <h1 className="mt-2 text-3xl font-bold font-display tracking-tight text-[#123324]">
          {isHi ? "नया पासवर्ड चुनें" : "Choose a new password"}
        </h1>
        <p className="mt-2 text-sm text-[#5e665f]">
          {isHi
            ? "आपका अकाउंट अभी अस्थायी पासवर्ड पर चल रहा है। अपनी दुकान को सुरक्षित रखने के लिए इसे बदलें।"
            : "Your account is currently using a temporary password. Update it to secure your shop workspace."}
        </p>
      </div>

      <form
        onSubmit={handleSubmit(submit)}
        className="rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 shadow-sm sm:p-8"
      >
        <div className="mb-6 flex gap-3 rounded-2xl bg-[#e7f2eb]/60 border border-[#cbe1d5]/80 p-4 text-[#1F5D42]">
          <ShieldCheck className="mt-0.5 shrink-0 text-[#1F5D42]" size={18} />
          <p className="text-xs leading-5 text-[#1F5D42]">
            {isHi
              ? "ऐसा मज़बूत पासवर्ड चुनें जो आपने पहले कभी इस्तेमाल न किया हो। पासवर्ड बदलने के बाद आपको दोबारा साइन इन करना होगा।"
              : "Choose a strong password you haven’t used before. You will be redirected to sign in again after it is updated."}
          </p>
        </div>

        {(
          [
            ["current_password", isHi ? "अस्थायी पासवर्ड" : "Temporary password"],
            ["new_password", isHi ? "नया पासवर्ड" : "New password"],
            ["confirm_password", isHi ? "नया पासवर्ड दोबारा डालें" : "Confirm new password"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="mb-4 block">
            <span className="mb-1.5 block text-xs font-semibold text-[#123324]">{label}</span>
            <input
              {...register(key)}
              type="password"
              autoComplete={key === "current_password" ? "current-password" : "new-password"}
              className="h-12 w-full rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-sm text-[#123324] outline-none placeholder:text-[#a5ada7] focus:border-[#1F5D42] focus:ring-3 focus:ring-[#1F5D42]/10"
            />
            {errors[key] && (
              <span className="mt-1 block text-xs font-medium text-red-600">
                {errors[key]?.message}
              </span>
            )}
          </label>
        ))}

        {error && (
          <p role="alert" className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3.5 py-3 text-xs text-red-700">
            {error}
          </p>
        )}

        <button
          disabled={saving}
          className="h-12 w-full rounded-xl bg-[#1F5D42] text-sm font-semibold text-white shadow-xs transition hover:bg-[#164732] disabled:opacity-60 cursor-pointer"
        >
          {saving
            ? (isHi ? "पासवर्ड बदला जा रहा है…" : "Updating password…")
            : (isHi ? "पासवर्ड बदलें और आगे बढ़ें" : "Update password & continue")}
        </button>
      </form>
    </div>
  );
}
