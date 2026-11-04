"use client";

import React from "react";
import { X, Package, ShieldCheck, Tag, Sparkles } from "lucide-react";

export interface MerchantProductDetailItem {
  id: number;
  name: string;
  brand?: string | null;
  category_name?: string | null;
  price?: string | number | null;
  mrp?: string | number | null;
  description?: string | null;
  image?: string | null;
  image_url?: string | null;
  effective_image?: string | null;
  sku?: string | null;
  is_available?: boolean;
  is_visible?: boolean;
  is_in_shop?: boolean;
}

interface MerchantProductDetailModalProps {
  product: MerchantProductDetailItem | null;
  onClose: () => void;
  lang?: "en" | "hi";
}

export function MerchantProductDetailModal({
  product,
  onClose,
  lang = "en",
}: MerchantProductDetailModalProps) {
  if (!product) return null;

  const isHi = lang === "hi";

  const imgSource = product.effective_image || product.image_url || product.image;
  const sellingPrice = parseFloat(String(product.price || "0"));
  const mrp = product.mrp ? parseFloat(String(product.mrp)) : null;
  const hasDiscount = mrp !== null && mrp > sellingPrice && sellingPrice > 0;
  const discountPct = hasDiscount ? Math.round(((mrp - sellingPrice) / mrp) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-3xl bg-[#FFFDF8] border border-[#ddd6ca] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#eee9df] px-5 py-3.5 bg-white">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#1F5D42] bg-[#e7f2eb] px-2.5 py-0.5 rounded-full border border-[#cbe1d5]">
              {product.category_name || (isHi ? "किराना" : "Grocery")}
            </span>
            {product.brand && (
              <span className="text-[10px] font-bold text-[#8a5b1d] bg-[#fff3db] px-2 py-0.5 rounded-full border border-[#f5deb5]">
                {product.brand}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-[#6d756f] hover:text-[#123324] p-1.5 rounded-xl hover:bg-[#eee9df] transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Media Frame */}
        <div className="w-full h-56 bg-gradient-to-br from-[#efe2c7]/40 to-[#d5b275]/20 flex items-center justify-center p-4 border-b border-[#eee9df] relative">
          {imgSource ? (
            <img
              src={imgSource}
              alt={product.name}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <div className="text-center text-[#998b77]">
              <Package size={48} className="mx-auto mb-1 opacity-60" />
              <span className="text-[11px] font-semibold">{isHi ? "कोई तस्वीर उपलब्ध नहीं" : "No image available"}</span>
            </div>
          )}

          {hasDiscount && (
            <div className="absolute top-3 left-3 bg-[#1F5D42] text-white px-2.5 py-1 rounded-xl text-[10px] font-bold shadow-xs flex items-center gap-1">
              <Sparkles size={11} className="text-[#E8A33D]" />
              <span>{discountPct}% {isHi ? "छूट" : "OFF"}</span>
            </div>
          )}
        </div>

        {/* Content Details */}
        <div className="p-6 space-y-4 overflow-y-auto text-xs">
          <div>
            <h2 className="font-display font-bold text-lg text-[#123324] leading-snug">
              {product.name}
            </h2>
            <div className="flex items-center gap-3 mt-2.5">
              <div className="flex items-baseline gap-2">
                <span className="font-display font-bold text-2xl text-[#1F5D42]">
                  ₹{sellingPrice.toFixed(0)}
                </span>
                {mrp && mrp > 0 && (
                  <span className="text-xs text-[#869088] line-through">
                    MRP ₹{mrp.toFixed(0)}
                  </span>
                )}
              </div>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1F5D42] bg-[#e7f2eb] px-2.5 py-0.5 rounded-full border border-[#cbe1d5]">
                <ShieldCheck size={12} className="text-[#1F5D42]" />
                <span>{isHi ? "प्रमाणित गुणवत्ता" : "Verified Quality"}</span>
              </span>
            </div>
          </div>

          {/* Description */}
          {product.description && (
            <div className="rounded-2xl bg-[#faf8f3] border border-[#eee9df] p-4 space-y-1">
              <span className="font-bold text-[11px] text-[#123324] block">
                {isHi ? "विवरण (Description)" : "Product Description"}
              </span>
              <p className="text-[#5e665f] text-xs leading-relaxed">
                {product.description}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[#eee9df] px-6 py-4 bg-white flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-[#1F5D42] text-white text-xs font-bold hover:bg-[#123324] transition shadow-xs cursor-pointer"
          >
            {isHi ? "ठीक है" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
