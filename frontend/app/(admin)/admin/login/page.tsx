"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  ShieldCheck,
  Lock,
  Mail,
  Eye,
  EyeOff,
  Key,
  RefreshCw,
  Usb,
  MessageSquare,
  AlertCircle,
  HelpCircle,
  PhoneCall,
  CheckCircle2,
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
  const [recoveryModalOpen, setRecoveryModalOpen] = useState(false);
  const [recoveryContact, setRecoveryContact] = useState("");
  const [recoveryChannel, setRecoveryChannel] = useState<"EMAIL" | "SMS">("EMAIL");
  const [recoveryStatus, setRecoveryStatus] = useState<string | null>(null);
  const [recoveryLoading, setRecoveryLoading] = useState(false);

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
        "Invalid credentials or insufficient Super Admin privileges.";
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
      setRecoveryStatus("Recovery token dispatched. Check your security inbox/SMS.");
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        "Recovery request failed. Verify your registered identifier.";
      setRecoveryStatus(`Error: ${detail}`);
    } finally {
      setRecoveryLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100 flex flex-col font-sans relative overflow-x-hidden selection:bg-[#1F5D42] selection:text-white">
      {/* Radial Ambient Glow */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#1F5D42]/20 via-[#0F172A] to-[#060E20] z-0" />

      {/* Top Security Status Header */}
      <header className="w-full px-6 flex justify-between items-center border-b border-slate-800 bg-[#0B1326]/90 backdrop-blur-md sticky top-0 h-16 z-30 shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-[#95D4B2] shadow-inner">
            <Shield className="w-5 h-5 text-[#95D4B2]" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold tracking-tight text-white">DukaanQR Sovereign Portal</span>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#95D4B2] animate-pulse" />
              <span className="text-[10px] font-mono tracking-wider text-slate-400 uppercase">
                Level-4 Cryptographic Auth Cluster
              </span>
            </div>
          </div>
        </div>

        {/* Live Telemetry Badges */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-slate-800/80 border border-slate-700 rounded-full text-xs text-slate-200">
            <ShieldCheck className="w-4 h-4 text-[#95D4B2]" />
            <span>System Operational • Level 4 Auth Node</span>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-[#1F5D42]/20 border border-[#1F5D42]/40 rounded-full text-xs text-[#95D4B2]">
            <Usb className="w-3.5 h-3.5" />
            <span>FIDO2 / WebAuthn Ready</span>
          </div>
          <button
            onClick={() => setRecoveryModalOpen(true)}
            className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-amber-500/50 text-amber-400 hover:bg-amber-500/10 transition-colors text-xs font-semibold"
            type="button"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Emergency Recovery</span>
          </button>
        </div>
      </header>

      {/* Main Authentication Canvas */}
      <main className="flex-1 flex items-center justify-center px-4 py-12 relative z-10">
        <div className="w-full max-w-lg mx-auto">
          {/* Main Card */}
          <div className="bg-[#171F33]/90 backdrop-blur-xl border border-slate-700/80 rounded-2xl shadow-2xl p-6 sm:p-8 relative">
            {/* Top Border Accent Line */}
            <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-transparent via-[#1F5D42] to-transparent rounded-t-2xl" />

            {/* Emblem & Titles */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#1F5D42]/20 border border-[#1F5D42]/50 text-[#95D4B2] mb-3 shadow-[0_0_24px_rgba(31,93,66,0.35)]">
                <ShieldCheck className="w-8 h-8" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Super Admin Portal</h1>
              <p className="text-xs text-slate-400 mt-1">Enterprise Network Governance & Sovereign Key Access</p>
              <div className="inline-flex items-center gap-1.5 mt-2.5 px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-[10px] text-slate-300 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-[#95D4B2] animate-ping" />
                <span>ROOT INSTANCE: AP-SOUTH-IND-1</span>
              </div>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="mb-5 p-3 rounded-lg bg-red-950/60 border border-red-500/50 text-red-200 text-xs flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{errorMessage}</span>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Field 1: Identifier */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <label htmlFor="admin-identifier" className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <span>Administrative Identifier</span>
                  </label>
                  <span className="text-[10px] font-medium text-[#95D4B2] bg-[#1F5D42]/20 border border-[#1F5D42]/30 px-2 py-0.5 rounded">
                    SSO / GovID Enabled
                  </span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="admin-identifier"
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="admin@dukaanqr.internal or +91 98XXX XXXXX"
                    className="w-full h-11 pl-10 pr-4 bg-[#0F172A] border border-slate-700 text-white placeholder:text-slate-500 rounded-lg text-xs focus:border-[#95D4B2] focus:ring-1 focus:ring-[#95D4B2] focus:outline-none transition-all"
                  />
                </div>
              </div>

              {/* Field 2: Passphrase */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <label htmlFor="admin-passphrase" className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <span>Master Passphrase</span>
                  </label>
                  <span className="text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                    HSM Backed
                  </span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="admin-passphrase"
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter master passphrase"
                    className="w-full h-11 pl-10 pr-10 bg-[#0F172A] border border-slate-700 text-white placeholder:text-slate-500 rounded-lg text-xs focus:border-[#95D4B2] focus:ring-1 focus:ring-[#95D4B2] focus:outline-none transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Field 3: Remember Me & Recovery Link */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none text-slate-300">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded bg-[#0F172A] border-slate-700 text-[#1F5D42] focus:ring-[#1F5D42]"
                  />
                  <span>Remember workstation for 30 days</span>
                </label>
                <button
                  type="button"
                  onClick={() => setRecoveryModalOpen(true)}
                  className="text-[#95D4B2] hover:underline text-xs"
                >
                  Forgot Passphrase?
                </button>
              </div>

              {/* Field 4: Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full h-11 bg-[#1F5D42] hover:bg-[#277553] disabled:opacity-60 text-white font-semibold rounded-lg flex items-center justify-center gap-2 transition-all shadow-[0_0_16px_rgba(31,93,66,0.35)] text-sm cursor-pointer"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Authenticating Sovereign Node...</span>
                    </>
                  ) : (
                    <>
                      <Key className="w-4 h-4" />
                      <span>Authenticate Sovereign Node</span>
                    </>
                  )}
                </button>
              </div>

              {/* Step-Up Divider */}
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-800" />
                </div>
                <div className="relative flex justify-center text-[10px] tracking-wider uppercase">
                  <span className="bg-[#171F33] px-2 text-slate-500">Or Step-Up Validation</span>
                </div>
              </div>

              {/* Secondary Gateways */}
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => alert("Hardware Security Key: Insert YubiKey and touch sensor when prompted.")}
                  className="h-9 px-3 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg flex items-center justify-center gap-2 text-xs transition-colors"
                >
                  <Usb className="w-3.5 h-3.5 text-[#95D4B2]" />
                  <span className="truncate">YubiKey FIDO2</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRecoveryModalOpen(true)}
                  className="h-9 px-3 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg flex items-center justify-center gap-2 text-xs transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
                  <span className="truncate">WhatsApp OTP Escrow</span>
                </button>
              </div>

              {/* Field 5: Security Assurance Block */}
              <div className="mt-5 pt-3.5 border-t border-slate-800 space-y-2 bg-[#0F172A]/80 rounded-lg p-3 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <div className="flex items-center gap-1.5 text-[#95D4B2] font-semibold text-[11px]">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>256-BIT AES ENCRYPTION</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                      TLS 1.3
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-[#1F5D42]/20 border border-[#1F5D42]/30 text-[#95D4B2]">
                      SOC2 TYPE II
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1 border-t border-slate-800">
                  <span>Current Session: BLR-DC-04 | 103.21.244.0/24</span>
                  <span className="text-[#95D4B2] flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#95D4B2]" />
                    Geo-Guard: IN-KA
                  </span>
                </div>
              </div>
            </form>
          </div>

          {/* Footer Contacts */}
          <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-slate-400 text-xs px-2">
            <div className="flex items-center gap-1.5">
              <PhoneCall className="w-3.5 h-3.5 text-slate-500" />
              <span>DukaanQR Network SOC: +91 80 4900 2000</span>
            </div>
            <button
              onClick={() => setRecoveryModalOpen(true)}
              className="text-amber-400 hover:underline flex items-center gap-1"
            >
              <span>Emergency Access Recovery</span>
            </button>
          </div>
        </div>
      </main>

      {/* Emergency Recovery Modal */}
      {recoveryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-[#171F33] border border-slate-700 rounded-xl max-w-md w-full p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-amber-400" />
                <h2 className="text-base font-bold text-white">Emergency Self-Recovery</h2>
              </div>
              <button
                onClick={() => {
                  setRecoveryModalOpen(false);
                  setRecoveryStatus(null);
                }}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSelfRecovery} className="mt-4 space-y-3">
              <p className="text-xs text-slate-300 leading-relaxed">
                Dispatch an out-of-band one-time verification challenge via registered administrator email or phone.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Channel</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRecoveryChannel("EMAIL")}
                    className={`py-1.5 text-xs rounded border ${
                      recoveryChannel === "EMAIL"
                        ? "bg-[#1F5D42] border-[#95D4B2] text-white"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    Email OTP
                  </button>
                  <button
                    type="button"
                    onClick={() => setRecoveryChannel("SMS")}
                    className={`py-1.5 text-xs rounded border ${
                      recoveryChannel === "SMS"
                        ? "bg-[#1F5D42] border-[#95D4B2] text-white"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    SMS / WhatsApp OTP
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Registered Contact (Email or Mobile)
                </label>
                <input
                  type="text"
                  required
                  value={recoveryContact}
                  onChange={(e) => setRecoveryContact(e.target.value)}
                  placeholder="admin@platform.com or +919876543210"
                  className="w-full h-10 px-3 bg-[#0F172A] border border-slate-700 rounded text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-[#95D4B2]"
                />
              </div>

              {recoveryStatus && (
                <div
                  className={`p-2.5 rounded text-xs ${
                    recoveryStatus.startsWith("Error")
                      ? "bg-red-950/60 border border-red-500/50 text-red-300"
                      : "bg-emerald-950/60 border border-emerald-500/50 text-emerald-300 flex items-center gap-2"
                  }`}
                >
                  {!recoveryStatus.startsWith("Error") && <CheckCircle2 className="w-4 h-4 shrink-0" />}
                  <span>{recoveryStatus}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setRecoveryModalOpen(false);
                    setRecoveryStatus(null);
                  }}
                  className="px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={recoveryLoading}
                  className="px-4 py-1.5 bg-[#1F5D42] hover:bg-[#277553] text-white font-semibold rounded text-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-60"
                >
                  {recoveryLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Dispatch OTP</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="w-full px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-3 border-t border-slate-800 bg-[#060E20] text-slate-400 text-xs relative z-20">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white tracking-tight">DukaanQR</span>
          <span>|</span>
          <span>© 2025 DukaanQR Enterprise Infrastructure. 256-bit AES Cryptographic Security Layer Active.</span>
        </div>
        <div className="flex items-center gap-4 text-[11px]">
          <span className="text-slate-500 hover:text-slate-300 cursor-pointer">Hardware Token Support</span>
          <span className="text-slate-500 hover:text-slate-300 cursor-pointer">Security Audit Log</span>
          <span className="text-slate-500 hover:text-slate-300 cursor-pointer">Privacy & Sovereign Guard</span>
        </div>
      </footer>
    </div>
  );
}
