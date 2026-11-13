"use client";

import React, { useState } from "react";
import { X, UserPlus, RefreshCw, CheckCircle2, AlertCircle, Send } from "lucide-react";
import { useAdminLang } from "./useAdminLang";
import { adminApi, ProvisionMerchantPayload } from "@/lib/api/admin";
import { normalizeIndianMobileInput } from "@/lib/format";

interface OnboardMerchantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  token?: string;
}

export function OnboardMerchantModal({ isOpen, onClose, onSuccess, token }: OnboardMerchantModalProps) {
  const hi = useAdminLang() === "hi";
  const [username, setUsername] = useState("");
  const [mobileDigits, setMobileDigits] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleGeneratePassword = () => {
    const randomStr = Math.random().toString(36).substring(2, 8);
    setPassword(`Dukaan#${randomStr}!`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const clean10 = mobileDigits.replace(/\D/g, "").slice(-10);
    if (clean10.length !== 10) {
      setError(hi ? "कृपया 10 अंकों का मोबाइल नंबर दर्ज करें" : "Please enter a valid 10-digit mobile number / कृपया 10 अंकों का मोबाइल नंबर दर्ज करें");
      setLoading(false);
      return;
    }

    try {
      const payload: ProvisionMerchantPayload = {
        username: username.trim(),
        mobile_number: `+91${clean10}`,
        email: email.trim() || undefined,
        initial_password: password,
      };

      await adminApi.provisionMerchant(payload, token);
      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
        onClose();
        setSuccess(false);
      }, 1500);
    } catch (err: any) {
      const data = err.response?.data;
      let msg = hi ? "मर्चेंट ऑनबोर्ड करने में विफल" : "Failed to onboard merchant / व्यापारी ऑनबोर्ड करने में विफल";
      if (typeof data === "string") {
        msg = data;
      } else if (data?.mobile_number) {
        msg = Array.isArray(data.mobile_number) ? data.mobile_number[0] : String(data.mobile_number);
      } else if (data?.username) {
        msg = Array.isArray(data.username) ? data.username[0] : String(data.username);
      } else if (data?.email) {
        msg = Array.isArray(data.email) ? data.email[0] : String(data.email);
      } else if (data?.initial_password) {
        msg = Array.isArray(data.initial_password) ? data.initial_password[0] : String(data.initial_password);
      } else if (data?.detail) {
        msg = String(data.detail);
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-lg w-full max-w-xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="px-6 py-3.5 bg-[#0F172A] text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-semibold tracking-tight">{hi ? "नया मर्चेंट जोड़ें" : "Onboard New Merchant Tenant"}</h2>
          </div>
          <button onClick={onClose} aria-label={hi ? "बंद करें" : "Close"} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{hi ? "मर्चेंट सफलतापूर्वक जुड़ गया! लॉगिन की जानकारी भेज दी गई है।" : "Merchant onboarded successfully! Welcome credentials dispatched."}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Username */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                {hi ? "मर्चेंट यूज़रनेम *" : "Merchant Username *"}
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={hi ? "जैसे sharma_kirana" : "e.g. sharma_kirana"}
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] outline-none"
              />
            </div>

            {/* Mobile Number with fixed +91 */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                {hi ? "मोबाइल नंबर (10 अंक) *" : "Mobile Number (10 Digits) *"}
              </label>
              <div className="flex items-center rounded border border-slate-200 bg-slate-50 overflow-hidden focus-within:bg-white focus-within:border-[#1F5D42] focus-within:ring-1 focus-within:ring-[#1F5D42]">
                <span className="px-2.5 py-1.5 bg-slate-100 text-slate-700 font-mono font-bold text-xs border-r border-slate-200 select-none">
                  +91
                </span>
                <input
                  type="tel"
                  required
                  
                  value={mobileDigits}
                  onChange={(e) => setMobileDigits(normalizeIndianMobileInput(e.target.value))}
                  placeholder="9876543210"
                  className="w-full px-3 py-1.5 text-xs bg-transparent outline-none font-mono"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                {hi ? "ईमेल (वैकल्पिक)" : "Official Email (Optional)"}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={hi ? "merchant@example.com (वैकल्पिक)" : "merchant@example.com (optional)"}
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] outline-none"
              />
            </div>

            {/* Temporary Password */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                {hi ? "शुरुआती अस्थायी पासवर्ड *" : "Initial Temporary Password *"}
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-3 pr-14 py-1.5 text-xs font-mono bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] outline-none"
                />
                <button
                  type="button"
                  onClick={handleGeneratePassword}
                  className="absolute right-1 top-1 px-1.5 py-0.5 text-[10px] bg-white border border-slate-200 text-slate-600 rounded hover:text-slate-900 flex items-center gap-1"
                >
                  <RefreshCw className="w-2.5 h-2.5" />
                  <span>{hi ? "बनाएं" : "Gen"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* WhatsApp Dispatch Notice */}
          <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded flex items-start gap-2.5 text-xs text-emerald-900">
            <Send className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">{hi ? "लॉगिन जानकारी अपने-आप भेजी जाएगी:" : "Automated Credential Dispatch:"}</span>
              <p className="text-slate-600 text-[11px]">
                {hi ? (
                  <>
                    बनाने के बाद मर्चेंट पर <code>must_change_password=True</code> लग जाएगा और पहले लॉगिन पर उससे अपना स्थायी पासवर्ड सेट करने को कहा जाएगा।
                  </>
                ) : (
                  <>
                    Upon creation, the merchant will be flagged with <code>must_change_password=True</code>{" "}
                    and prompted to set their permanent password on first login.
                  </>
                )}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-slate-200 text-slate-700 text-xs font-medium rounded hover:bg-slate-50 transition-colors"
            >
              {hi ? "रद्द करें" : "Cancel"}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-[#1F5D42] text-white text-xs font-semibold rounded hover:bg-[#164430] shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? (hi ? "बनाया जा रहा है..." : "Provisioning...") : (hi ? "मर्चेंट बनाएं" : "Provision Merchant")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
