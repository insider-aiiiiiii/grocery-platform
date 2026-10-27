"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowLeft, CheckCircle2, KeyRound, Phone } from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

export default function MerchantRecoveryPage() {
  const [mobile, setMobile] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestCode = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await merchantApi.requestPasswordRecovery(mobile); setSent(true); }
    catch (err) { setError(getApiError(err)); }
    finally { setBusy(false); }
  };
  const resetPassword = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await merchantApi.confirmPasswordRecovery({ mobile_number: mobile, otp, new_password: password }); setDone(true); }
    catch (err) { setError(getApiError(err)); }
    finally { setBusy(false); }
  };
  return <main className="grid min-h-screen place-items-center bg-[#f4f5ef] px-5 py-12"><section className="w-full max-w-[440px] rounded-3xl border border-[#e3e9e1] bg-white p-6 shadow-[0_20px_70px_-42px_rgba(27,54,34,.28)] sm:p-9"><Link href="/merchant/login" className="inline-flex items-center gap-2 text-xs font-semibold text-[#66806b]"><ArrowLeft size={14}/>Back to sign in</Link><div className="mb-7 mt-7 grid h-12 w-12 place-items-center rounded-2xl bg-[#e5f0e2] text-[#426b49]">{done ? <CheckCircle2 size={22}/> : <KeyRound size={21}/>}</div><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-[#819087]">Account recovery</p><h1 className="mt-2 text-2xl font-semibold tracking-[-.04em] text-[#20352a]">{done ? "Password updated" : sent ? "Enter your code" : "Reset your password"}</h1><p className="mt-2 text-sm leading-6 text-[#78867c]">{done ? "Your password has been changed. Sign in with your new password." : sent ? "Enter the seven-digit code sent to the registered mobile number, then choose a new password." : "We’ll send a one-time code to the mobile number registered to your merchant account."}</p>
    {done ? <Link href="/merchant/login" className="mt-7 flex h-11 items-center justify-center rounded-xl bg-[#214e37] text-sm font-semibold text-white">Return to sign in</Link> : <form onSubmit={sent ? resetPassword : requestCode} className="mt-6 space-y-4"><label className="block"><span className="mb-1.5 block text-xs font-semibold text-[#435548]">Registered mobile number</span><span className="flex h-11 items-center gap-2 rounded-xl border border-[#dfe5dd] px-3"><Phone size={15} className="text-[#849087]"/><input required value={mobile} onChange={(e) => setMobile(e.target.value)} disabled={sent} inputMode="tel" autoComplete="tel" placeholder="+91 98765 43210" className="w-full bg-transparent text-sm outline-none disabled:text-[#758278]"/></span></label>{sent && <><label className="block"><span className="mb-1.5 block text-xs font-semibold text-[#435548]">One-time code</span><input required value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 7))} inputMode="numeric" autoComplete="one-time-code" maxLength={7} placeholder="7-digit code" className="h-11 w-full rounded-xl border border-[#dfe5dd] px-3 text-sm tracking-[.2em] outline-none focus:border-[#64896a]"/></label><label className="block"><span className="mb-1.5 block text-xs font-semibold text-[#435548]">New password</span><input required value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="new-password" minLength={8} className="h-11 w-full rounded-xl border border-[#dfe5dd] px-3 text-sm outline-none focus:border-[#64896a]"/></label></>}{error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2.5 text-xs text-red-700">{error}</p>}<button disabled={busy} className="h-11 w-full rounded-xl bg-[#214e37] text-sm font-semibold text-white hover:bg-[#183f2d] disabled:opacity-60">{busy ? "Please wait…" : sent ? "Set new password" : "Send recovery code"}</button></form>}
    <p className="mt-6 text-[10px] leading-5 text-[#98a39a]">If recovery is not available for your account, contact your platform administrator.</p></section></main>;
}
