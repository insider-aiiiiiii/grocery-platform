"use client";

import React, { useState } from "react";
import { X, UserPlus, RefreshCw, CheckCircle2, AlertCircle, Send } from "lucide-react";
import { adminApi, ProvisionMerchantPayload } from "@/lib/api/admin";

interface OnboardMerchantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  token?: string;
}

export function OnboardMerchantModal({ isOpen, onClose, onSuccess, token }: OnboardMerchantModalProps) {
  const [username, setUsername] = useState("");
  const [mobileNumber, setMobileNumber] = useState("+91");
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

    try {
      const payload: ProvisionMerchantPayload = {
        username: username.trim(),
        mobile_number: mobileNumber.trim(),
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
      const msg = err.response?.data
        ? JSON.stringify(err.response.data)
        : err.message || "Failed to onboard merchant";
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
            <h2 className="text-sm font-semibold tracking-tight">Onboard New Merchant Tenant</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
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
              <span>Merchant onboarded successfully! Welcome credentials dispatched.</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Username */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Merchant Username *
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. sharma_kirana"
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] outline-none"
              />
            </div>

            {/* Mobile Number */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Mobile Number (+91) *
              </label>
              <input
                type="text"
                required
                value={mobileNumber}
                onChange={(e) => setMobileNumber(e.target.value)}
                placeholder="+919876543210"
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] outline-none font-mono"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Official Email (Optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="merchant@example.com (optional)"
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] outline-none"
              />
            </div>

            {/* Temporary Password */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Initial Temporary Password *
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
                  <span>Gen</span>
                </button>
              </div>
            </div>
          </div>

          {/* WhatsApp Dispatch Notice */}
          <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded flex items-start gap-2.5 text-xs text-emerald-900">
            <Send className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Automated Credential Dispatch:</span>
              <p className="text-slate-600 text-[11px]">
                Upon creation, the merchant will be flagged with <code>must_change_password=True</code>{" "}
                and prompted to set their permanent password on first login.
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
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-[#1F5D42] text-white text-xs font-semibold rounded hover:bg-[#164430] shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? "Provisioning..." : "Provision Merchant"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
