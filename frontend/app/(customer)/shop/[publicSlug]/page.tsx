"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Sparkles,
  Tag,
  AlertCircle,
  RefreshCw,
  Layers,
  ChevronRight,
  Package,
  Store,
  CheckCircle2,
} from "lucide-react";
import {
  customerApi,
  PublicShopInfo,
  PublicCategory,
  PublicProduct,
  PublicCampaign,
  PublicCart,
} from "@/lib/api/customer";
import { ShopHeader } from "@/components/customer/ShopHeader";
import { ProductCard } from "@/components/customer/ProductCard";
import { CartBottomBar } from "@/components/customer/CartBottomBar";
import { ProductDetailModal } from "@/components/customer/ProductDetailModal";

// Helper for category contextual icons matching Blinkit style
function getCategoryIcon(name: string): string {
  const t = name.toLowerCase();
  if (t.includes("dairy") || t.includes("milk") || t.includes("cheese") || t.includes("butter")) return "🥛";
  if (t.includes("atta") || t.includes("flour") || t.includes("rice") || t.includes("dal") || t.includes("grain") || t.includes("staple")) return "🌾";
  if (t.includes("snack") || t.includes("biscuit") || t.includes("munch") || t.includes("chips") || t.includes("cookie")) return "🍪";
  if (t.includes("beverage") || t.includes("tea") || t.includes("coffee") || t.includes("juice") || t.includes("drink")) return "🧃";
  if (t.includes("masala") || t.includes("spice") || t.includes("oil") || t.includes("ghee")) return "🧂";
  if (t.includes("clean") || t.includes("wash") || t.includes("soap") || t.includes("detergent")) return "🧼";
  if (t.includes("personal") || t.includes("beauty") || t.includes("hair") || t.includes("skin")) return "🧴";
  if (t.includes("fruit") || t.includes("vegetable") || t.includes("fresh")) return "🍎";
  if (t.includes("bread") || t.includes("bakery") || t.includes("egg")) return "🍞";
  return "📦";
}

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

  // Blinkit Category & Subcategory Navigation State
  const [selectedRootCategory, setSelectedRootCategory] = useState<number | "all">("all");
  const [selectedSubcategory, setSelectedSubcategory] = useState<number | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeModalProduct, setActiveModalProduct] = useState<PublicProduct | null>(null);

  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cartError, setCartError] = useState<string | null>(null);

  const showCartError = (msg: string) => {
    setCartError(msg);
    setTimeout(() => setCartError(null), 3500);
  };

  const cartStorageKey = `dukaan_cart_${publicSlug}`;

  // Silent or manual storefront refresh
  const syncStorefront = useCallback(
    async (silent = false) => {
      if (!publicSlug) return;
      if (!silent) setIsSyncing(true);
      try {
        const [catData, campData, prodData] = await Promise.all([
          customerApi.getCategories(publicSlug),
          customerApi.getCampaigns(publicSlug),
          customerApi.getProducts(publicSlug),
        ]);
        setCategories(catData);
        setCampaigns(campData);
        setProducts(prodData);
      } catch (err: any) {
        if (!silent) {
          showCartError("Could not sync live catalog. Retrying shortly.");
        }
      } finally {
        if (!silent) setIsSyncing(false);
      }
    },
    [publicSlug]
  );

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
        setError(
          err.response?.data?.detail || "Could not load the storefront. Please check the link."
        );
      } finally {
        setLoading(false);
      }
    }

    loadStorefront();
  }, [publicSlug]);

  // Real-time Background Polling every 12 seconds for live sync
  useEffect(() => {
    if (!publicSlug) return;
    const interval = setInterval(() => {
      syncStorefront(true);
    }, 12000);
    return () => clearInterval(interval);
  }, [publicSlug, syncStorefront]);

  // Tab focus / visibility revalidation
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        syncStorefront(true);
      }
    };
    window.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("focus", onVisibilityChange);
    return () => {
      window.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("focus", onVisibilityChange);
    };
  }, [syncStorefront]);

  // Blinkit Hierarchy: Root categories (no parent or is_subcategory == false)
  const rootCategories = useMemo(() => {
    const roots = categories.filter((c) => !c.parent || c.is_subcategory === false);
    return roots.length > 0 ? roots : categories;
  }, [categories]);

  // Subcategories for the currently active Root Category
  const currentSubcategories = useMemo(() => {
    if (selectedRootCategory === "all") return [];
    return categories.filter((c) => c.parent === selectedRootCategory);
  }, [categories, selectedRootCategory]);

  // When switching root category, reset subcategory to "all"
  const handleSelectRootCategory = (catId: number | "all") => {
    setSelectedRootCategory(catId);
    setSelectedSubcategory("all");
  };

  // Cart item quantity lookup helper
  const cartQuantityMap = useMemo(() => {
    const map: Record<number, number> = {};
    if (!cart?.items) return map;
    for (const item of cart.items) {
      map[item.product.id] = (map[item.product.id] || 0) + item.quantity;
    }
    return map;
  }, [cart]);

  // Filter products by selected root category, subcategory, and search
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      // 1. Search Query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = p.name.toLowerCase().includes(q);
        const matchesBrand = p.brand?.toLowerCase().includes(q);
        const matchesDesc = p.description?.toLowerCase().includes(q);
        if (!matchesName && !matchesBrand && !matchesDesc) return false;
      }

      // 2. Subcategory filter takes highest precedence if selected
      if (selectedSubcategory !== "all") {
        const inSub = p.categories?.some((c) => c.id === selectedSubcategory);
        if (!inSub) return false;
        return true;
      }

      // 3. Root Category filter
      if (selectedRootCategory !== "all") {
        const validCategoryIds = new Set<number>([
          selectedRootCategory,
          ...currentSubcategories.map((sc) => sc.id),
        ]);
        const inRootOrChild = p.categories?.some(
          (c) => validCategoryIds.has(c.id) || c.parent === selectedRootCategory
        );
        if (!inRootOrChild) return false;
      }

      return true;
    });
  }, [products, selectedRootCategory, selectedSubcategory, currentSubcategories, searchQuery]);

  // Group products by subcategory when in a root category with subcategories
  const groupedProducts = useMemo(() => {
    if (selectedRootCategory === "all" || currentSubcategories.length === 0 || selectedSubcategory !== "all") {
      return null;
    }

    const groups: Array<{ subcategory: PublicCategory; products: PublicProduct[] }> = [];
    const assignedIds = new Set<number>();

    for (const sub of currentSubcategories) {
      const prods = filteredProducts.filter((p) => p.categories?.some((c) => c.id === sub.id));
      if (prods.length > 0) {
        groups.push({ subcategory: sub, products: prods });
        prods.forEach((p) => assignedIds.add(p.id));
      }
    }

    // Unassigned products under root category
    const remaining = filteredProducts.filter((p) => !assignedIds.has(p.id));
    if (remaining.length > 0) {
      groups.push({
        subcategory: {
          id: -1,
          name: "Other Items",
          slug: "other",
        },
        products: remaining,
      });
    }

    return groups;
  }, [filteredProducts, selectedRootCategory, currentSubcategories, selectedSubcategory]);

  // Cart Actions with Instant Optimistic UI Synchronization
  const handleAddToCart = async (product: PublicProduct, variant?: any) => {
    if (!cart) return;
    const previousCart = cart;
    const targetVariant = variant || product.variants?.[0];
    const unitPriceNum = targetVariant?.price
      ? parseFloat(targetVariant.price)
      : product.price
      ? parseFloat(product.price)
      : 0;

    const existingIndex = cart.items.findIndex(
      (i) => i.product.id === product.id && (targetVariant ? i.variant?.id === targetVariant.id : true)
    );

    const nextItems = [...cart.items];
    if (existingIndex >= 0) {
      const current = nextItems[existingIndex];
      const currentQty = Math.round(Number(current.quantity) || 1);
      const updatedQty = currentQty + 1;
      nextItems[existingIndex] = {
        ...current,
        quantity: updatedQty,
        total_price: (parseFloat(current.unit_price) * updatedQty).toFixed(2),
      };
    } else {
      nextItems.push({
        id: -Date.now(),
        product: {
          id: product.id,
          name: product.name,
          brand: product.brand,
          image: product.image,
        },
        variant: targetVariant
          ? {
              id: targetVariant.id,
              name: targetVariant.name,
              image: targetVariant.image,
            }
          : null,
        quantity: 1,
        unit_price: unitPriceNum.toFixed(2),
        total_price: unitPriceNum.toFixed(2),
      });
    }

    const optimisticItemsCount = nextItems.reduce((acc, i) => acc + i.quantity, 0);
    const optimisticTotalAmount = nextItems
      .reduce((acc, i) => acc + parseFloat(i.total_price || "0"), 0)
      .toFixed(2);

    setCart({
      ...cart,
      items_count: optimisticItemsCount,
      total_amount: optimisticTotalAmount,
      items: nextItems,
    });

    try {
      const updatedCart = await customerApi.addItemToCart(publicSlug, cart.id, {
        product_id: product.id,
        variant_id: targetVariant?.id,
        quantity: 1,
      });
      setCart(updatedCart);
    } catch (err: any) {
      setCart(previousCart);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.quantity?.[0] ||
        "Could not add item. Stock may be limited.";
      showCartError(String(msg));
    }
  };

  const handleUpdateQuantity = async (product: PublicProduct, delta: number) => {
    if (!cart) return;
    const cartItem = cart.items.find((i) => i.product.id === product.id);
    if (!cartItem) {
      if (delta > 0) handleAddToCart(product);
      return;
    }

    const previousCart = cart;
    const currentQty = Math.round(Number(cartItem.quantity) || 1);
    const nextQty = Math.max(0, currentQty + delta);

    let nextItems: typeof cart.items = [];
    if (nextQty <= 0) {
      nextItems = cart.items.filter((i) => i.id !== cartItem.id);
    } else {
      nextItems = cart.items.map((i) =>
        i.id === cartItem.id
          ? {
              ...i,
              quantity: nextQty,
              total_price: (parseFloat(i.unit_price) * nextQty).toFixed(2),
            }
          : i
      );
    }

    const optimisticItemsCount = nextItems.reduce((acc, i) => acc + i.quantity, 0);
    const optimisticTotalAmount = nextItems
      .reduce((acc, i) => acc + parseFloat(i.total_price || "0"), 0)
      .toFixed(2);

    setCart({
      ...cart,
      items_count: optimisticItemsCount,
      total_amount: optimisticTotalAmount,
      items: nextItems,
    });

    try {
      if (nextQty <= 0) {
        const updatedCart = await customerApi.removeCartItem(publicSlug, cart.id, cartItem.id);
        setCart(updatedCart);
      } else {
        const updatedCart = await customerApi.updateCartItem(publicSlug, cart.id, cartItem.id, nextQty);
        setCart(updatedCart);
      }
    } catch (err: any) {
      setCart(previousCart);
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.quantity?.[0] ||
        "Could not update item. Stock may be limited.";
      showCartError(String(msg));
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
          {error ||
            (isHindi
              ? "यह दुकान लिंक अमान्य है या अस्थायी रूप से बंद है।"
              : "This store link does not exist or has been paused.")}
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

      {/* Floating Cart Sync Error Toast */}
      {cartError && (
        <div className="fixed top-4 left-4 right-4 z-50 max-w-md mx-auto bg-rose-900/95 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg backdrop-blur flex items-center justify-between animate-in fade-in slide-in-from-top-2 border border-rose-700">
          <span>{cartError}</span>
          <button
            onClick={() => setCartError(null)}
            className="ml-2 text-white/80 hover:text-white font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Container */}
      <div className="max-w-4xl mx-auto space-y-3 px-3 sm:px-4">
        {/* 2. Promotional Campaign Banner (If active) */}
        {campaigns.length > 0 && (() => {
          const camp = campaigns[0];
          let bannerImg: string | null = null;
          let bannerText = camp.content || "";
          try {
            if (bannerText.startsWith("{")) {
              const parsed = JSON.parse(bannerText);
              bannerImg = parsed.image || null;
              bannerText = parsed.text || "";
            } else if (bannerText.startsWith("data:image/") || bannerText.startsWith("http")) {
              bannerImg = bannerText;
              bannerText = "";
            }
          } catch {
            // raw string
          }

          return (
            <div className="pt-2">
              {bannerImg ? (
                <div className="relative w-full max-h-48 sm:max-h-56 rounded-2xl overflow-hidden shadow-xs border border-[#ddd6ca] bg-slate-100">
                  <img
                    src={bannerImg}
                    alt={camp.title}
                    className="w-full h-full max-h-48 sm:max-h-56 object-cover"
                  />
                  {(camp.title || bannerText) && (
                    <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 text-white">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[#E8A33D] block">
                        {isHindi ? "दुकान स्पेशल ऑफर" : "Store Announcement"}
                      </span>
                      <h4 className="font-display font-bold text-xs sm:text-sm leading-tight mt-0.5 truncate">
                        {camp.title}
                      </h4>
                      {bannerText && (
                        <p className="text-[11px] text-white/90 line-clamp-1 mt-0.5">
                          {bannerText}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-gradient-to-r from-[#E8A33D]/20 via-[#FFFDF8] to-[#1F5D42]/10 border border-[#E8A33D]/40 rounded-2xl p-3 flex items-start gap-3 shadow-2xs">
                  <div className="p-2 rounded-xl bg-[#E8A33D] text-[#123324] shrink-0 shadow-2xs">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#9b4d16] block">
                      {isHindi ? "दुकान स्पेशल ऑफर" : "Store Announcement"}
                    </span>
                    <h4 className="font-display font-bold text-xs sm:text-sm text-[#17251e] leading-tight mt-0.5 truncate">
                      {camp.title}
                    </h4>
                    {bannerText && (
                      <p className="text-[11px] text-[#6d756f] mt-0.5 line-clamp-1">
                        {bannerText}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* 3. Live Sync Status & Active Selection Bar */}
        <div className="flex items-center justify-between pt-1 pb-1 px-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[#17251e]">
              {selectedRootCategory === "all"
                ? isHindi
                  ? "सभी श्रेणियां"
                  : "All Categories"
                : rootCategories.find((c) => c.id === selectedRootCategory)?.name || "Category"}
            </span>
            <span className="text-[11px] text-[#6d756f] font-mono">
              ({filteredProducts.length} {isHindi ? "सामान" : "items"})
            </span>
          </div>

          {/* Real-time Live Sync Action */}
          <button
            onClick={() => syncStorefront(false)}
            disabled={isSyncing}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-white border border-[#ddd6ca] text-[#1F5D42] hover:bg-[#e7f2eb] transition-all shadow-2xs active:scale-95 disabled:opacity-60"
            title="Click to refresh inventory and products from the store"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isSyncing ? "bg-amber-500 animate-ping" : "bg-emerald-500"}`} />
            <span>{isSyncing ? (isHindi ? "अपडेट हो रहा है..." : "Syncing...") : (isHindi ? "लाइव सिंक" : "Live Sync")}</span>
            <RefreshCw className={`w-2.5 h-2.5 ${isSyncing ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* 4. Blinkit Two-Column Layout (Left: Root Categories Rail, Right: Subcategories + Products) */}
        <div className="flex gap-2 sm:gap-4 items-start">
          {/* Left Vertical Categories Rail */}
          <aside className="w-20 sm:w-44 shrink-0 bg-white rounded-2xl border border-[#e2ddd4] p-1.5 shadow-2xs sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto no-scrollbar space-y-1">
            {/* All Products Option */}
            <button
              onClick={() => handleSelectRootCategory("all")}
              className={`w-full flex flex-col sm:flex-row items-center sm:gap-2 p-2 rounded-xl text-center sm:text-left transition-all ${
                selectedRootCategory === "all"
                  ? "bg-[#1F5D42] text-white font-bold shadow-xs scale-[1.02]"
                  : "text-[#5e665f] hover:bg-[#f6f0e6]"
              }`}
            >
              <span className="text-lg select-none">🏪</span>
              <div className="min-w-0">
                <span className="text-[10px] sm:text-xs block truncate leading-tight">
                  {isHindi ? "सभी सामान" : "All Items"}
                </span>
                <span
                  className={`text-[9px] font-mono hidden sm:block ${
                    selectedRootCategory === "all" ? "text-emerald-200" : "text-slate-400"
                  }`}
                >
                  {products.length} items
                </span>
              </div>
            </button>

            {/* Root Categories from Backend */}
            {rootCategories.map((cat) => {
              const isSelected = selectedRootCategory === cat.id;
              const icon = getCategoryIcon(cat.name);
              const catProductCount = products.filter((p) =>
                p.categories?.some((c) => c.id === cat.id || c.parent === cat.id)
              ).length;

              return (
                <button
                  key={cat.id}
                  onClick={() => handleSelectRootCategory(cat.id)}
                  className={`w-full flex flex-col sm:flex-row items-center sm:gap-2 p-2 rounded-xl text-center sm:text-left transition-all relative ${
                    isSelected
                      ? "bg-[#1F5D42] text-white font-bold shadow-xs scale-[1.02]"
                      : "text-[#5e665f] hover:bg-[#f6f0e6]"
                  }`}
                >
                  <span className="text-lg select-none">{icon}</span>
                  <div className="min-w-0">
                    <span className="text-[10px] sm:text-xs block line-clamp-2 leading-tight">
                      {cat.name}
                    </span>
                    <span
                      className={`text-[9px] font-mono hidden sm:block ${
                        isSelected ? "text-emerald-200" : "text-slate-400"
                      }`}
                    >
                      {catProductCount} items
                    </span>
                  </div>
                </button>
              );
            })}
          </aside>

          {/* Right Main Content Pane */}
          <main className="flex-1 min-w-0 space-y-3">
            {/* Top Subcategories Filter Bar (when root category has subcategories) */}
            {currentSubcategories.length > 0 && (
              <div className="sticky top-20 z-10 bg-[#f7f4ee]/95 backdrop-blur-md py-1 border-b border-[#e2ddd4]">
                <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
                  <button
                    onClick={() => setSelectedSubcategory("all")}
                    className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all shadow-2xs ${
                      selectedSubcategory === "all"
                        ? "bg-[#E8A33D] text-[#123324] font-bold scale-105"
                        : "bg-white border border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
                    }`}
                  >
                    {isHindi ? "सभी" : "All"}
                  </button>
                  {currentSubcategories.map((sub) => {
                    const isSelected = selectedSubcategory === sub.id;
                    return (
                      <button
                        key={sub.id}
                        onClick={() => setSelectedSubcategory(sub.id)}
                        className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all shadow-2xs ${
                          isSelected
                            ? "bg-[#E8A33D] text-[#123324] font-bold scale-105"
                            : "bg-white border border-[#ddd6ca] text-[#5e665f] hover:bg-[#eee9df]"
                        }`}
                      >
                        {sub.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Empty State */}
            {filteredProducts.length === 0 ? (
              <div className="py-14 bg-white rounded-2xl border border-[#e2ddd4] text-center p-6 space-y-2.5 shadow-2xs">
                <div className="w-12 h-12 rounded-full bg-[#f6f0e6] text-[#7a531d] mx-auto flex items-center justify-center">
                  <Tag className="w-6 h-6" />
                </div>
                <h3 className="font-display font-bold text-base text-[#17251e]">
                  {isHindi ? "कोई सामान नहीं मिला" : "No products found"}
                </h3>
                <p className="text-xs text-[#6d756f] max-w-xs mx-auto">
                  {isHindi
                    ? "कृपया कुछ और खोजें या कोई अन्य श्रेणी चुनें।"
                    : "Try searching for something else or choose another category from the left."}
                </p>
              </div>
            ) : groupedProducts ? (
              /* Grouped by Subcategory (Blinkit Style) */
              <div className="space-y-5">
                {groupedProducts.map((grp) => (
                  <div key={grp.subcategory.id} className="space-y-2">
                    <div className="flex items-center gap-2 border-b border-[#e2ddd4] pb-1 px-1">
                      <span className="font-display font-bold text-xs sm:text-sm text-[#123324]">
                        {grp.subcategory.name}
                      </span>
                      <span className="text-[10px] text-[#6d756f] font-mono">
                        ({grp.products.length})
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {grp.products.map((product) => (
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
                  </div>
                ))}
              </div>
            ) : (
              /* Flat Grid of Products */
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
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
