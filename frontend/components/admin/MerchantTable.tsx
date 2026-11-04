"use client";

import React, { useState } from "react";
import { QrCode, RefreshCw, Power, PowerOff, ShieldCheck, Clock, Ban, Trash2, KeyRound, Download, X, CheckCircle2, Edit2, Phone } from "lucide-react";
import { adminApi } from "@/lib/api/admin";

export interface MerchantShopItem {
  id: number;
  shopId: number;
  merchantId?: number;
  shopName: string;
  merchantName: string;
  mobileNumber: string;
  city: string;
  status: "ACTIVE" | "PENDING_PASSWORD_CHANGE" | "SUSPENDED" | "DEACTIVATED";
  catalogItemsCount: number;
  monthlyVolume: string;
  publicSlug: string;
}

interface MerchantTableProps {
  merchants: MerchantShopItem[];
  onRefresh?: () => void;
  token?: string;
}

export function MerchantTable({ merchants, onRefresh, token }: MerchantTableProps) {
  const [filter, setFilter] = useState<string>("ALL");
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Reset Password State
  const [resettingMerchant, setResettingMerchant] = useState<MerchantShopItem | null>(null);
  const [tempPassword, setTempPassword] = useState<string>("");
  const [resetLoading, setResetLoading] = useState<boolean>(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<boolean>(false);

  // Edit Mobile State
  const [editingMerchant, setEditingMerchant] = useState<MerchantShopItem | null>(null);
  const [editMobileDigits, setEditMobileDigits] = useState<string>("");
  const [editMobileLoading, setEditMobileLoading] = useState<boolean>(false);
  const [editMobileError, setEditMobileError] = useState<string | null>(null);
  const [editMobileSuccess, setEditMobileSuccess] = useState<boolean>(false);

  const handleOpenEditMobile = (m: MerchantShopItem) => {
    setEditingMerchant(m);
    setEditMobileDigits(m.mobileNumber.replace(/\D/g, "").slice(-10));
    setEditMobileError(null);
    setEditMobileSuccess(false);
  };

  const handleConfirmEditMobile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMerchant) return;
    const clean10 = editMobileDigits.replace(/\D/g, "").slice(-10);
    if (clean10.length !== 10) {
      setEditMobileError("Please enter a valid 10-digit mobile number.");
      return;
    }
    setEditMobileLoading(true);
    setEditMobileError(null);
    try {
      const targetId = editingMerchant.merchantId || editingMerchant.id;
      await adminApi.updateMerchantMobile(targetId, `+91${clean10}`, token);
      setEditMobileSuccess(true);
      setTimeout(() => {
        setEditingMerchant(null);
        setEditMobileSuccess(false);
        onRefresh?.();
      }, 1200);
    } catch (err: any) {
      const msg = err.response?.data?.mobile_number?.[0] || err.response?.data?.detail || (err.response?.data ? JSON.stringify(err.response.data) : err.message);
      setEditMobileError(msg);
    } finally {
      setEditMobileLoading(false);
    }
  };

  const generateRandomPassword = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
    let pwd = "Dukaan@";
    for (let i = 0; i < 4; i++) {
      pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return pwd;
  };

  const handleOpenReset = (m: MerchantShopItem) => {
    setResettingMerchant(m);
    setTempPassword(generateRandomPassword());
    setResetError(null);
    setResetSuccess(false);
  };

  const handleDownloadCredentials = (m: MerchantShopItem, pwd: string) => {
    const content = [
      "========================================================",
      "DUKANDAAR HYPERLOCAL GROCERY PLATFORM",
      "MERCHANT ACCOUNT LOGIN CREDENTIALS",
      "========================================================",
      `Shop Name       : ${m.shopName}`,
      `Merchant Name   : ${m.merchantName}`,
      `Registered Mobile: ${m.mobileNumber}`,
      `Temporary Pass  : ${pwd}`,
      `Login URL       : http://localhost:3000/merchant/login`,
      `Issued By       : Super Admin`,
      `Generated At    : ${new Date().toLocaleString("en-IN")}`,
      "--------------------------------------------------------",
      "INSTRUCTIONS FOR MERCHANT:",
      "1. Open the login link above in your browser.",
      "2. Log in using your registered mobile number and this temporary password.",
      "3. You will be prompted to set your own secure permanent password.",
      "4. Store your credentials safely and do not share them.",
      "========================================================",
    ].join("\n");

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `merchant_credentials_${m.mobileNumber.replace(/\D/g, "")}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resettingMerchant) return;
    if (!tempPassword || tempPassword.trim().length < 8) {
      setResetError("Temporary password must be at least 8 characters.");
      return;
    }
    setResetLoading(true);
    setResetError(null);
    try {
      const targetId = resettingMerchant.merchantId || resettingMerchant.id;
      await adminApi.resetMerchantPassword(targetId, tempPassword.trim(), token);
      setResetSuccess(true);
      // Auto-trigger download for convenient delivery
      handleDownloadCredentials(resettingMerchant, tempPassword.trim());
      onRefresh?.();
    } catch (err: any) {
      setResetError(err.response?.data?.password?.[0] || err.response?.data?.detail || err.message);
    } finally {
      setResetLoading(false);
    }
  };

  const filteredMerchants = merchants.filter((m) => {
    if (filter === "ALL") return true;
    if (filter === "ACTIVE") return m.status === "ACTIVE";
    if (filter === "PENDING") return m.status === "PENDING_PASSWORD_CHANGE";
    if (filter === "SUSPENDED") return m.status === "SUSPENDED" || m.status === "DEACTIVATED";
    return true;
  });

  const handleDeactivate = async (shopId: number) => {
    setActionLoadingId(shopId);
    try {
      await adminApi.deactivateShop(shopId, token);
      onRefresh?.();
    } catch (e: any) {
      alert(`Deactivation failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReactivate = async (shopId: number) => {
    setActionLoadingId(shopId);
    try {
      await adminApi.reactivateShop(shopId, token);
      onRefresh?.();
    } catch (e: any) {
      alert(`Reactivation failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRegenerateQR = async (shopId: number) => {
    setActionLoadingId(shopId);
    try {
      await adminApi.regenerateShopQR(shopId, token);
      alert("QR code regenerated with fresh public slug.");
      onRefresh?.();
    } catch (e: any) {
      alert(`Regenerate QR failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDeleteShop = async (shopId: number, shopName: string) => {
    if (!window.confirm(`⚠️ DANGER: Permanently delete shop "${shopName}"? This action cannot be undone and will permanently delete all shop data, products, and orders.`)) {
      return;
    }
    setActionLoadingId(shopId);
    try {
      await adminApi.deleteShop(shopId, token);
      alert(`Shop "${shopName}" permanently deleted.`);
      onRefresh?.();
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };


  return (
    <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
      {/* Table Header Control Panel */}
      <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/50">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Tenant Governance Directory</h2>
          <p className="text-xs text-slate-500">
            Active merchant nodes, authentication status, and shop security controls.
          </p>
        </div>

        {/* Filter Chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "ALL"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            All Merchants ({merchants.length})
          </button>
          <button
            onClick={() => setFilter("ACTIVE")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "ACTIVE"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setFilter("PENDING")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "PENDING"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Pending Password Reset
          </button>
          <button
            onClick={() => setFilter("SUSPENDED")}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded ${
              filter === "SUSPENDED"
                ? "bg-[#0F172A] text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Suspended
          </button>
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#0F172A] text-slate-100 text-[10px] uppercase font-bold tracking-wider">
              <th className="py-2.5 px-3">Shop & Tenant ID</th>
              <th className="py-2.5 px-3">Merchant / Contact</th>
              <th className="py-2.5 px-3">Location</th>
              <th className="py-2.5 px-3">Catalog Items</th>
              <th className="py-2.5 px-3">30-Day Sales</th>
              <th className="py-2.5 px-3">Operational State</th>
              <th className="py-2.5 px-3 text-right">Governance Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredMerchants.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  No merchants found matching the selected filter.
                </td>
              </tr>
            ) : (
              filteredMerchants.map((m) => {
                const isLoading = actionLoadingId === (m.shopId ?? m.id);
                return (
                  <tr key={m.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                      <div className="flex items-center gap-1.5">
                        <QrCode className="w-3.5 h-3.5 text-slate-400" />
                        {m.publicSlug ? (
                          <span>QR-{m.publicSlug.slice(0, 8).toUpperCase()}</span>
                        ) : (
                          <span className="text-[10px] bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 rounded font-sans font-medium">
                            Setup Pending
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900">{m.shopName}</div>
                      <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500">
                        <span>{m.mobileNumber}</span>
                        <button
                          type="button"
                          onClick={() => handleOpenEditMobile(m)}
                          title="Edit Merchant Mobile Number / मोबाइल नंबर बदलें"
                          className="p-0.5 rounded text-slate-400 hover:text-emerald-700 hover:bg-emerald-50 transition-colors"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{m.city}</td>
                    <td className="py-2.5 px-3 tabular-nums font-medium text-slate-800">
                      {m.catalogItemsCount} SKUs
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900 tabular-nums">
                      {m.monthlyVolume}
                    </td>
                    <td className="py-2.5 px-3">
                      {m.status === "ACTIVE" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                          Active
                        </span>
                      ) : m.status === "PENDING_PASSWORD_CHANGE" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800">
                          <Clock className="w-3 h-3 text-amber-600" />
                          Pending Pwd
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-800">
                          <Ban className="w-3 h-3 text-red-600" />
                          Suspended
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        {/* Reset Password */}
                        <button
                          onClick={() => handleOpenReset(m)}
                          disabled={isLoading}
                          title="Reset Merchant Password & Download Credentials"
                          className="p-1 rounded border border-amber-200 bg-amber-50 hover:bg-amber-600 text-amber-700 hover:text-white transition-colors"
                        >
                          <KeyRound className="w-3.5 h-3.5" />
                        </button>

                        {/* Regenerate QR */}
                        {m.shopId ? (
                          <button
                            onClick={() => handleRegenerateQR(m.shopId!)}
                            disabled={isLoading}
                            title="Rotate QR Slug"
                            className="p-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-600"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                          </button>
                        ) : null}

                        {/* Deactivate or Reactivate */}
                        {m.shopId ? (
                          m.status === "ACTIVE" ? (
                            <button
                              onClick={() => handleDeactivate(m.shopId!)}
                              disabled={isLoading}
                              className="px-2 py-1 rounded text-[10px] font-bold bg-red-50 border border-red-200 text-red-700 hover:bg-red-600 hover:text-white transition-colors"
                            >
                              Deactivate
                            </button>
                          ) : (
                            <button
                              onClick={() => handleReactivate(m.shopId!)}
                              disabled={isLoading}
                              className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-50 border border-emerald-200 text-emerald-800 hover:bg-emerald-600 hover:text-white transition-colors"
                            >
                              Reactivate
                            </button>
                          )
                        ) : null}

                        {/* Permanent Delete */}
                        {m.shopId ? (
                          <button
                            onClick={() => handleDeleteShop(m.shopId!, m.shopName)}
                            disabled={isLoading}
                            title="Permanently Delete Shop"
                            className="p-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-600 text-rose-600 hover:text-white transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Super Admin Merchant Password Reset Modal */}
      {resettingMerchant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white border border-[#ddd6ca] rounded-2xl w-full max-w-md overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-700">
                  <KeyRound className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold font-display text-[#123324]">
                    Reset Merchant Password
                  </h3>
                  <p className="text-[11px] text-[#6d756f]">
                    {resettingMerchant.shopName} · {resettingMerchant.mobileNumber}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setResettingMerchant(null)}
                className="text-[#6d756f] hover:text-[#123324] p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {resetError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
                {resetError}
              </div>
            )}

            {resetSuccess ? (
              <div className="space-y-4 text-xs">
                <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 font-bold text-sm text-emerald-900">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    Password Reset Successfully!
                  </div>
                  <p className="text-emerald-700">
                    The merchant's temporary password has been updated in the database.
                  </p>
                  <div className="p-2.5 bg-white rounded-lg border border-emerald-200 font-mono text-emerald-900 flex items-center justify-between">
                    <span>Temp Pass: <strong>{tempPassword}</strong></span>
                    <span className="text-[10px] text-emerald-600 font-sans font-semibold">Ready</span>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleDownloadCredentials(resettingMerchant, tempPassword)}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#1F5D42] text-white font-bold hover:bg-[#123324] transition shadow-xs"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Credentials (.txt)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setResettingMerchant(null)}
                    className="px-4 py-2.5 rounded-xl border border-[#ddd6ca] bg-[#FAF8F3] hover:bg-[#eee9df] text-[#123324] font-semibold transition"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleConfirmReset} className="space-y-4 text-xs">
                <div className="p-3 rounded-xl bg-[#FAF8F3] border border-[#eee9df] space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-[#6d756f]">Shop Name:</span>
                    <strong className="text-[#123324]">{resettingMerchant.shopName}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d756f]">Merchant Name:</span>
                    <strong className="text-[#123324]">{resettingMerchant.merchantName}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d756f]">Registered Mobile:</span>
                    <strong className="font-mono text-[#123324]">{resettingMerchant.mobileNumber}</strong>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="font-bold text-[#123324]">
                      New Temporary Password <span className="text-red-500">*</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => setTempPassword(generateRandomPassword())}
                      className="text-[11px] text-[#1F5D42] hover:underline font-semibold"
                    >
                      Regenerate
                    </button>
                  </div>
                  <input
                    type="text"
                    required
                    value={tempPassword}
                    onChange={(e) => setTempPassword(e.target.value)}
                    placeholder="Enter min 8-character temporary password"
                    className="w-full px-3 py-2 border border-[#ddd6ca] rounded-xl outline-none focus:border-[#1F5D42] font-mono text-sm"
                  />
                  <p className="text-[10px] text-[#6d756f] mt-1">
                    Merchant will be prompted to set their permanent password upon logging in.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#eee9df]">
                  <button
                    type="button"
                    onClick={() => setResettingMerchant(null)}
                    className="px-3.5 py-2 border border-[#ddd6ca] rounded-xl hover:bg-[#FAF8F3] font-semibold text-[#6d756f]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={resetLoading}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#1F5D42] text-white font-bold rounded-xl hover:bg-[#123324] disabled:opacity-50 transition shadow-xs"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>{resetLoading ? "Setting Password…" : "Set Password & Download .txt"}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Super Admin Edit Merchant Mobile Modal */}
      {editingMerchant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white border border-[#ddd6ca] rounded-2xl w-full max-w-md overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700">
                  <Phone className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold font-display text-[#123324]">
                    Edit Merchant Mobile Number
                  </h3>
                  <p className="text-[11px] text-[#6d756f]">
                    {editingMerchant.shopName} · Merchant User #{editingMerchant.id}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEditingMerchant(null)}
                className="text-[#6d756f] hover:text-[#123324] p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {editMobileError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
                {editMobileError}
              </div>
            )}

            {editMobileSuccess ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl space-y-2 text-xs">
                <div className="flex items-center gap-2 font-bold text-sm text-emerald-900">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  Mobile Number Updated Successfully!
                </div>
                <p className="text-emerald-700">
                  The merchant can now log in using +91{editMobileDigits.slice(-10)}.
                </p>
              </div>
            ) : (
              <form onSubmit={handleConfirmEditMobile} className="space-y-4 text-xs">
                <div className="p-3 rounded-xl bg-[#FAF8F3] border border-[#eee9df] space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-[#6d756f]">Shop Name:</span>
                    <strong className="text-[#123324]">{editingMerchant.shopName}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d756f]">Merchant Name:</span>
                    <strong className="text-[#123324]">{editingMerchant.merchantName}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6d756f]">Current Mobile:</span>
                    <strong className="font-mono text-[#123324]">{editingMerchant.mobileNumber}</strong>
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-[#123324] mb-1">
                    New 10-Digit Mobile Number <span className="text-red-500">*</span>
                  </label>
                  <div className="flex items-center rounded-xl border border-[#ddd6ca] bg-white overflow-hidden focus-within:border-[#1F5D42] focus-within:ring-1 focus-within:ring-[#1F5D42]">
                    <span className="px-3 py-2 bg-[#FAF8F3] text-slate-700 font-mono font-bold text-xs border-r border-[#ddd6ca] select-none">
                      +91
                    </span>
                    <input
                      type="tel"
                      required
                      maxLength={10}
                      value={editMobileDigits}
                      onChange={(e) => setEditMobileDigits(e.target.value.replace(/\D/g, "").slice(0, 10))}
                      placeholder="9876543210"
                      className="w-full px-3 py-2 text-sm font-mono bg-transparent outline-none"
                    />
                  </div>
                  <p className="text-[10px] text-[#6d756f] mt-1">
                    Enter the 10-digit number without 0 or +91 prefix.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#eee9df]">
                  <button
                    type="button"
                    onClick={() => setEditingMerchant(null)}
                    className="px-3.5 py-2 border border-[#ddd6ca] rounded-xl hover:bg-[#FAF8F3] font-semibold text-[#6d756f]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={editMobileLoading}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#1F5D42] text-white font-bold rounded-xl hover:bg-[#123324] disabled:opacity-50 transition shadow-xs"
                  >
                    <Phone className="w-3.5 h-3.5" />
                    <span>{editMobileLoading ? "Saving…" : "Save New Number"}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
