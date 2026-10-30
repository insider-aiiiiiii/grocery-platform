"use client";

import React, { useState } from "react";
import { X, Plus, Minus, Package, ShieldCheck } from "lucide-react";
import { PublicProduct, PublicProductVariant } from "@/lib/api/customer";

interface ProductDetailModalProps {
  product: PublicProduct | null;
  cartQuantity: number;
  onClose: () => void;
  onAdd: (product: PublicProduct, variant?: PublicProductVariant) => void;
  onUpdateQuantity: (product: PublicProduct, delta: number) => void;
}

export function ProductDetailModal({
  product,
  cartQuantity,
  onClose,
  onAdd,
  onUpdateQuantity,
}: ProductDetailModalProps) {
  if (!product) return null;

  const [selectedVariant, setSelectedVariant] = useState<PublicProductVariant | undefined>(
    product.variants?.[0]
  );

  const price = selectedVariant?.price
    ? parseFloat(selectedVariant.price)
    : product.price
    ? parseFloat(product.price)
    : 0;

  const isOutOfStock = product.is_out_of_stock || !product.is_orderable;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-lg rounded-t-3xl sm:rounded-2xl max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200">
        {/* Header with Close */}
        <div className="sticky top-0 bg-white/95 backdrop-blur-sm px-5 py-3.5 border-b border-slate-100 flex items-center justify-between z-10">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            {product.brand || "Product Details"}
          </span>
          <button
            onClick={onClose}
            className="p-1 rounded-full text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Media */}
        <div className="w-full aspect-[4/3] bg-slate-50 flex items-center justify-center border-b border-slate-100 p-6 relative">
          {product.image ? (
            <img
              src={product.image}
              alt={product.name}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <Package className="w-16 h-16 text-slate-300" />
          )}

          {isOutOfStock && (
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-[1px] flex items-center justify-center">
              <span className="px-3 py-1.5 bg-white text-slate-900 text-xs font-bold rounded-lg uppercase tracking-wider">
                Currently Out of Stock
              </span>
            </div>
          )}
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              {product.name}
            </h2>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xl font-bold text-slate-900">₹{price.toFixed(0)}</span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                <ShieldCheck className="w-3 h-3 text-emerald-600" />
                Verified Quality
              </span>
            </div>
          </div>

          {/* Variants selector if multiple variants exist */}
          {product.variants && product.variants.length > 1 && (
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-2">
                Select Pack / Variant
              </label>
              <div className="flex flex-wrap gap-2">
                {product.variants.map((v) => {
                  const isSelected = selectedVariant?.id === v.id;
                  return (
                    <button
                      key={v.id}
                      onClick={() => setSelectedVariant(v)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                        isSelected
                          ? "border-[#1F5D42] bg-emerald-50 text-[#1F5D42] ring-1 ring-[#1F5D42]"
                          : "border-slate-200 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      {v.name} • ₹{parseFloat(v.price || "0").toFixed(0)}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Description */}
          {product.description && (
            <div className="pt-2 border-t border-slate-100">
              <h4 className="text-xs font-bold text-slate-700 mb-1">Description</h4>
              <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line">
                {product.description}
              </p>
            </div>
          )}

          {/* Action Footer */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
            <div>
              <span className="text-[11px] text-slate-500 block">Total Price</span>
              <span className="text-lg font-bold text-slate-900">
                ₹{(price * Math.max(1, cartQuantity)).toFixed(0)}
              </span>
            </div>

            {isOutOfStock ? (
              <button
                disabled
                className="px-5 py-2.5 bg-slate-100 text-slate-400 font-bold text-xs rounded-xl cursor-not-allowed"
              >
                Out of Stock
              </button>
            ) : cartQuantity > 0 ? (
              <div className="flex items-center bg-[#1F5D42] text-white rounded-xl px-2 py-1 shadow-sm">
                <button
                  onClick={() => onUpdateQuantity(product, -1)}
                  className="p-1.5 hover:bg-[#164430] rounded-lg transition-colors"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <span className="w-8 text-center text-sm font-bold font-mono">
                  {cartQuantity}
                </span>
                <button
                  onClick={() => onUpdateQuantity(product, 1)}
                  className="p-1.5 hover:bg-[#164430] rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  onAdd(product, selectedVariant);
                }}
                className="px-6 py-2.5 bg-[#1F5D42] hover:bg-[#164430] text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center gap-1.5 active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>Add to Basket</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
