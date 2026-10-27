"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { KeyRound, ShieldCheck } from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

const schema = z.object({ current_password: z.string().min(1, "Enter the temporary password"), new_password: z.string().min(8, "Use at least 8 characters"), confirm_password: z.string() }).refine((data) => data.new_password === data.confirm_password, { path: ["confirm_password"], message: "Passwords do not match" });
type Values = z.infer<typeof schema>;

export default function ChangePasswordPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema) });
  const submit = async ({ current_password, new_password }: Values) => {
    setSaving(true); setError("");
    try {
      await merchantApi.changePassword(current_password, new_password);
      sessionStorage.removeItem("merchant_access_token"); sessionStorage.removeItem("merchant_refresh_token"); sessionStorage.removeItem("merchant_must_change_password");
      router.replace("/merchant/login");
    } catch (err) { setError(getApiError(err)); }
    finally { setSaving(false); }
  };
  return <div className="mx-auto max-w-[650px]">
    <div className="mb-7"><div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-[#e3efdf] text-[#315f43]"><KeyRound size={21}/></div><p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[#718474]">One-time setup</p><h1 className="mt-2 text-3xl font-semibold tracking-[-.04em]">Choose a new password</h1><p className="mt-2 text-sm text-[#7a887e]">Your account uses a temporary password. Change it to continue.</p></div>
    <form onSubmit={handleSubmit(submit)} className="rounded-2xl border border-[#e5e9e2] bg-white p-5 shadow-[0_12px_32px_-24px_rgba(30,50,36,.18)] sm:p-8">
      <div className="mb-6 flex gap-3 rounded-xl bg-[#f2f6ef] p-4"><ShieldCheck className="mt-0.5 shrink-0 text-[#4b7653]" size={18}/><p className="text-xs leading-5 text-[#5e7162]">Choose a password you haven’t used before. You’ll sign in again after it’s updated.</p></div>
      {([["current_password", "Temporary password"], ["new_password", "New password"], ["confirm_password", "Confirm new password"]] as const).map(([key, label]) => <label key={key} className="mb-4 block"><span className="mb-1.5 block text-xs font-semibold text-[#3c4d40]">{label}</span><input {...register(key)} type="password" autoComplete={key === "current_password" ? "current-password" : "new-password"} className="h-11 w-full rounded-xl border border-[#dfe5dd] px-3.5 text-sm outline-none focus:border-[#64896a] focus:ring-4 focus:ring-[#e5efe3]"/>{errors[key] && <span className="mt-1 block text-[11px] text-red-600">{errors[key]?.message}</span>}</label>)}
      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-3.5 py-3 text-xs text-red-700">{error}</p>}
      <button disabled={saving} className="h-11 w-full rounded-xl bg-[#214e37] text-sm font-semibold text-white hover:bg-[#183f2d] disabled:opacity-60">{saving ? "Updating password…" : "Update password"}</button>
    </form>
  </div>;
}
