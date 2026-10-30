"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { Sparkles, Tag, AlertCircle, RefreshCw } from "lucide-react";
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

  const [language, setLanguage] = useState<"en" | "hi">("en");
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

  const isHindi = language === "hi";

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7f4ee] flex flex-col items-center justify-center p-4">
        <RefreshCw className="w-8 h-8 text-[#1F5D42] animate-spin mb-3" />
        <p className="text-xs font-semibold text-[#5e665f]">
          {isHindi ? "दुकान खुल रही है…" : "Opening store shelves…"}
        </p>
      </div>
    );
  }

  if (error || !shop) {
    return (
      <div className="min-h-screen bg-[#f7f4ee] flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-red-100 text-red-700 flex items-center justify-center mb-3">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-display font-bold text-lg text-[#17251e] mb-1">
          {isHindi ? "दुकान उपलब्ध नहीं है" : "Store Unavailable"}
        </h2>
        <p className="text-xs text-[#6d756f] max-w-sm mb-4">
          {error || (isHindi ? "यह दुकान लिंक अमान्य है या अस्थायी रूप से बंद है।" : "This store link does not exist or has been paused.")}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-5 py-2.5 bg-[#1F5D42] text-white text-xs font-bold rounded-xl shadow-md hover:bg-[#123324] transition"
        >
          {isHindi ? "पुनः प्रयास करें" : "Try Again"}
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f4ee] text-[#17251e] font-body pb-32">
      {/* 1. Header with Store Identity, Timing, Language Switcher and Search */}
      <ShopHeader
        shop={shop}
        language={language}
        onToggleLanguage={() => setLanguage((prev) => (prev === "en" ? "hi" : "en"))}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Main Container */}
      <div className="max-w-xl mx-auto space-y-3">
        {/* 2. Promotional Campaign Banner (If active) */}
        {campaigns.length > 0 && (
          <div className="px-4 pt-3">
            <div className="bg-gradient-to-r from-[#E8A33D]/20 via-[#FFFDF8] to-[#1F5D42]/10 border border-[#E8A33D]/40 rounded-2xl p-3.5 flex items-start gap-3 shadow-sm">
              <div className="p-2 rounded-xl bg-[#E8A33D] text-[#123324] shrink-0 shadow-sm">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#9b4d16] block">
                  {isHindi ? "दुकान स्पेशल ऑफर" : "Dukaan Special Offer"}
                </span>
                <h4 className="font-display font-bold text-sm text-[#17251e] leading-tight mt-0.5">
                  {campaigns[0].title}
                </h4>
                {campaigns[0].content && (
                  <p className="text-xs text-[#6d756f] mt-0.5 line-clamp-1">
                    {campaigns[0].content}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 3. Horizontal Category Filter Pills */}
        <CategoryBar
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          language={language}
        />

        {/* 4. Product List (Matching Visual Board layout) */}
        <main className="px-4 pt-1 space-y-2.5">
          <div className="flex items-center justify-between px-1">
            <h2 className="font-display font-bold text-base text-[#17251e]">
              {selectedCategory === "all"
                ? isHindi
                  ? "सभी उपलब्ध सामान"
                  : "All Store Items"
                : categories.find((c) => c.id === selectedCategory)?.name || (isHindi ? "सामान" : "Items")}
            </h2>
            <span className="text-xs text-[#6d756f] font-medium">
              {filteredProducts.length} {isHindi ? "सामान" : filteredProducts.length === 1 ? "Product" : "Products"}
            </span>
          </div>

          {filteredProducts.length === 0 ? (
            <div className="py-14 bg-white rounded-2xl border border-[#e2ddd4] text-center p-6 space-y-2.5 shadow-sm">
              <div className="w-12 h-12 rounded-full bg-[#f6f0e6] text-[#7a531d] mx-auto flex items-center justify-center">
                <Tag className="w-6 h-6" />
              </div>
              <h3 className="font-display font-bold text-base text-[#17251e]">
                {isHindi ? "कोई सामान नहीं मिला" : "No products found"}
              </h3>
              <p className="text-xs text-[#6d756f] max-w-xs mx-auto">
                {isHindi
                  ? "कृपया कुछ और खोजें या कोई अन्य श्रेणी चुनें।"
                  : "Try searching for something else or pick a different category."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {filteredProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  cartQuantity={cartQuantityMap[product.id] || 0}
                  onAdd={handleAddToCart}
                  onUpdateQuantity={handleUpdateQuantity}
                  onClickDetail={setActiveModalProduct}
                  language={language}
                />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* 5. Product Detail Modal */}
      <ProductDetailModal
        product={activeModalProduct}
        cartQuantity={activeModalProduct ? cartQuantityMap[activeModalProduct.id] || 0 : 0}
        onClose={() => setActiveModalProduct(null)}
        onAdd={handleAddToCart}
        onUpdateQuantity={handleUpdateQuantity}
      />

      {/* 6. Persistent Floating Bottom Cart Bar */}
      <CartBottomBar
        itemCount={cart?.items_count || 0}
        totalAmount={cart?.total_amount || "0"}
        onOpenCart={() => router.push(`/shop/${publicSlug}/cart`)}
        language={language}
      />
    </div>
  );
}
