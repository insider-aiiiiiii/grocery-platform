"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ArrowRight, MapPin, Store } from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

const buildSchema = (hi: boolean) => z.object({ name: z.string().min(2, hi ? "अपनी दुकान का नाम डालें" : "Enter your shop name"), description: z.string().optional(), address_line: z.string().min(2, hi ? "पूरा पता डालें" : "Enter the street address"), area: z.string().min(2, hi ? "इलाका डालें" : "Enter the area"), city: z.string().min(2, hi ? "शहर डालें" : "Enter the city"), state: z.string().min(2, hi ? "राज्य डालें" : "Enter the state"), pincode: z.string().min(4, hi ? "सही पिन कोड डालें" : "Enter a valid PIN code") });
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

export default function ShopSetupPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const lang = usePortalLang();
  const isHi = lang === "hi";
  const schema = useMemo(() => buildSchema(isHi), [isHi]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema) });
  const onSubmit = async (values: Values) => {
    setSaving(true); setError("");
    try {
      await merchantApi.createShop({ ...values, is_home_delivery_enabled: true, is_pickup_enabled: true, delivery_fee_type: "FIXED", delivery_charge: "0.00" });
      await queryClient.invalidateQueries({ queryKey: ["merchant", "shop"] });
      router.replace("/merchant"); router.refresh();
    } catch (err) { setError(getApiError(err)); }
    finally { setSaving(false); }
  };
  const fields: Array<[keyof Values, string, string]> = isHi
    ? [["name", "दुकान का नाम", "जैसे: ग्रीन बास्केट किराना"], ["address_line", "पूरा पता", "दुकान नंबर, बिल्डिंग, गली"], ["area", "इलाका / मोहल्ला", "जैसे: इंदिरानगर"], ["city", "शहर", "बेंगलुरु"], ["state", "राज्य", "कर्नाटक"], ["pincode", "पिन कोड", "560038"]]
    : [["name", "Shop name", "e.g. Green Basket Grocery"], ["address_line", "Street address", "Shop no., building, street"], ["area", "Area / neighborhood", "e.g. Indiranagar"], ["city", "City", "Bengaluru"], ["state", "State", "Karnataka"], ["pincode", "PIN code", "560038"]];

  return <div className="mx-auto max-w-[780px]">
    <div className="mb-7"><div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-[#e3efdf] text-[#315f43]"><Store size={22}/></div><p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[#718474]">{isHi ? "अच्छी शुरुआत" : "A great start"}</p><h1 className="mt-2 text-3xl font-semibold tracking-[-.04em]">{isHi ? "अपनी दुकान सेट करें" : "Set up your shop"}</h1><p className="mt-2 text-sm text-[#7a887e]">{isHi ? "अपनी दुकान की जानकारी भरें ताकि आपका पोर्टल खुल सके। इसे बाद में बदल भी सकते हैं।" : "Add your store details to open your merchant workspace. You can update these later."}</p></div>
    <form onSubmit={handleSubmit(onSubmit)} className="rounded-2xl border border-[#e5e9e2] bg-white p-5 shadow-[0_12px_32px_-24px_rgba(30,50,36,.18)] sm:p-8">
      <div className="mb-6 flex items-center gap-2 border-b border-[#eef0ec] pb-4 text-sm font-semibold"><MapPin size={16} className="text-[#4e7657]"/>{isHi ? "दुकान की जानकारी" : "Store information"}</div>
      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map(([key, label, placeholder]) => <label key={key} className={`block ${key === "name" ? "sm:col-span-2" : ""}`}><span className="mb-1.5 block text-xs font-semibold text-[#3c4d40]">{label}</span><input {...register(key)} placeholder={placeholder} className="h-11 w-full rounded-xl border border-[#dfe5dd] bg-white px-3.5 text-sm outline-none transition placeholder:text-[#a6b1a8] focus:border-[#64896a] focus:ring-4 focus:ring-[#e5efe3]"/>{errors[key] && <span className="mt-1 block text-[11px] text-red-600">{errors[key]?.message}</span>}</label>)}
        <label className="block sm:col-span-2"><span className="mb-1.5 block text-xs font-semibold text-[#3c4d40]">{isHi ? "दुकान का छोटा परिचय" : "A short introduction"} <span className="font-normal text-[#9aa49c]">{isHi ? "(वैकल्पिक)" : "(optional)"}</span></span><textarea {...register("description")} rows={3} placeholder={isHi ? "आस-पास के ग्राहकों को बताएं कि आपकी दुकान में क्या खास है" : "Tell nearby customers what makes your shop special"} className="w-full resize-y rounded-xl border border-[#dfe5dd] p-3.5 text-sm outline-none placeholder:text-[#a6b1a8] focus:border-[#64896a] focus:ring-4 focus:ring-[#e5efe3]"/></label>
      </div>
      {error && <p role="alert" className="mt-5 rounded-xl bg-red-50 px-3.5 py-3 text-xs text-red-700">{error}</p>}
      <div className="mt-7 flex flex-col-reverse items-center justify-between gap-4 border-t border-[#eef0ec] pt-5 sm:flex-row"><p className="text-[11px] text-[#8b968d]">{isHi ? "आपका संपर्क नंबर आपके दुकानदार अकाउंट से लिया जाता है।" : "Your contact number comes from your merchant account."}</p><button disabled={saving} className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#214e37] px-5 text-sm font-semibold text-white hover:bg-[#183f2d] disabled:opacity-60 sm:w-auto">{saving ? (isHi ? "दुकान बन रही है…" : "Creating shop…") : (isHi ? "मेरी दुकान बनाएं" : "Create my shop")}<ArrowRight size={16}/></button></div>
    </form>
  </div>;
}
