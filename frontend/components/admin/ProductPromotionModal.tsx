"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Verified,
  Network,
  Barcode,
  IndianRupee,
  CloudUpload,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Building2,
  Package,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";

export interface ShopProductPromotionTarget {
  id: number;
  name: string;
  brand?: string;
  category?: number | string;
  description?: string;
  barcode?: string;
  price?: string | number;
  shopName?: string;
  shopId?: number;
}

interface ProductPromotionModalProps {
  isOpen: boolean;
  onClose: () => void;
  product?: ShopProductPromotionTarget | null;
  onSuccess?: (promotedData: any) => void;
}

export function ProductPromotionModal({
  isOpen,
  onClose,
  product,
  onSuccess,
}: ProductPromotionModalProps) {
  const [productIdInput, setProductIdInput] = useState<string>("");
  const [name, setName] = useState<string>("");
  const [brand, setBrand] = useState<string>("");
  const [category, setCategory] = useState<string>("1");
  const [description, setDescription] = useState<string>("");
  const [barcode, setBarcode] = useState<string>("");
  const [unitPrice, setUnitPrice] = useState<string>("");
  const [enforceCeiling, setEnforceCeiling] = useState<boolean>(true);
  const [broadcastNotification, setBroadcastNotification] = useState<boolean>(true);

  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      setProductIdInput(String(product.id));
      setName(product.name || "");
      setBrand(product.brand || "");
      setCategory(typeof product.category === "number" ? String(product.category) : "1");
      setDescription(product.description || "");
      setBarcode(product.barcode || "");
      setUnitPrice(product.price ? String(product.price) : "");
    } else {
      setProductIdInput("");
      setName("");
      setBrand("");
      setCategory("1");
      setDescription("");
      setBarcode("");
      setUnitPrice("");
    }
    setErrorMessage(null);
    setSuccessMessage(null);
  }, [product, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setLoading(true);

    const targetId = Number(productIdInput);
    if (!targetId || isNaN(targetId)) {
      setErrorMessage("Please specify a valid numeric Shop Product ID.");
      setLoading(false);
      return;
    }

    try {
      const payload: {
        name?: string;
        brand?: string;
        description?: string;
        category?: number;
      } = {};

      if (name.trim()) payload.name = name.trim();
      if (brand.trim()) payload.brand = brand.trim();
      if (description.trim()) payload.description = description.trim();
      const parsedCat = parseInt(category, 10);
      if (!isNaN(parsedCat)) payload.category = parsedCat;

      const result = await adminApi.promoteShopProduct(targetId, payload);
      setSuccessMessage(
        `Successfully promoted to Master SKU #${result.master_product?.id || result.id || targetId}! Live sync broadcast sent.`
      );
      onSuccess?.(result);
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        "Failed to promote shop product to master catalog. Verify product exists.";
      setErrorMessage(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0F172A]/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl animate-in zoom-in-95 duration-150 flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#0F172A] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-[#1F5D42] flex items-center justify-center text-white shadow-sm">
              <Verified className="w-5 h-5 text-emerald-300" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white leading-tight">
                Promote Product to Global Master Catalog
              </h2>
              <p className="text-[11px] text-slate-400 font-normal leading-tight mt-0.5">
                Review and approve merchant shop product for network-wide master listing
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Provenance Banner */}
        <div className="px-6 py-2.5 bg-amber-50/60 border-b border-amber-200/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-[#78350F]">
            <Building2 className="w-4 h-4 text-amber-700 shrink-0" />
            <span>
              Origin:{" "}
              <strong className="font-semibold text-slate-800">
                {product?.shopName || "Merchant Store (Direct Ingestion)"}
              </strong>{" "}
              {product?.id ? `• Shop Product #${product.id}` : ""}
            </span>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 tracking-wider uppercase border border-emerald-300 self-start sm:self-auto">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
            Verified Catalog Lock
          </span>
        </div>

        {/* Messages */}
        {errorMessage && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="mx-6 mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Modal Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Target Shop Product ID */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Shop Product ID *
              </label>
              <div className="relative flex items-center">
                <Package className="w-4 h-4 absolute left-3 text-slate-400" />
                <input
                  type="number"
                  required
                  value={productIdInput}
                  onChange={(e) => setProductIdInput(e.target.value)}
                  placeholder="e.g. 104"
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] font-mono text-slate-900"
                />
              </div>
            </div>

            {/* Barcode / EAN */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Barcode / EAN-13
              </label>
              <div className="relative flex items-center">
                <Barcode className="w-4 h-4 absolute left-3 text-slate-400" />
                <input
                  type="text"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  placeholder="e.g. 8901262010052"
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] font-mono text-slate-900"
                />
              </div>
            </div>

            {/* Product Name */}
            <div className="sm:col-span-2">
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Master Product Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Amul Taaza Homogenised Toned Milk 1L"
                className="w-full px-3 py-1.5 text-xs font-semibold text-slate-900 bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42]"
              />
            </div>

            {/* Brand */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Brand / FMCG Principal *
              </label>
              <input
                type="text"
                required
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                placeholder="e.g. Amul / GCMMF"
                className="w-full px-3 py-1.5 text-xs text-slate-900 bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42]"
              />
            </div>

            {/* Category ID / Hierarchy */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Category (Master ID) *
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-1.5 text-xs text-slate-900 bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42]"
              >
                <option value="1">1 — Dairy & Cold Chain (Milk, Curd, Butter)</option>
                <option value="2">2 — Staples & Flours (Atta, Rice, Pulses)</option>
                <option value="3">3 — Edible Oils & Ghee</option>
                <option value="4">4 — Packaged & Instant Foods</option>
                <option value="5">5 — Beverages & Tea/Coffee</option>
                <option value="6">6 — Personal Care & Hygiene</option>
                <option value="7">7 — Household Cleaning & Essentials</option>
              </select>
            </div>

            {/* Description */}
            <div className="sm:col-span-2">
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Master Description & Packaging
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="High quality standard retail SKU with standardized packaging attributes."
                className="w-full px-3 py-1.5 text-xs text-slate-900 bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42]"
              />
            </div>

            {/* Unit Price */}
            <div>
              <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Verified MRP / Benchmark (₹)
              </label>
              <div className="relative flex items-center">
                <IndianRupee className="w-3.5 h-3.5 absolute left-3 text-slate-400" />
                <input
                  type="text"
                  value={unitPrice}
                  onChange={(e) => setUnitPrice(e.target.value)}
                  placeholder="56.00"
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded focus:bg-white focus:border-[#1F5D42] focus:ring-1 focus:ring-[#1F5D42] font-semibold text-slate-900"
                />
              </div>
            </div>

            {/* Pricing guardrail guidance */}
            <div className="flex flex-col justify-center text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-200">
              <span className="font-semibold text-slate-700">Anti-Gouging Ceiling Lock</span>
              <span>Protects local dukandaars while guaranteeing verified standard margins.</span>
            </div>
          </div>

          {/* Governance Checklist */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 text-xs">
            <div className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Governance & Distribution Controls
            </div>
            <label className="flex items-start gap-2 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={enforceCeiling}
                onChange={(e) => setEnforceCeiling(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-[#1F5D42] focus:ring-[#1F5D42]"
              />
              <span className="leading-snug">
                <strong>Enforce MRP Price Ceiling</strong> across all connected tenant shops.
              </span>
            </label>
            <label className="flex items-start gap-2 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={broadcastNotification}
                onChange={(e) => setBroadcastNotification(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-[#1F5D42] focus:ring-[#1F5D42]"
              />
              <span className="leading-snug">
                <strong>Broadcast live master update</strong> to merchant network via WhatsApp Sync Engine.
              </span>
            </label>
          </div>

          {/* Modal Footer Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-200">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 border border-slate-300 text-slate-700 text-xs font-semibold rounded hover:bg-slate-100 transition-colors"
            >
              Dismiss
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-[#1F5D42] hover:bg-[#164430] text-white text-xs font-semibold rounded shadow-sm flex items-center gap-2 transition-all cursor-pointer disabled:opacity-60"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Promoting to Master SKU...</span>
                </>
              ) : (
                <>
                  <CloudUpload className="w-3.5 h-3.5" />
                  <span>Promote to Master SKU</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
