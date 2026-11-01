"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowLeft, CheckCircle2, KeyRound, Phone, Store } from "lucide-react";
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
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await merchantApi.requestPasswordRecovery(mobile);
      setSent(true);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await merchantApi.confirmPasswordRecovery({
        mobile_number: mobile,
        otp,
        new_password: password,
      });
      setDone(true);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center bg-[#F6F0E6] px-4 py-12 font-sans text-[#17251e]">
      <section className="w-full max-w-[440px] rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 sm:p-9 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-[#eee9df]">
          <Link
            href="/merchant/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1F5D42] hover:underline"
          >
            <ArrowLeft size={14} />
            Back to sign in
          </Link>
          <div className="flex items-center gap-1.5 text-xs font-bold text-[#123324]">
            <div className="grid h-6 w-6 place-items-center rounded-lg bg-[#E8A33D] text-[#123324]">
              <Store size={13} />
            </div>
            <span>Dukandaar</span>
          </div>
        </div>

        <div className="mb-6 mt-6 grid h-12 w-12 place-items-center rounded-2xl bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5]">
          {done ? <CheckCircle2 size={24} /> : <KeyRound size={22} />}
        </div>

        <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#6d756f]">
          Merchant Account Recovery
        </p>
        <h1 className="mt-1.5 text-2xl font-bold font-display tracking-tight text-[#123324]">
          {done ? "Password updated" : sent ? "Enter your code" : "Reset your password"}
        </h1>
        <p className="mt-2 text-xs leading-relaxed text-[#5e665f]">
          {done
            ? "Your password has been changed successfully. You can now sign in with your new credentials."
            : sent
            ? "Enter the seven-digit code sent to your registered mobile number, then choose a new password."
            : "We’ll send a one-time code to the mobile number registered to your merchant account."}
        </p>

        {done ? (
          <Link
            href="/merchant/login"
            className="mt-7 flex h-12 items-center justify-center rounded-xl bg-[#1F5D42] text-sm font-semibold text-white shadow-xs hover:bg-[#164732] transition"
          >
            Return to sign in
          </Link>
        ) : (
          <form onSubmit={sent ? resetPassword : requestCode} className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-[#123324]">
                Registered mobile number
              </span>
              <span className="flex h-12 items-center gap-2.5 rounded-xl border border-[#ddd6ca] bg-white px-3.5 focus-within:border-[#1F5D42] focus-within:ring-2 focus-within:ring-[#1F5D42]/10">
                <Phone size={15} className="text-[#6d756f] shrink-0" />
                <input
                  required
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  disabled={sent}
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="+91 98765 43210"
                  className="w-full bg-transparent text-sm text-[#123324] outline-none placeholder:text-[#a5ada7] disabled:text-[#88918a]"
                />
              </span>
            </label>

            {sent && (
              <>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-[#123324]">
                    One-time code
                  </span>
                  <input
                    required
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 7))}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={7}
                    placeholder="7-digit code"
                    className="h-12 w-full rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-sm tracking-[.2em] outline-none focus:border-[#1F5D42] focus:ring-2 focus:ring-[#1F5D42]/10"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-[#123324]">
                    New password
                  </span>
                  <input
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    placeholder="Minimum 8 characters"
                    className="h-12 w-full rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-sm outline-none focus:border-[#1F5D42] focus:ring-2 focus:ring-[#1F5D42]/10"
                  />
                </label>
              </>
            )}

            {error && (
              <p role="alert" className="rounded-xl bg-red-50 border border-red-200 px-3.5 py-3 text-xs text-red-700">
                {error}
              </p>
            )}

            <button
              disabled={busy}
              className="h-12 w-full rounded-xl bg-[#1F5D42] text-sm font-semibold text-white hover:bg-[#164732] shadow-xs transition disabled:opacity-60 cursor-pointer"
            >
              {busy ? "Please wait…" : sent ? "Set new password" : "Send recovery code"}
            </button>
          </form>
        )}

        <p className="mt-6 text-[10px] leading-relaxed text-[#848c85] text-center border-t border-[#eee9df] pt-4">
          If recovery is not available for your account, contact your Dukandaar administrator.
        </p>
      </section>
    </main>
  );
}
