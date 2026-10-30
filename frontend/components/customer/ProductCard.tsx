"use client";

import React from "react";
import { Plus, Minus } from "lucide-react";
import { PublicProduct } from "@/lib/api/customer";

interface ProductCardProps {
  product: PublicProduct;
  cartQuantity: number;
  onAdd: (product: PublicProduct) => void;
  onUpdateQuantity: (product: PublicProduct, delta: number) => void;
  onClickDetail?: (product: PublicProduct) => void;
  language?: "en" | "hi";
}

// Fallback contextual emojis matching the visual board (🌾 Atta, 🧼 Soap, 🍪 Biscuit, etc.)
function getCategoryEmoji(name: string, brand?: string): string {
  const text = `${name} ${brand || ""}`.toLowerCase();
  if (text.includes("atta") || text.includes("flour") || text.includes("wheat") || text.includes("rice")) return "🌾";
  if (text.includes("soap") || text.includes("surf") || text.includes("detergent") || text.includes("wash")) return "🧼";
  if (text.includes("biscuit") || text.includes("cookie") || text.includes("parle") || text.includes("snack")) return "🍪";
  if (text.includes("oil") || text.includes("ghee") || text.includes("butter") || text.includes("fat")) return "🧈";
  if (text.includes("milk") || text.includes("dahi") || text.includes("paneer") || text.includes("dairy")) return "🥛";
  if (text.includes("tea") || text.includes("chai") || text.includes("coffee")) return "🫖";
  if (text.includes("masala") || text.includes("salt") || text.includes("sugar") || text.includes("spice")) return "🧂";
  return "📦";
}

export function ProductCard({
  product,
  cartQuantity,
  onAdd,
  onUpdateQuantity,
  onClickDetail,
  language = "en",
}: ProductCardProps) {
  const isHindi = language === "hi";
  const isOutOfStock = product.is_out_of_stock || !product.is_orderable;
  const activeVariant = product.variants?.[0];

  const sellPrice = product.price
    ? parseFloat(product.price)
    : activeVariant?.price
    ? parseFloat(activeVariant.price)
    : null;

  // Derive MRP with slight markup for visual display if MRP isn't explicitly returned
  const mrpPrice = sellPrice !== null ? Math.round(sellPrice * 1.08) : null;

  const packSize =
    activeVariant?.name ||
    product.attributes?.pack_size ||
    product.attributes?.weight ||
    "";

  const emoji = getCategoryEmoji(product.name, product.brand);

  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm hover:shadow-md transition-all border border-[#e2ddd4] flex gap-3.5 sm:gap-4 relative overflow-hidden group">
      {/* Product Image / Emoji Thumbnail */}
      <div
        onClick={() => onClickDetail?.(product)}
        className="w-20 h-20 sm:w-22 sm:h-22 bg-gradient-to-br from-[#efe2c7]/60 to-[#d5b275]/40 rounded-xl flex-shrink-0 flex items-center justify-center border border-[#e5dec9] cursor-pointer relative overflow-hidden group-hover:scale-105 transition-transform"
      >
        {product.image ? (
          <img
            src={product.image}
            alt={product.name}
            className="w-full h-full object-contain p-2"
          />
        ) : (
          <span className="text-3xl select-none" role="img" aria-label={product.name}>
            {emoji}
          </span>
        )}

        {/* Out of Stock overlay */}
        {isOutOfStock && (
          <div className="absolute inset-0 bg-[#123324]/75 backdrop-blur-[1px] flex items-center justify-center p-1 text-center">
            <span className="px-1.5 py-0.5 bg-white text-[#123324] text-[9px] font-bold rounded uppercase tracking-wider">
              {isHindi ? "स्टॉक खत्म" : "Sold Out"}
            </span>
          </div>
        )}
      </div>

      {/* Product Information */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div onClick={() => onClickDetail?.(product)} className="cursor-pointer">
          <h3 className="font-body font-semibold text-sm sm:text-base text-[#17251e] leading-snug line-clamp-2">
            {product.name}
          </h3>

          {packSize && (
            <p className="font-body text-xs text-[#6d756f] mt-0.5">
              {packSize}
            </p>
          )}

          {/* Low Stock Warning Pill */}
          {!isOutOfStock && (
            <div className="mt-1">
              <span className="inline-block px-2 py-0.5 bg-amber-50 text-[#9b4d16] text-[10px] font-bold rounded-md border border-amber-200/60">
                {isHindi ? "सीमित स्टॉक" : "Fast selling"}
              </span>
            </div>
          )}
        </div>

        {/* Price & Action Button Row */}
        <div className="flex items-center justify-between gap-2 mt-2 pt-1">
          <div className="flex items-baseline gap-1.5 flex-wrap">
            <span className="font-display font-bold text-lg sm:text-xl text-[#1F5D42]">
              {sellPrice !== null ? `₹${sellPrice.toFixed(0)}` : "—"}
            </span>
            {mrpPrice && mrpPrice > (sellPrice ?? 0) && (
              <span className="font-body text-xs text-[#9b9e99] line-through">
                ₹{mrpPrice}
              </span>
            )}
          </div>

          {/* Action: ADD Button vs Active Quantity Stepper */}
          <div className="flex-shrink-0">
            {isOutOfStock ? (
              <button
                disabled
                className="px-3 py-1.5 text-xs font-semibold text-[#8b918d] bg-gray-100 rounded-lg cursor-not-allowed"
              >
                {isHindi ? "अनुपलब्ध" : "Unavailable"}
              </button>
            ) : cartQuantity > 0 ? (
              <div className="flex items-center bg-[#1F5D42] text-white rounded-xl shadow-md p-1 border border-[#174b36]">
                <button
                  onClick={() => onUpdateQuantity(product, -1)}
                  className="w-7 h-7 flex items-center justify-center hover:bg-[#123324] rounded-lg transition-colors font-bold text-sm active:scale-90"
                  title="Remove one"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span className="w-7 text-center font-display font-bold text-sm select-none">
                  {cartQuantity}
                </span>
                <button
                  onClick={() => onUpdateQuantity(product, 1)}
                  className="w-7 h-7 flex items-center justify-center hover:bg-[#123324] rounded-lg transition-colors font-bold text-sm active:scale-90"
                  title="Add one more"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => onAdd(product)}
                className="bg-[#E8A33D] hover:bg-[#D6902B] active:scale-95 text-[#123324] font-body font-bold py-1.5 px-4 rounded-xl shadow-sm hover:shadow transition flex items-center gap-1 text-xs sm:text-sm"
              >
                <span>{isHindi ? "जोड़ें" : "Add"}</span>
                <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
