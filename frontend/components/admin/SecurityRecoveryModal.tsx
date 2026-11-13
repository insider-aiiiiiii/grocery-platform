"use client";

import React, { useState } from "react";
import { ShieldCheck, KeyRound, Mail, Phone, CheckCircle2, AlertCircle } from "lucide-react";
import { useAdminLang } from "./useAdminLang";
import { adminApi } from "@/lib/api/admin";

interface SecurityRecoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SecurityRecoveryModal({ isOpen, onClose }: SecurityRecoveryModalProps) {
  const hi = useAdminLang() === "hi";
  const [tab, setTab] = useState<"self" | "admin">("self");
  const [channel, setChannel] = useState<"EMAIL" | "SMS">("EMAIL");
  const [contact, setContact] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [targetUserId, setTargetUserId] = useState<number | "">("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  if (!isOpen) return null;

  const handleRequestSelfRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      await adminApi.requestSelfRecovery({ channel, contact });
      setStep("confirm");
      setMsg({ text: hi ? "रिकवरी OTP आपके रजिस्टर्ड संपर्क पर भेज दिया गया है।" : "Recovery OTP dispatched to your registered contact channel.", type: "success" });
    } catch {
      setMsg({ text: hi ? "अनुरोध विफल रहा। संपर्क जानकारी जाँचें।" : "Request failed. Check contact value.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSelfRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      await adminApi.confirmSelfRecovery({ code: otpCode, new_password: newPassword, contact });
      setMsg({ text: hi ? "पासवर्ड सफलतापूर्वक रीसेट हो गया! अब आप लॉगिन कर सकते हैं।" : "Password successfully reset! You can now log in.", type: "success" });
      setTimeout(() => {
        onClose();
        setStep("request");
      }, 1500);
    } catch {
      setMsg({ text: hi ? "रिकवरी कोड गलत है या समाप्त हो चुका है।" : "Invalid or expired recovery code.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleRequestAdminReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      await adminApi.requestAdminReset({
        target_user_id: Number(targetUserId) || 0,
        channel,
        current_password: currentPassword,
      });
      setStep("confirm");
      setMsg({ text: hi ? "एडमिन रीसेट कोड संबंधित एडमिन को भेज दिया गया है।" : "Administrative reset code dispatched to target admin.", type: "success" });
    } catch {
      setMsg({ text: hi ? "एडमिन रीसेट अनुरोध विफल रहा। अपनी मौजूदा जानकारी जाँचें।" : "Administrative reset request failed. Verify current credentials.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAdminReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      await adminApi.confirmAdminReset({ code: otpCode, new_password: newPassword });
      setMsg({ text: hi ? "संबंधित एडमिन का पासवर्ड सफलतापूर्वक रीसेट हो गया।" : "Target administrator password successfully reset.", type: "success" });
      setTimeout(() => {
        onClose();
        setStep("request");
      }, 1500);
    } catch {
      setMsg({ text: hi ? "एडमिन कोड गलत है या समाप्त हो चुका है।" : "Invalid or expired administrative code.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#1F5D42]" />
            <h3 className="text-sm font-bold text-slate-900">{hi ? "सुपर एडमिन सुरक्षा और रिकवरी" : "Super Admin Security & Recovery"}</h3>
          </div>
          <button onClick={onClose} aria-label={hi ? "बंद करें" : "Close"} className="text-slate-400 hover:text-slate-600 font-bold text-sm">
            ✕
          </button>
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-slate-200 text-xs">
          <button
            onClick={() => { setTab("self"); setStep("request"); setMsg(null); }}
            className={`flex-1 py-2 font-medium border-b-2 ${
              tab === "self" ? "border-[#1F5D42] text-[#1F5D42]" : "border-transparent text-slate-500"
            }`}
          >
            {hi ? "खुद रिकवरी (एक्सेस खो गया)" : "Self-Recovery (Lost Access)"}
          </button>
          <button
            onClick={() => { setTab("admin"); setStep("request"); setMsg(null); }}
            className={`flex-1 py-2 font-medium border-b-2 ${
              tab === "admin" ? "border-[#1F5D42] text-[#1F5D42]" : "border-transparent text-slate-500"
            }`}
          >
            {hi ? "एडमिन रीसेट (साथी एडमिन)" : "Administrative Reset (Peer)"}
          </button>
        </div>

        {msg && (
          <div
            className={`p-2.5 rounded text-xs flex items-center gap-2 ${
              msg.type === "success"
                ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
                : "bg-rose-50 border border-rose-200 text-rose-800"
            }`}
          >
            {msg.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{msg.text}</span>
          </div>
        )}

        {/* Form rendering */}
        {tab === "self" ? (
          step === "request" ? (
            <form onSubmit={handleRequestSelfRecovery} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "कोड भेजने का तरीका" : "Dispatch Channel"}</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setChannel("EMAIL")}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 border rounded text-xs ${
                      channel === "EMAIL" ? "bg-slate-100 border-[#1F5D42] font-bold text-slate-900" : "border-slate-200 text-slate-600"
                    }`}
                  >
                    <Mail className="w-3.5 h-3.5" /> {hi ? "ईमेल" : "Email"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setChannel("SMS")}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 border rounded text-xs ${
                      channel === "SMS" ? "bg-slate-100 border-[#1F5D42] font-bold text-slate-900" : "border-slate-200 text-slate-600"
                    }`}
                  >
                    <Phone className="w-3.5 h-3.5" /> {hi ? "SMS / मोबाइल" : "SMS / Mobile"}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  {hi ? "रजिस्टर्ड" : "Registered"} {channel === "EMAIL" ? (hi ? "ईमेल पता" : "Email Address") : (hi ? "मोबाइल नंबर" : "Mobile Number")}
                </label>
                <input
                  type={channel === "EMAIL" ? "email" : "text"}
                  required
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  placeholder={channel === "EMAIL" ? "admin@platform.com" : "+919999000001"}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={onClose} className="px-3 py-1.5 border border-slate-200 rounded text-slate-600">
                  {hi ? "रद्द करें" : "Cancel"}
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 bg-[#1F5D42] text-white rounded font-semibold hover:bg-[#164430] disabled:opacity-50"
                >
                  {loading ? (hi ? "भेजा जा रहा है..." : "Dispatching...") : (hi ? "रिकवरी कोड भेजें" : "Send Recovery Code")}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleConfirmSelfRecovery} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "6 अंकों का OTP / कोड दर्ज करें" : "Enter 6-Digit OTP / Code"}</label>
                <input
                  type="text"
                  required
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder="123456"
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono tracking-widest text-center text-sm font-bold"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "नया मास्टर पासवर्ड" : "New Master Password"}</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setStep("request")} className="px-3 py-1.5 border border-slate-200 rounded text-slate-600">
                  {hi ? "वापस" : "Back"}
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 bg-[#1F5D42] text-white rounded font-semibold hover:bg-[#164430] disabled:opacity-50"
                >
                  {loading ? (hi ? "जाँच हो रही है..." : "Verifying...") : (hi ? "पासवर्ड रीसेट की पुष्टि करें" : "Confirm Password Reset")}
                </button>
              </div>
            </form>
          )
        ) : (
          step === "request" ? (
            <form onSubmit={handleRequestAdminReset} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "संबंधित सुपर एडमिन ID" : "Target Super Admin ID"}</label>
                <input
                  type="number"
                  required
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(parseInt(e.target.value))}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "कोड भेजने का तरीका" : "Dispatch Channel"}</label>
                <select
                  value={channel}
                  onChange={(e) => setChannel(e.target.value as "EMAIL" | "SMS")}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                >
                  <option value="EMAIL">{hi ? "ईमेल" : "Email"}</option>
                  <option value="SMS">{hi ? "SMS / व्हाट्सऐप" : "SMS / WhatsApp"}</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "आपका मौजूदा मास्टर पासवर्ड" : "Your Current Master Password"}</label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={onClose} className="px-3 py-1.5 border border-slate-200 rounded text-slate-600">
                  {hi ? "रद्द करें" : "Cancel"}
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 bg-[#1F5D42] text-white rounded font-semibold hover:bg-[#164430] disabled:opacity-50"
                >
                  {loading ? (hi ? "भेजा जा रहा है..." : "Submitting...") : (hi ? "एडमिन रीसेट शुरू करें" : "Initiate Administrative Reset")}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleConfirmAdminReset} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "रीसेट वेरिफिकेशन कोड" : "Reset Verification Code"}</label>
                <input
                  type="text"
                  required
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder={hi ? "साथी एडमिन को मिला कोड" : "Code received by peer"}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono text-center font-bold"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">{hi ? "संबंधित का नया पासवर्ड" : "New Target Password"}</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setStep("request")} className="px-3 py-1.5 border border-slate-200 rounded text-slate-600">
                  {hi ? "वापस" : "Back"}
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 bg-[#1F5D42] text-white rounded font-semibold hover:bg-[#164430] disabled:opacity-50"
                >
                  {loading ? (hi ? "पुष्टि हो रही है..." : "Confirming...") : (hi ? "रीसेट पूरा करें" : "Finalize Peer Reset")}
                </button>
              </div>
            </form>
          )
        )}
      </div>
    </div>
  );
}
