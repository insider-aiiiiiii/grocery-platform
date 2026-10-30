"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { Search, Sparkles, Tag, AlertCircle, RefreshCw, X } from "lucide-react";
import {
  customerApi,
  PublicShopInfo,
  PublicCategory,
  PublicProduct,
  PublicCampaign,
  PublicCart,
} from "@/lib/api/customer";
import { ShopHeader } from "@/components/customer/ShopHeader";
import { CategoryBar } from "@/components/customer/CategoryBar";
import { ProductCard } from "@/components/customer/ProductCard";
import { CartBottomBar } from "@/components/customer/CartBottomBar";
import { ProductDetailModal } from "@/components/customer/ProductDetailModal";

export default function CustomerShopPage() {
  const params = useParams();
  const router = useRouter();
  const publicSlug = Array.isArray(params?.publicSlug)
    ? params.publicSlug[0]
    : (params?.publicSlug as string);

  const [shop, setShop] = useState<PublicShopInfo | null>(null);
  const [categories, setCategories] = useState<PublicCategory[]>([]);
  const [campaigns, setCampaigns] = useState<PublicCampaign[]>([]);
  const [products, setProducts] = useState<PublicProduct[]>([]);
  const [cart, setCart] = useState<PublicCart | null>(null);

  const [selectedCategory, setSelectedCategory] = useState<number | string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeModalProduct, setActiveModalProduct] = useState<PublicProduct | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Cart ID persistence in localStorage per shop
  const cartStorageKey = `dukaan_cart_${publicSlug}`;

  // Fetch Initial Store Data
  useEffect(() => {
    if (!publicSlug) return;

    async function loadStorefront() {
      setLoading(true);
      setError(null);
      try {
        const [shopData, catData, campData, prodData] = await Promise.all([
          customerApi.getShop(publicSlug),
          customerApi.getCategories(publicSlug),
          customerApi.getCampaigns(publicSlug),
          customerApi.getProducts(publicSlug),
        ]);

        setShop(shopData);
        setCategories(catData);
        setCampaigns(campData);
        setProducts(prodData);

        // Load or create cart
        const savedCartId = localStorage.getItem(cartStorageKey);
        if (savedCartId) {
          try {
            const existingCart = await customerApi.getCart(publicSlug, parseInt(savedCartId, 10));
            setCart(existingCart);
          } catch {
            const newCart = await customerApi.createCart(publicSlug);
            localStorage.setItem(cartStorageKey, newCart.id.toString());
            setCart(newCart);
          }
        } else {
          const newCart = await customerApi.createCart(publicSlug);
          localStorage.setItem(cartStorageKey, newCart.id.toString());
          setCart(newCart);
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || "Could not load the storefront. Please check the link.");
      } finally {
        setLoading(false);
      }
    }

    loadStorefront();
  }, [publicSlug]);

  // Cart item quantity lookup helper
  const cartQuantityMap = useMemo(() => {
    const map: Record<number, number> = {};
    if (!cart?.items) return map;
    for (const item of cart.items) {
      map[item.product.id] = (map[item.product.id] || 0) + item.quantity;
    }
    return map;
  }, [cart]);

  // Filter products by category and search
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      // Category filter
      if (selectedCategory !== "all") {
        const inCategory = p.categories?.some((c) => c.id === selectedCategory);
        if (!inCategory) return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = p.name.toLowerCase().includes(q);
        const matchesBrand = p.brand?.toLowerCase().includes(q);
        const matchesDesc = p.description?.toLowerCase().includes(q);
        if (!matchesName && !matchesBrand && !matchesDesc) return false;
      }
      return true;
    });
  }, [products, selectedCategory, searchQuery]);

  // Cart Actions
  const handleAddToCart = async (product: PublicProduct, variant?: any) => {
    if (!cart) return;
    try {
      const updatedCart = await customerApi.addItemToCart(publicSlug, cart.id, {
        product_id: product.id,
        variant_id: variant?.id,
        quantity: 1,
      });
      setCart(updatedCart);
    } catch (err: any) {
      console.error("Failed to add to cart", err);
    }
  };

  const handleUpdateQuantity = async (product: PublicProduct, delta: number) => {
    if (!cart) return;
    const cartItem = cart.items.find((i) => i.product.id === product.id);
    if (!cartItem) {
      if (delta > 0) handleAddToCart(product);
      return;
    }

    const nextQty = cartItem.quantity + delta;
    try {
      if (nextQty <= 0) {
        const updatedCart = await customerApi.removeCartItem(publicSlug, cart.id, cartItem.id);
        setCart(updatedCart);
      } else {
        const updatedCart = await customerApi.updateCartItem(publicSlug, cart.id, cartItem.id, nextQty);
        setCart(updatedCart);
      }
    } catch (err: any) {
      console.error("Failed to update cart quantity", err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center p-4">
        <RefreshCw className="w-8 h-8 text-[#1F5D42] animate-spin mb-3" />
        <p className="text-xs font-semibold text-slate-600">Loading store shelves…</p>
      </div>
    );
  }

  if (error || !shop) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mb-3">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-slate-900 mb-1">Store Unavailable</h2>
        <p className="text-xs text-slate-600 max-w-sm mb-4">
          {error || "This store link does not exist or has been paused."}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-[#1F5D42] text-white text-xs font-semibold rounded-xl"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans pb-28">
      {/* 1. Header with Store Identity & Timing */}
      <ShopHeader shop={shop} />

      {/* Main Container */}
      <div className="max-w-xl mx-auto space-y-3">
        {/* 2. Search Input */}
        <div className="px-4 pt-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search dairy, atta, oil, biscuits…"
              className="w-full pl-10 pr-9 py-2.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-[#1F5D42] focus:ring-2 focus:ring-[#1F5D42]/10 transition-all placeholder:text-slate-400 shadow-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* 3. Promotional Campaign Banner (If active) */}
        {campaigns.length > 0 && (
          <div className="px-4">
            <div className="bg-gradient-to-r from-[#E8A33D]/15 via-emerald-50 to-[#1F5D42]/10 border border-[#E8A33D]/30 rounded-2xl p-3 flex items-start gap-2.5 shadow-sm">
              <div className="p-1.5 rounded-lg bg-[#E8A33D] text-slate-900 shrink-0">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#E8A33D] block">
                  Dukaan Special Offer
                </span>
                <h4 className="text-xs font-bold text-slate-900 leading-tight">
                  {campaigns[0].title}
                </h4>
                {campaigns[0].content && (
                  <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-1">
                    {campaigns[0].content}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 4. Horizontal Category Filter Pills */}
        <CategoryBar
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        {/* 5. 2-Column Product Grid */}
        <main className="px-4 pt-1">
          <div className="flex items-center justify-between mb-2.5">
            <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              {selectedCategory === "all"
                ? "All Store Items"
                : categories.find((c) => c.id === selectedCategory)?.name || "Items"}
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">
              {filteredProducts.length} {filteredProducts.length === 1 ? "Product" : "Products"}
            </span>
          </div>

          {filteredProducts.length === 0 ? (
            <div className="py-12 bg-white rounded-2xl border border-slate-200 text-center p-6 space-y-2">
              <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
                <Tag className="w-5 h-5" />
              </div>
              <h3 className="text-xs font-bold text-slate-700">No products found</h3>
              <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                Try searching for something else or pick a different category.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {filteredProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  cartQuantity={cartQuantityMap[product.id] || 0}
                  onAdd={handleAddToCart}
                  onUpdateQuantity={handleUpdateQuantity}
                  onClickDetail={setActiveModalProduct}
                />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* 6. Product Detail Modal */}
      <ProductDetailModal
        product={activeModalProduct}
        cartQuantity={activeModalProduct ? cartQuantityMap[activeModalProduct.id] || 0 : 0}
        onClose={() => setActiveModalProduct(null)}
        onAdd={handleAddToCart}
        onUpdateQuantity={handleUpdateQuantity}
      />

      {/* 7. Persistent Floating Cart Bar */}
      <CartBottomBar
        itemCount={cart?.items_count || 0}
        totalAmount={cart?.total_amount || "0"}
        onOpenCart={() => router.push(`/shop/${publicSlug}/cart`)}
      />
    </div>
  );
}
