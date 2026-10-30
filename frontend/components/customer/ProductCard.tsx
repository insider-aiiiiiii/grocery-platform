"use client";

import React from "react";
import { Plus, Minus, Package, Sparkles } from "lucide-react";
import { PublicProduct } from "@/lib/api/customer";

interface ProductCardProps {
  product: PublicProduct;
  cartQuantity: number;
  onAdd: (product: PublicProduct) => void;
  onUpdateQuantity: (product: PublicProduct, delta: number) => void;
  onClickDetail?: (product: PublicProduct) => void;
}

export function ProductCard({
  product,
  cartQuantity,
  onAdd,
  onUpdateQuantity,
  onClickDetail,
}: ProductCardProps) {
  const isOutOfStock = product.is_out_of_stock || !product.is_orderable;
  const activeVariant = product.variants?.[0];
  const displayPrice = product.price
    ? parseFloat(product.price)
    : activeVariant?.price
    ? parseFloat(activeVariant.price)
    : null;

  const packSize = activeVariant?.name || product.attributes?.pack_size || product.attributes?.weight || "";

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-3 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow relative">
      {/* Product Image & Badges */}
      <div
        onClick={() => onClickDetail?.(product)}
        className="cursor-pointer"
      >
        <div className="w-full aspect-square bg-slate-50 rounded-xl relative overflow-hidden flex items-center justify-center border border-slate-100">
          {product.image ? (
            <img
              src={product.image}
              alt={product.name}
              className="w-full h-full object-contain p-2"
            />
          ) : (
            <Package className="w-10 h-10 text-slate-300" />
          )}

          {/* Out of Stock Ribbon */}
          {isOutOfStock && (
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-[1px] flex items-center justify-center">
              <span className="px-2 py-1 bg-white text-slate-900 text-[10px] font-bold rounded uppercase tracking-wider">
                Out of Stock
              </span>
            </div>
          )}

          {/* Pack size pill */}
          {packSize && (
            <span className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-white/95 text-slate-700 shadow-sm border border-slate-200">
              {packSize}
            </span>
          )}
        </div>

        {/* Content */}
        <div className="mt-2.5 space-y-0.5">
          {product.brand && (
            <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
              {product.brand}
            </p>
          )}
          <h3 className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug">
            {product.name}
          </h3>
        </div>
      </div>

      {/* Pricing and Add to Bag Button */}
      <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between gap-1">
        <div>
          <span className="text-sm font-bold text-slate-900">
            {displayPrice !== null ? `₹${displayPrice.toFixed(0)}` : "—"}
          </span>
        </div>

        {/* Action Button: + ADD vs Stepper */}
        {isOutOfStock ? (
          <button
            disabled
            className="px-2.5 py-1 text-[11px] font-semibold text-slate-400 bg-slate-100 rounded-lg cursor-not-allowed"
          >
            Unavailable
          </button>
        ) : cartQuantity > 0 ? (
          <div className="flex items-center bg-[#1F5D42] text-white rounded-lg px-1 py-0.5 shadow-sm">
            <button
              onClick={() => onUpdateQuantity(product, -1)}
              className="p-1 hover:bg-[#164430] rounded transition-colors"
              title="Remove one"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <span className="w-6 text-center text-xs font-bold font-mono">
              {cartQuantity}
            </span>
            <button
              onClick={() => onUpdateQuantity(product, 1)}
              className="p-1 hover:bg-[#164430] rounded transition-colors"
              title="Add one more"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => onAdd(product)}
            className="px-3 py-1 border-1.5 border-[#1F5D42] text-[#1F5D42] bg-emerald-50/50 hover:bg-[#1F5D42] hover:text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center gap-1 active:scale-95"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>ADD</span>
          </button>
        )}
      </div>
    </div>
  );
}
