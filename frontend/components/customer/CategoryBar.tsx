"use client";

import React from "react";
import { PublicCategory } from "@/lib/api/customer";

interface CategoryBarProps {
  categories: PublicCategory[];
  selectedCategory: number | string;
  onSelectCategory: (categoryId: number | string) => void;
}

export function CategoryBar({
  categories,
  selectedCategory,
  onSelectCategory,
}: CategoryBarProps) {
  return (
    <div className="bg-white border-b border-slate-200 sticky top-0 z-20">
      <div className="max-w-xl mx-auto px-4 py-2.5 overflow-x-auto no-scrollbar flex items-center gap-2">
        <button
          onClick={() => onSelectCategory("all")}
          className={`px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            selectedCategory === "all"
              ? "bg-[#1F5D42] text-white shadow-sm"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          All Items
        </button>

        {categories.map((cat) => {
          const isSelected = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => onSelectCategory(cat.id)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                isSelected
                  ? "bg-[#1F5D42] text-white shadow-sm"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {cat.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
