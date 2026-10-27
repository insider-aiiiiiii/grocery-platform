"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ArrowRight, Eye, EyeOff, Leaf, LockKeyhole, Phone } from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

const schema = z.object({ mobile_number: z.string().min(8, "Enter your registered mobile number"), password: z.string().min(1, "Enter your password") });
type Values = z.infer<typeof schema>;

export default function MerchantLoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: Values) => {
    setError("");
    setSubmitting(true);
    try {
      const result = await merchantApi.login(values.mobile_number, values.password);
      if (result.user.role !== "MERCHANT") throw new Error("This sign-in is for merchant accounts.");
      sessionStorage.setItem("merchant_access_token", result.access);
      sessionStorage.setItem("merchant_refresh_token", result.refresh);
      sessionStorage.setItem("merchant_must_change_password", String(result.must_change_password));
      router.replace(result.must_change_password ? "/merchant/change-password" : result.user.shop_id ? "/merchant" : "/merchant/setup");
    } catch (err) {
      setError(err instanceof Error && !("response" in err) ? err.message : getApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return <main className="grid min-h-screen bg-[#f4f5ef] lg:grid-cols-[1.05fr_.95fr]">
    <section className="relative hidden overflow-hidden bg-[#173b2c] px-14 py-12 text-white lg:flex lg:flex-col lg:justify-between xl:px-20">
      <div className="absolute -right-28 top-24 h-[430px] w-[430px] rounded-full border border-white/10"/><div className="absolute -right-16 top-36 h-[300px] w-[300px] rounded-full border border-white/10"/>
      <div className="relative flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#d3ef6a] text-[#193a2c]"><Leaf size={22}/></div><div><p className="font-semibold tracking-tight">dukana</p><p className="text-[10px] uppercase tracking-[.2em] text-[#a5b9ac]">Merchant studio</p></div></div>
      <div className="relative max-w-lg"><p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[.06] px-3 py-1.5 text-[11px] text-[#d6e4da]"><span className="h-1.5 w-1.5 rounded-full bg-[#d3ef6a]"/>Your neighborhood, online</p><h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.045em] xl:text-[58px]">Good things happen<br/>at your <span className="text-[#d3ef6a]">corner shop.</span></h1><p className="mt-6 max-w-md text-sm leading-7 text-[#b4c3b9]">A calmer way to manage orders, keep products in stock, and grow the business you’ve built.</p>
        <div className="mt-12 flex items-center gap-4 border-t border-white/10 pt-6"><div className="flex -space-x-2"><span className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#173b2c] bg-[#e9c1a3] text-[10px] font-bold text-[#4e392e]">A</span><span className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#173b2c] bg-[#b8cfad] text-[10px] font-bold text-[#274132]">R</span><span className="grid h-8 w-8 place-items-center rounded-full border-2 border-[#173b2c] bg-[#edd995] text-[10px] font-bold text-[#55431d]">S</span></div><p className="text-xs text-[#b4c3b9]">Built for the people behind<br/><strong className="font-medium text-white">everyday essentials.</strong></p></div>
      </div>
      <p className="relative text-[10px] text-[#81998b]">© 2026 Dukana · Merchant workspace</p>
    </section>
    <section className="flex min-h-screen items-center justify-center px-5 py-12 sm:px-10">
      <div className="w-full max-w-[410px]">
        <div className="mb-10 flex items-center gap-3 lg:hidden"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#173b2c] text-[#d3ef6a]"><Leaf size={21}/></div><div><p className="font-semibold">dukana</p><p className="text-[10px] uppercase tracking-[.18em] text-[#758278]">Merchant studio</p></div></div>
        <div className="mb-8"><p className="mb-2 text-[11px] font-semibold uppercase tracking-[.17em] text-[#7a8a7e]">Welcome back</p><h2 className="text-[32px] font-semibold tracking-[-.04em] text-[#1c3327]">Sign in to your shop</h2><p className="mt-2 text-sm text-[#78857c]">Use the mobile number provided for your merchant account.</p></div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <label className="block"><span className="mb-2 block text-xs font-semibold text-[#34483a]">Mobile number</span><span className="flex h-12 items-center gap-3 rounded-xl border border-[#dfe5dd] bg-white px-3.5 focus-within:border-[#568063] focus-within:ring-4 focus-within:ring-[#dce9dc]"><Phone size={16} className="text-[#829187]"/><input {...register("mobile_number")} autoComplete="tel" inputMode="tel" placeholder="+91 98765 43210" className="w-full bg-transparent text-sm outline-none placeholder:text-[#aab4ac]"/></span>{errors.mobile_number && <span className="mt-1.5 block text-xs text-red-600">{errors.mobile_number.message}</span>}</label>
          <label className="block"><span className="mb-2 block text-xs font-semibold text-[#34483a]">Password</span><span className="flex h-12 items-center gap-3 rounded-xl border border-[#dfe5dd] bg-white px-3.5 focus-within:border-[#568063] focus-within:ring-4 focus-within:ring-[#dce9dc]"><LockKeyhole size={16} className="text-[#829187]"/><input {...register("password")} autoComplete="current-password" type={showPassword ? "text" : "password"} placeholder="Your password" className="w-full bg-transparent text-sm outline-none placeholder:text-[#aab4ac]"/><button type="button" className="text-[#829187]" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></span>{errors.password && <span className="mt-1.5 block text-xs text-red-600">{errors.password.message}</span>}</label>
          {error && <p role="alert" className="rounded-xl bg-red-50 px-3.5 py-3 text-xs text-red-700">{error}</p>}
          <button disabled={submitting} className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#214e37] text-sm font-semibold text-white shadow-sm transition hover:bg-[#183f2d] disabled:opacity-60">{submitting ? "Signing in…" : "Continue to workspace"}<ArrowRight size={16}/></button>
        </form>
        <p className="mt-6 text-center text-xs text-[#849087]">Forgot your password? <Link href="/merchant/recover" className="font-semibold text-[#426b49] hover:underline">Reset it with a code</Link></p>
        <p className="mt-10 text-center text-[10px] text-[#9aa49c]">Your account is protected by secure sign-in.</p>
      </div>
    </section>
  </main>;
}
