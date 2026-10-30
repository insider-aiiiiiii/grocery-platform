"use client";

import React from "react";
import { ArrowRight, ShoppingBag } from "lucide-react";

interface CartBottomBarProps {
  itemCount: number;
  totalAmount: string | number;
  onOpenCart: () => void;
  language?: "en" | "hi";
}

export function CartBottomBar({
  itemCount,
  totalAmount,
  onOpenCart,
  language = "en",
}: CartBottomBarProps) {
  if (itemCount <= 0) return null;

  const isHindi = language === "hi";
  const formattedAmount =
    typeof totalAmount === "number"
      ? totalAmount.toFixed(0)
      : parseFloat(totalAmount || "0").toFixed(0);

  return (
    <div className="fixed bottom-4 left-0 right-0 z-40 px-4 max-w-xl mx-auto animate-in slide-in-from-bottom-4 duration-200">
      <div
        onClick={onOpenCart}
        className="bg-gradient-to-r from-[#123324] via-[#1a4a35] to-[#1F5D42] text-white rounded-2xl p-3.5 sm:p-4 flex items-center justify-between shadow-[0_12px_28px_rgba(18,51,36,0.35)] border border-emerald-500/20 cursor-pointer hover:brightness-105 transition-all active:scale-[0.99]"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#E8A33D] text-[#123324] flex items-center justify-center font-bold shadow-sm shrink-0">
            <ShoppingBag className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-medium text-white/80">
              {itemCount} {isHindi ? "सामान" : itemCount === 1 ? "Item" : "Items"}
            </p>
            <p className="font-display font-bold text-lg sm:text-xl text-white leading-none mt-0.5">
              ₹{formattedAmount}
            </p>
          </div>
        </div>

        <button className="flex items-center gap-2 px-4 py-2.5 bg-[#E8A33D] hover:bg-[#D6902B] text-[#123324] text-xs sm:text-sm font-bold font-body rounded-xl transition-all shadow-md active:scale-95">
          <span>{isHindi ? "ऑर्डर और चेकआउट" : "View Cart & Checkout"}</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>
    </div>
  );
}
