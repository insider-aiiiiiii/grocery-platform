"use client";

import React from "react";
import { PublicCategory } from "@/lib/api/customer";

interface CategoryBarProps {
  categories: PublicCategory[];
  selectedCategory: number | string;
  onSelectCategory: (categoryId: number | string) => void;
  language?: "en" | "hi";
}

export function CategoryBar({
  categories,
  selectedCategory,
  onSelectCategory,
  language = "en",
}: CategoryBarProps) {
  const isHindi = language === "hi";

  return (
    <nav className="sticky top-0 z-10 bg-[#f7f4ee]/95 backdrop-blur-md py-3 border-b border-[#e5dec9]">
      <div className="max-w-xl mx-auto px-4 overflow-x-auto no-scrollbar flex items-center gap-2">
        <button
          onClick={() => onSelectCategory("all")}
          className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all shadow-sm ${
            selectedCategory === "all"
              ? "bg-[#E8A33D] text-[#123324] font-bold shadow-md scale-105"
              : "bg-white border border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
          }`}
        >
          {isHindi ? "सभी सामान" : "All Items"}
        </button>

        {categories.map((cat) => {
          const isSelected = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => onSelectCategory(cat.id)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all shadow-sm ${
                isSelected
                  ? "bg-[#E8A33D] text-[#123324] font-bold shadow-md scale-105"
                  : "bg-white border border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
              }`}
            >
              {cat.name}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
