"use client";

import React from "react";
import { ShoppingBag, ArrowRight } from "lucide-react";

interface CartBottomBarProps {
  itemCount: number;
  totalAmount: string | number;
  onOpenCart: () => void;
}

export function CartBottomBar({
  itemCount,
  totalAmount,
  onOpenCart,
}: CartBottomBarProps) {
  if (itemCount <= 0) return null;

  const formattedAmount =
    typeof totalAmount === "number"
      ? totalAmount.toFixed(0)
      : parseFloat(totalAmount || "0").toFixed(0);

  return (
    <div className="fixed bottom-4 left-0 right-0 z-40 px-4 max-w-xl mx-auto animate-in slide-in-from-bottom-3 duration-200">
      <div
        onClick={onOpenCart}
        className="bg-[#0F172A] text-white rounded-2xl p-3.5 flex items-center justify-between shadow-2xl border border-slate-800 cursor-pointer hover:bg-slate-900 transition-all active:scale-[0.99]"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#1F5D42] text-white flex items-center justify-center font-bold">
            <ShoppingBag className="w-5 h-5 text-emerald-300" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-300">
              {itemCount} {itemCount === 1 ? "Item" : "Items"} in Bag
            </div>
            <div className="text-sm font-bold text-white tracking-tight">
              ₹{formattedAmount}
            </div>
          </div>
        </div>

        <button className="flex items-center gap-1.5 px-4 py-2 bg-[#1F5D42] text-white text-xs font-bold rounded-xl hover:bg-[#164430] transition-colors shadow-sm">
          <span>View Cart</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
