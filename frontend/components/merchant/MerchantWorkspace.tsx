"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  Activity,
  ArrowRight,
  Check,
  Clock3,
  Copy,
  Download,
  ExternalLink,
  IndianRupee,
  Layers,
  Plus,
  Printer,
  RefreshCw,
  Search,
  ShoppingBag,
  Store,
  UploadCloud,
  UsersRound,
  X,
  ClipboardList,
  AlertTriangle,
  Upload,
  Image as ImageIcon,
  Trash2,
  Boxes,
  CheckCircle2,
  Sparkles,
  MessageCircle,
  Receipt,
  Edit3,
  Minus,
} from "lucide-react";
import { getApiError as getApiErrorEn, InventoryItem, MerchantOrder, merchantApi, Overview, Product, Shop } from "@/lib/api/merchant";
import { BulkExcelUploadModal } from "./BulkExcelUploadModal";
import { OrdersHistoryView } from "./OrdersHistoryView";
import { MerchantProductDetailModal, MerchantProductDetailItem } from "./MerchantProductDetailModal";

type Lang = "en" | "hi";

const currentLang = (): Lang => {
  try {
    return localStorage.getItem("portal_language") === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
};

function useLang(): Lang {
  const [l, setL] = useState<Lang>("en");
  useEffect(() => {
    const sync = () => setL(currentLang());
    sync();
    window.addEventListener("portal-lang-changed", sync);
    return () => window.removeEventListener("portal-lang-changed", sync);
  }, []);
  return l;
}

const API_ERROR_HI: Record<string, string> = {
  "Something went wrong. Please try again.": "कुछ गड़बड़ हो गई। कृपया दोबारा कोशिश करें।",
  "Network Error": "नेटवर्क में समस्या है। इंटरनेट जांचें।",
  "Authentication credentials were not provided.": "कृपया पहले लॉगिन करें।",
  "Invalid token.": "सत्र समाप्त हो गया है। कृपया दोबारा लॉगिन करें।",
  "Not found.": "यह जानकारी नहीं मिली।",
  "You do not have permission to perform this action.": "आपको यह काम करने की अनुमति नहीं है।",
  "This field is required.": "यह जानकारी भरना ज़रूरी है।",
  "This field may not be blank.": "यह जानकारी खाली नहीं हो सकती।",
  "A valid number is required.": "सही संख्या डालें।",
  "Enter a valid URL.": "सही लिंक डालें।",
};

function getApiError(error: unknown) {
  const message = getApiErrorEn(error);
  return currentLang() === "hi" ? (API_ERROR_HI[message] ?? message) : message;
}

const money = (value?: string | number | null) => `₹${Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const dateTime = (value: string, lang: Lang = currentLang()) => new Date(value).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" });

const productSchema = z.object({
  name: z.string().trim().min(1, "Enter a product name"),
  price: z.coerce.number().min(0, "Price cannot be negative"),
  brand: z.string().optional(),
  unit: z.string().optional(),
  sku: z.string().optional(),
  description: z.string().optional(),
});
type ProductValues = z.infer<typeof productSchema>;
type ProductInput = z.input<typeof productSchema>;



const shopSettingsSchema = z.object({
  name: z.string().min(1),
  logo: z.string().optional(),
  description: z.string().optional(),
  address_line: z.string().min(1),
  area: z.string().min(1),
  city: z.string().min(1),
  state: z.string().min(1),
  pincode: z.string().min(1),
  google_maps_url: z.string().optional(),
  opening_time: z.string().optional(),
  closing_time: z.string().optional(),
  is_home_delivery_enabled: z.boolean(),
  is_pickup_enabled: z.boolean(),
  is_temporarily_closed: z.boolean(),
  delivery_fee_type: z.enum(["FIXED", "CONFIRMED_ON_WHATSAPP"]),
  delivery_charge: z.coerce.number().min(0),
  pending_order_timeout_minutes: z.coerce.number().int().min(1),
});
type ShopSettingsValues = z.infer<typeof shopSettingsSchema>;
type ShopSettingsInput = z.input<typeof shopSettingsSchema>;

function Title({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        {eyebrow && <p className="mb-1 text-[10px] font-bold uppercase tracking-[.18em] text-[#1F5D42]">{eyebrow}</p>}
        <h1 className="font-display text-2xl font-bold tracking-tight text-[#123324] sm:text-3xl">{title}</h1>
        {description && <p className="mt-1 text-xs text-[#6d756f]">{description}</p>}
      </div>
      {action}
    </div>
  );
}

function Notice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const lang = useLang();
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-[#f0d8d1] bg-[#fff8f5] p-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-semibold text-[#883f2e]">{lang === "hi" ? "यह जानकारी लोड नहीं हो सकी" : "Couldn’t load this information"}</p>
        <p className="mt-1 text-xs text-[#9c6555]">{getApiError(error)}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-2 self-start rounded-lg border border-[#ead0c8] bg-white px-3 py-2 text-xs font-semibold text-[#734c40]">
          <RefreshCw size={13} />{lang === "hi" ? "दोबारा कोशिश करें" : "Try again"}
        </button>
      )}
    </div>
  );
}

function LoadingRows() {
  return (
    <div className="space-y-3 rounded-2xl border border-[#ddd6ca] bg-white p-5">
      {[1, 2, 3, 4].map((n) => <div key={n} className="h-11 animate-pulse rounded-lg bg-[#eee9df]" />)}
    </div>
  );
}

function Metric({ icon: Icon, label, value, note, tint = "green" }: { icon: typeof Activity; label: string; value: string | number; note?: string; tint?: string }) {
  const colors: Record<string, string> = {
    green: "bg-[#e7f2eb] text-[#1F5D42]",
    yellow: "bg-[#fff3db] text-[#8a5b1d]",
    blue: "bg-[#e4edf2] text-[#456b7f]",
    rose: "bg-[#ffece6] text-[#9b4832]",
  };
  return (
    <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-5 shadow-xs">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-[#6d756f]">{label}</p>
          <p className="font-display mt-2 text-2xl font-bold tracking-tight text-[#123324]">{value}</p>
        </div>
        <span className={`grid h-10 w-10 place-items-center rounded-xl ${colors[tint]}`}>
          <Icon size={18} />
        </span>
      </div>
      {note && <p className="mt-2 text-[11px] text-[#7d857e]">{note}</p>}
    </div>
  );
}

const STATUS_HI: Record<string, string> = {
  PENDING: "लंबित",
  ACCEPTED: "स्वीकृत",
  PREPARING: "तैयार हो रहा है",
  READY: "तैयार है",
  OUT_FOR_DELIVERY: "डिलीवरी के लिए निकला",
  COMPLETED: "पूरा हुआ",
  REJECTED: "अस्वीकृत",
  CANCELLED: "रद्द",
  PICKUP: "दुकान से पिकअप",
  HOME_DELIVERY: "होम डिलीवरी",
  PAID: "भुगतान हुआ",
  UNPAID: "भुगतान बाकी",
  REFUNDED: "रिफंड हुआ",
  FAILED: "असफल",
};

function StatusPill({ status }: { status: string }) {
  const lang = useLang();
  const color =
    status === "PENDING"
      ? "bg-[#fff1d9] text-[#8c5c1e] border border-[#f3ddb6]"
      : status === "REJECTED"
      ? "bg-[#fde8de] text-[#9a4d2a] border border-[#f7cdbb]"
      : status === "COMPLETED"
      ? "bg-[#e4f2e9] text-[#276746] border border-[#c6e6d1]"
      : "bg-[#e7f0ed] text-[#345c47] border border-[#cbe1d5]";
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wide ${color}`}>{lang === "hi" && STATUS_HI[status] ? STATUS_HI[status] : status.replaceAll("_", " ")}</span>;
}

export default function MerchantWorkspace() {
  const pathname = usePathname();
  const section = pathname.split("/")[2] || "overview";
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState("today");
  const [search, setSearch] = useState("");
  const [newProductOpen, setNewProductOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [activeProductDetail, setActiveProductDetail] = useState<MerchantProductDetailItem | null>(null);
  const [pendingItemId, setPendingItemId] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [catalogTab, setCatalogTab] = useState<"shop" | "master">("shop");
  const [masterSearch, setMasterSearch] = useState("");
  const [masterBrandFilter, setMasterBrandFilter] = useState("ALL");
  const [masterCategoryFilter, setMasterCategoryFilter] = useState("ALL");

  // Inventory Filters and Price Editing State
  const [inventorySearch, setInventorySearch] = useState("");
  const [inventoryBrandFilter, setInventoryBrandFilter] = useState("ALL");
  const [inventoryCategoryFilter, setInventoryCategoryFilter] = useState("ALL");
  const [editingPriceItem, setEditingPriceItem] = useState<{
    productId: number;
    name: string;
    price: string;
    mrp: string;
  } | null>(null);
  const [editPriceLoading, setEditPriceLoading] = useState(false);
  const [editPriceError, setEditPriceError] = useState<string | null>(null);

  useEffect(() => {
    const syncLang = () => {
      const saved = (localStorage.getItem("portal_language") as "en" | "hi") || "en";
      setLang(saved);
    };
    syncLang();
    window.addEventListener("portal-lang-changed", syncLang);
    return () => window.removeEventListener("portal-lang-changed", syncLang);
  }, []);

  const analytics = useQuery({ queryKey: ["merchant", "analytics", period], queryFn: () => merchantApi.analytics(period), enabled: ["overview", "analytics"].includes(section) });
  const orders = useQuery({ queryKey: ["merchant", "orders"], queryFn: merchantApi.orders, enabled: ["overview", "orders", "customers"].includes(section), refetchInterval: ["overview", "orders"].includes(section) ? 10000 : false });
  const products = useQuery({ queryKey: ["merchant", "products"], queryFn: merchantApi.products, enabled: ["overview", "catalog", "inventory"].includes(section) });
  const categories = useQuery({ queryKey: ["merchant", "categories"], queryFn: merchantApi.categories, enabled: ["catalog", "inventory"].includes(section) });
  const masterCatalog = useQuery({ queryKey: ["merchant", "master-catalog"], queryFn: merchantApi.getMasterCatalog, enabled: section === "catalog" });
  const stock = useQuery({ queryKey: ["merchant", "inventory"], queryFn: merchantApi.inventory, enabled: ["overview", "inventory"].includes(section) });
  const customers = useQuery({ queryKey: ["merchant", "customers"], queryFn: merchantApi.customers, enabled: section === "customers" });
  const shop = useQuery({ queryKey: ["merchant", "shop"], queryFn: merchantApi.shop });

  const refresh = (key?: string) => queryClient.invalidateQueries({ queryKey: key ? ["merchant", key] : ["merchant"] });

  const toggleMasterMutation = useMutation({
    mutationFn: ({ master_product_id, selected, price }: { master_product_id: number; selected: boolean; price?: string }) =>
      merchantApi.toggleMasterProduct(master_product_id, selected, price),
    onSuccess: (res) => {
      setNotice(
        res.is_in_shop
          ? (lang === "hi" ? "आइटम आपकी दुकान में जोड़ दिया गया (✓)" : "Item added to your Dukaan (✓)")
          : (lang === "hi" ? "आइटम आपकी दुकान से हटा दिया गया (✗)" : "Item removed from your Dukaan (✗)")
      );
      refresh("master-catalog");
      refresh("products");
      refresh("inventory");
    },
    onError: (e) => setNotice(getApiError(e)),
  });

  const orderMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) => merchantApi.orderAction(id, action),
    onSuccess: () => {
      setNotice(lang === "hi" ? "ऑर्डर सफलतापूर्वक अपडेट हुआ।" : "Order updated successfully.");
      refresh("orders");
      refresh("analytics");
    },
    onError: (e) => setNotice(getApiError(e)),
  });

  const stockMutation = useMutation({
    mutationFn: ({ item, action, quantity }: { item: InventoryItem; action: "set-stock" | "add-stock" | "subtract-stock"; quantity: string }) =>
      merchantApi.updateStock(item.id, action, quantity),
    onMutate: async ({ item, action, quantity }) => {
      setPendingItemId(item.id);
      await queryClient.cancelQueries({ queryKey: ["merchant", "inventory"] });
      const previous = queryClient.getQueryData<InventoryItem[]>(["merchant", "inventory"]);

      if (previous) {
        const qtyNum = Number(quantity) || 0;
        queryClient.setQueryData<InventoryItem[]>(["merchant", "inventory"], (old) => {
          if (!old) return [];
          return old.map((it) => {
            if (it.id !== item.id) return it;
            let newQty = Number(it.available_quantity);
            if (action === "set-stock") newQty = qtyNum;
            else if (action === "add-stock") newQty += qtyNum;
            else if (action === "subtract-stock") newQty = Math.max(0, newQty - qtyNum);
            return {
              ...it,
              available_quantity: String(newQty),
              quantity: String(newQty),
              is_out_of_stock: newQty <= 0,
            };
          });
        });
      }
      return { previous };
    },
    onError: (e, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["merchant", "inventory"], context.previous);
      }
      setNotice(getApiError(e));
    },
    onSettled: () => {
      setPendingItemId(null);
      refresh("inventory");
      refresh("analytics");
    },
  });

  const productMutation = useMutation({
    mutationFn: (payload: (Partial<Product> & { name: string }) | FormData) =>
      merchantApi.createProduct(payload),
    onSuccess: () => {
      setNewProductOpen(false);
      setNotice(lang === "hi" ? "प्रोडक्ट कैटलॉग में सफलतापूर्वक जोड़ा गया।" : "Product added to your catalog.");
      refresh("products");
    },
    onError: (e) => setNotice(getApiError(e)),
  });

  const handleSaveProductPrice = async (price: string, mrp: string) => {
    if (!editingPriceItem) return;
    setEditPriceLoading(true);
    setEditPriceError(null);
    try {
      await merchantApi.updateProduct(editingPriceItem.productId, {
        price: price.trim(),
        mrp: mrp.trim() || undefined,
      });
      setNotice(lang === "hi" ? "विक्रय मूल्य व MRP सफलतापूर्वक अपडेट हो गया।" : "Price & MRP updated successfully.");
      setEditingPriceItem(null);
      refresh("products");
      refresh("inventory");
      refresh("master-catalog");
    } catch (err: any) {
      setEditPriceError(err.response?.data?.price?.[0] || err.message || (lang === "hi" ? "मूल्य अपडेट नहीं हो सका" : "Failed to update price"));
    } finally {
      setEditPriceLoading(false);
    }
  };

  const filteredOrders = useMemo(
    () => (orders.data ?? []).filter((row) => `${row.id} ${row.customer_name_snapshot} ${row.customer_phone_snapshot} ${row.status}`.toLowerCase().includes(search.toLowerCase())),
    [orders.data, search]
  );

  const productMap = useMemo(() => new Map((products.data ?? []).map((p) => [p.id, p])), [products.data]);

  const categoryMap = useMemo(
    () => new Map((categories.data ?? []).map((c) => [c.id, c.name])),
    [categories.data]
  );

  const inventoryCategories = useMemo(() => {
    const set = new Set<string>();
    (products.data ?? []).forEach((p) => {
      const catName = p.category_name || (p.categories?.[0] ? categoryMap.get(p.categories[0]) : undefined);
      if (catName) set.add(catName);
    });
    return Array.from(set).sort();
  }, [products.data, categoryMap]);

  const inventoryBrands = useMemo(() => {
    const set = new Set<string>();
    (products.data ?? []).forEach((p) => {
      if (p.brand) set.add(p.brand);
    });
    return Array.from(set).sort();
  }, [products.data]);

  const filteredStock = useMemo(() => {
    return (stock.data ?? []).filter((item) => {
      const prod = productMap.get(item.product);
      const prodCat = prod?.category_name || (prod?.categories?.[0] ? categoryMap.get(prod.categories[0]) : undefined);
      if (inventoryCategoryFilter !== "ALL" && prodCat !== inventoryCategoryFilter) {
        return false;
      }
      if (inventoryBrandFilter !== "ALL" && prod?.brand !== inventoryBrandFilter) {
        return false;
      }
      if (inventorySearch.trim()) {
        const q = inventorySearch.toLowerCase();
        const matchesName = item.product_name?.toLowerCase().includes(q);
        const matchesBrand = prod?.brand?.toLowerCase().includes(q);
        const matchesSku = item.sku?.toLowerCase().includes(q);
        if (!matchesName && !matchesBrand && !matchesSku) return false;
      }
      return true;
    });
  }, [stock.data, productMap, categoryMap, inventoryCategoryFilter, inventoryBrandFilter, inventorySearch]);

  const masterCategories = useMemo(() => {
    const set = new Set<string>();
    (masterCatalog.data ?? []).forEach((mp) => {
      if (mp.category_name) set.add(mp.category_name);
    });
    return Array.from(set).sort();
  }, [masterCatalog.data]);

  const masterBrands = useMemo(() => {
    const set = new Set<string>();
    (masterCatalog.data ?? []).forEach((mp) => {
      if (mp.brand) set.add(mp.brand);
    });
    return Array.from(set).sort();
  }, [masterCatalog.data]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  // Section 01: Home / My QR
  if (section === "overview") {
    return (
      <MyQrHomePage
        shop={shop.data}
        analytics={analytics}
        orders={orders}
        period={period}
        setPeriod={setPeriod}
        onToggleStatus={async () => {
          if (!shop.data) return;
          try {
            await merchantApi.updateShop({ is_temporarily_closed: !shop.data.is_temporarily_closed });
            refresh("shop");
            setNotice(
              !shop.data.is_temporarily_closed
                ? (lang === "hi" ? "दुकान अस्थायी रूप से बंद कर दी गई है।" : "Store is now marked as Closed.")
                : (lang === "hi" ? "दुकान सफलतापूर्वक खोल दी गई है।" : "Store is now marked as Open!")
            );
          } catch (e) {
            setNotice(getApiError(e));
          }
        }}
        lang={lang}
      />
    );
  }

  // Section 02: Inventory
  if (section === "inventory") {
    return (
      <>
        <Title
          eyebrow={lang === "hi" ? "दुकान का स्टॉक" : "Store Stock"}
          title={lang === "hi" ? "इन्वेंट्री" : "Inventory"}
          description={
            lang === "hi"
              ? "दुकान का स्टॉक बढ़ाएं/घटाएं, 'स्टॉक में नहीं' टॉगल करें, और उत्पाद का विक्रय मूल्य व MRP सीधे बदलें।"
              : "Directly manage stock quantity, toggle Out of Stock status, and adjust selling prices."
          }
          action={
            <div className="flex gap-2">
              <button
                onClick={() => {
                  refresh("inventory");
                  refresh("products");
                }}
                className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-xs font-semibold text-[#1F5D42] hover:bg-[#F6F0E6] cursor-pointer shadow-xs transition"
              >
                <RefreshCw size={14} />
                <span>{lang === "hi" ? "रिफ्रेश" : "Refresh"}</span>
              </button>
            </div>
          }
        />

        {/* Filter Bar: Search, Category, Brand */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 bg-white p-3.5 rounded-2xl border border-[#ddd6ca] shadow-xs">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8b948d]" />
            <input
              type="text"
              value={inventorySearch}
              onChange={(e) => setInventorySearch(e.target.value)}
              placeholder={lang === "hi" ? "सामान या ब्रांड खोजें..." : "Search inventory items or brands..."}
              className="w-full pl-9 pr-3 py-2 bg-white border border-[#ddd6ca] rounded-xl text-xs outline-none focus:border-[#1F5D42]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={inventoryCategoryFilter}
              onChange={(e) => setInventoryCategoryFilter(e.target.value)}
              className="h-9 px-3 rounded-xl border border-[#ddd6ca] bg-white text-xs text-[#123324] font-medium outline-none focus:border-[#1F5D42]"
            >
              <option value="ALL">{lang === "hi" ? "सभी श्रेणियां" : "All Categories"}</option>
              {inventoryCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <select
              value={inventoryBrandFilter}
              onChange={(e) => setInventoryBrandFilter(e.target.value)}
              className="h-9 px-3 rounded-xl border border-[#ddd6ca] bg-white text-xs text-[#123324] font-medium outline-none focus:border-[#1F5D42]"
            >
              <option value="ALL">{lang === "hi" ? "सभी ब्रांड" : "All Brands"}</option>
              {inventoryBrands.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Inventory Items List */}
        <div className="space-y-4">
          {stock.isLoading ? (
            <LoadingRows />
          ) : stock.isError ? (
            <Notice error={stock.error} onRetry={() => stock.refetch()} />
          ) : (
            <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] overflow-hidden shadow-xs">
              <div className="border-b border-[#eee9df] bg-[#f8f6f0] px-5 py-3 flex justify-between items-center text-xs font-bold text-[#123324]">
                <span>{lang === "hi" ? "दुकान इन्वेंट्री सूची" : "Store Inventory List"}</span>
                <span className="text-[#6d756f] font-normal">
                  {filteredStock.length} / {stock.data?.length ?? 0} {lang === "hi" ? "सामान" : "items"}
                </span>
              </div>
              {filteredStock.length === 0 ? (
                <div className="p-8 text-center text-xs text-[#6d756f]">
                  {lang === "hi" ? "कोई सामान इस फ़िल्टर में नहीं मिला।" : "No inventory items match the selected filter."}
                </div>
              ) : (
                <div className="divide-y divide-[#eee9df]">
                  {filteredStock.map((item) => {
                    const prod = productMap.get(item.product);
                    return (
                      <InventoryTickRow
                        key={item.id}
                        item={item}
                        product={prod}
                        lang={lang}
                        onSave={(action, quantity) => stockMutation.mutate({ item, action, quantity })}
                        onEditPrice={() => {
                          if (prod) {
                            setEditingPriceItem({
                              productId: prod.id,
                              name: prod.name,
                              price: String(prod.price ?? ""),
                              mrp: String(prod.mrp ?? prod.price ?? ""),
                            });
                          }
                        }}
                        busy={pendingItemId === item.id}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {editingPriceItem && (
          <EditPriceModal
            item={editingPriceItem}
            loading={editPriceLoading}
            error={editPriceError}
            lang={lang}
            onClose={() => setEditingPriceItem(null)}
            onSave={(price, mrp) => handleSaveProductPrice(price, mrp)}
          />
        )}
        {notice && <Toast text={notice} onClose={() => setNotice("")} />}
      </>
    );
  }

  // Section 03: Orders with Per-Item Resolve
  if (section === "orders") {
    return (
      <>
        <Title
          eyebrow={lang === "hi" ? "ऑर्डर डेस्क" : "Order desk"}
          title={lang === "hi" ? "नए आने वाले ऑर्डर्स" : "Incoming orders"}
          description={
            lang === "hi"
              ? "ग्राहकों के ऑर्डर्स को तुरंत पूरा करें। अनुपलब्ध सामान को व्यक्तिगत रूप से सुलझाएं।"
              : "Keep the rest of the order moving. Resolve out-of-stock items individually."
          }
          action={
            <button
              onClick={() => refresh("orders")}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-xs font-semibold text-[#1F5D42] hover:bg-[#F6F0E6] cursor-pointer"
            >
              <RefreshCw size={14} />
              <span>{lang === "hi" ? "डेस्क रिफ्रेश करें" : "Refresh Desk"}</span>
            </button>
          }
        />

        <div className="mb-4 flex flex-col gap-3 rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-[320px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#98a39a]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={lang === "hi" ? "ऑर्डर # या ग्राहक फोन से खोजें..." : "Search by order or customer phone"}
              className="h-10 w-full rounded-xl bg-white border border-[#ddd6ca] pl-9 pr-3 text-xs outline-none focus:border-[#1F5D42]"
            />
          </div>
          <p className="text-xs text-[#6d756f]">
            {filteredOrders.length} {lang === "hi" ? "ऑर्डर्स · प्रति 10 सेकंड में स्वतः लाइव अपडेट" : "orders · live polling every 10s"}
          </p>

        </div>

        {orders.isLoading ? (
          <LoadingRows />
        ) : orders.isError ? (
          <Notice error={orders.error} onRetry={() => orders.refetch()} />
        ) : (
          <div className="space-y-4">
            {filteredOrders.length ? (
              filteredOrders.map((order) => (
                <VisualOrderCard
                  key={order.id}
                  order={order}
                  lang={lang}
                  onAction={(action) => orderMutation.mutate({ id: order.id, action })}
                  busy={orderMutation.isPending}
                  onItemResolved={(itemName) => {
                    setNotice(
                      lang === "hi"
                        ? `'${itemName}' ऑर्डर #${order.id} से हटा दिया गया। कुल रकम अपडेट हो गई।`
                        : `Item '${itemName}' removed from Order #${order.id}. Total adjusted.`
                    );
                    refresh("orders");
                  }}
                />
              ))
            ) : (
              <Empty icon={ClipboardList} title={lang === "hi" ? "कोई नया ऑर्डर नहीं" : "No incoming orders"} text={lang === "hi" ? "आपके QR स्टोर से आने वाले नए ऑर्डर यहां तुरंत दिखेंगे।" : "New orders placed from your QR store will appear here in real time."} />
            )}
          </div>
        )}
        {notice && <Toast text={notice} onClose={() => setNotice("")} />}
      </>
    );
  }

  // Section 04: Simple Analytics
  if (section === "analytics") {
    return (
      <>
        <Title
          eyebrow={lang === "hi" ? "दुकान प्रदर्शन" : "Shop Performance"}
          title={lang === "hi" ? "व्यापार विश्लेषण" : "Business Analytics"}
          description={
            period === "today"
              ? (lang === "hi" ? "आज का लाइव ऑर्डर व बिक्री डेटा" : "Live order & sales telemetry for today")
              : period === "yesterday"
              ? (lang === "hi" ? "कल का ऑर्डर व बिक्री डेटा" : "Order & sales telemetry for yesterday")
              : period === "this_week"
              ? (lang === "hi" ? "इस सप्ताह का ऑर्डर व बिक्री डेटा" : "Order & sales telemetry for this week")
              : (lang === "hi" ? "इस माह का ऑर्डर व बिक्री डेटा" : "Order & sales telemetry for this month")
          }
          action={<PeriodSelect value={period} onChange={setPeriod} />}
        />
        {analytics.isLoading ? (
          <LoadingRows />
        ) : analytics.isError ? (
          <Notice error={analytics.error} onRetry={() => analytics.refetch()} />
        ) : (
          <VisualAnalyticsPanel data={analytics.data!} period={period} lang={lang} />
        )}
      </>
    );
  }

  // Catalog / Products Section
  if (section === "catalog") {
    const sortedShopProducts = [...(products.data ?? [])].sort((a, b) =>
      (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" })
    );

    const filteredMaster = (masterCatalog.data ?? []).filter((mp) => {
      if (masterCategoryFilter !== "ALL" && mp.category_name !== masterCategoryFilter) return false;
      if (masterBrandFilter !== "ALL" && mp.brand !== masterBrandFilter) return false;
      if (!masterSearch.trim()) return true;
      const q = masterSearch.toLowerCase();
      return (
        mp.name?.toLowerCase().includes(q) ||
        mp.brand?.toLowerCase().includes(q) ||
        mp.category_name?.toLowerCase().includes(q) ||
        mp.description?.toLowerCase().includes(q)
      );
    });

    return (
      <>
        <Title
          eyebrow={lang === "hi" ? "आपकी दुकान" : "Your store"}
          title={lang === "hi" ? "उत्पाद कैटलॉग (A-Z)" : "Product catalog (A-Z)"}
          description={
            lang === "hi"
              ? "दुकान में दिखने वाले सामान प्रबंधित करें, या प्रमाणित मास्टर कैटलॉग से एक क्लिक में जोड़ें।"
              : "Manage products customers can discover in your shop, or add verified items from the platform Master Catalog."
          }
          action={
            catalogTab === "shop" ? (
              <button
                onClick={() => setNewProductOpen(true)}
                className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#1F5D42] px-4 text-xs font-bold text-white hover:bg-[#123324] shadow-xs transition cursor-pointer"
              >
                <Plus size={15} />
                <span>{lang === "hi" ? "+ नया सामान जोड़ें" : "Add custom product"}</span>
              </button>
            ) : null
          }
        />

        {/* Catalog Navigation Tabs */}
        <div className="mb-5 flex flex-wrap items-center gap-2 border-b border-[#ddd6ca] pb-3">
          <button
            onClick={() => setCatalogTab("shop")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${
              catalogTab === "shop"
                ? "bg-[#1F5D42] text-white shadow-xs"
                : "bg-white border border-[#ddd6ca] text-[#123324] hover:bg-[#F6F0E6]"
            }`}
          >
            {lang === "hi"
              ? `मेरी दुकान के प्रोडक्ट्स (${sortedShopProducts.length})`
              : `My Dukaan Products (${sortedShopProducts.length})`}
          </button>
          <button
            onClick={() => setCatalogTab("master")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              catalogTab === "master"
                ? "bg-[#1F5D42] text-white shadow-xs"
                : "bg-white border border-[#ddd6ca] text-[#123324] hover:bg-[#F6F0E6]"
            }`}
          >
            <Boxes size={14} />
            <span>
              {lang === "hi"
                ? `मास्टर कैटलॉग से चुनें (${masterCatalog.data?.length ?? 0})`
                : `Select from Master Catalog (${masterCatalog.data?.length ?? 0})`}
            </span>
          </button>
        </div>

        {catalogTab === "shop" ? (
          products.isLoading ? (
            <LoadingRows />
          ) : products.isError ? (
            <Notice error={products.error} onRetry={() => products.refetch()} />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-[#ddd6ca] bg-white">
              <div className="grid grid-cols-[1.4fr_.7fr_.7fr_.6fr] gap-3 border-b border-[#eee9df] bg-[#faf8f3] px-5 py-3 text-[10px] font-bold uppercase tracking-[.13em] text-[#6d756f]">
                <span>{lang === "hi" ? "उत्पाद विवरण" : "Product"}</span>
                <span>{lang === "hi" ? "विक्रय मूल्य" : "Price"}</span>
                <span>{lang === "hi" ? "स्थिति" : "Visibility"}</span>
                <span>{lang === "hi" ? "क्रिया" : "Action"}</span>
              </div>
              {sortedShopProducts.length ? (
                sortedShopProducts.map((item) => (
                  <ProductRow
                    key={item.id}
                    product={item}
                    lang={lang}
                    onViewDetail={() =>
                      setActiveProductDetail({
                        id: item.id,
                        name: item.name,
                        price: item.price,
                        mrp: item.mrp ?? undefined,
                        brand: item.brand ?? undefined,
                        description: item.description ?? undefined,
                        image: item.effective_image || item.image || undefined,
                        sku: item.sku ?? undefined,
                        is_available: item.is_available,
                        is_visible: item.is_visible,
                      })
                    }
                    onToggle={() =>
                      merchantApi
                        .updateProduct(item.id, { is_visible: !item.is_visible })
                        .then(() => refresh("products"))
                        .catch((e) => setNotice(getApiError(e)))
                    }
                    onDelete={() => {
                      if (window.confirm(lang === "hi" ? `${item.name} को कैटलॉग से हटाएं?` : `Remove ${item.name} from catalog?`))
                        merchantApi
                          .deleteProduct(item.id)
                          .then(() => refresh("products"))
                          .catch((e) => setNotice(getApiError(e)));
                    }}
                  />
                ))
              ) : (
                <Empty icon={ShoppingBag} title={lang === "hi" ? "कैटलॉग खाली है" : "Your catalog is ready"} text={lang === "hi" ? "नए उत्पाद जोड़ें या मास्टर कैटलॉग से एक क्लिक में सामान जोड़ें।" : "Add products so customers can browse and order from your shop, or click 'Select from Master Catalog' to import verified items with one click."} />
              )}
            </div>
          )
        ) : (
          /* Master Catalog Browser with Tick / Cross Selection */
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-[#ddd6ca] shadow-xs">
              <div className="relative flex-1 max-w-sm">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8b948d]" />
                <input
                  type="text"
                  value={masterSearch}
                  onChange={(e) => setMasterSearch(e.target.value)}
                  placeholder={lang === "hi" ? "मास्टर प्रोडक्ट्स में खोजें..." : "Search Master Catalog items..."}
                  className="w-full pl-9 pr-3 py-2 bg-white border border-[#ddd6ca] rounded-xl text-xs outline-none focus:border-[#1F5D42]"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={masterCategoryFilter}
                  onChange={(e) => setMasterCategoryFilter(e.target.value)}
                  className="h-9 px-3 rounded-xl border border-[#ddd6ca] bg-white text-xs text-[#123324] font-medium outline-none focus:border-[#1F5D42]"
                >
                  <option value="ALL">{lang === "hi" ? "सभी श्रेणियां" : "All Categories"}</option>
                  {masterCategories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>

                <select
                  value={masterBrandFilter}
                  onChange={(e) => setMasterBrandFilter(e.target.value)}
                  className="h-9 px-3 rounded-xl border border-[#ddd6ca] bg-white text-xs text-[#123324] font-medium outline-none focus:border-[#1F5D42]"
                >
                  <option value="ALL">{lang === "hi" ? "सभी ब्रांड" : "All Brands"}</option>
                  {masterBrands.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {masterCatalog.isLoading ? (
              <LoadingRows />
            ) : masterCatalog.isError ? (
              <Notice error={masterCatalog.error} onRetry={() => masterCatalog.refetch()} />
            ) : filteredMaster.length === 0 ? (
              <div className="bg-white rounded-2xl border border-[#ddd6ca] p-8 text-center text-[#869088]">
                <Boxes className="w-8 h-8 mx-auto text-[#b2bcae] mb-2 opacity-50" />
                <p className="font-semibold text-sm text-[#123324]">{lang === "hi" ? "कोई मास्टर उत्पाद नहीं मिला" : "No master products found"}</p>
                <p className="text-xs text-[#6d756f] mt-1">{lang === "hi" ? "खोज के अनुरूप कोई सामान उपलब्ध नहीं है।" : "Super Admin has not added any master items matching this search yet."}</p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {filteredMaster.map((item) => {
                  const itemImg = item.effective_image || item.image || item.image_url;
                  return (
                    <div
                      key={item.id}
                      className={`rounded-2xl border p-4 transition flex flex-col justify-between ${
                        item.is_in_shop
                          ? "bg-[#f4f9f6] border-[#a8d3ba] shadow-xs ring-1 ring-[#1F5D42]/20"
                          : "bg-white border-[#ddd6ca] hover:border-[#bbb0a0]"
                      }`}
                    >
                      <div>
                        <div
                          className="flex items-start gap-3 mb-3 cursor-pointer group"
                          onClick={() =>
                            setActiveProductDetail({
                              id: item.id,
                              name: item.name,
                              price: item.mrp ?? 0,
                              mrp: item.mrp ?? undefined,
                              brand: item.brand ?? undefined,
                              category_name: item.category_name ?? undefined,
                              description: item.description ?? undefined,
                              image: itemImg || undefined,
                              is_in_shop: item.is_in_shop,
                            })
                          }
                        >
                          {itemImg ? (
                            <img
                              src={itemImg}
                              alt={item.name}
                              className="w-12 h-12 object-cover rounded-xl border border-[#ddd6ca] shrink-0 bg-white group-hover:scale-105 transition"
                            />
                          ) : (
                            <div className="w-12 h-12 rounded-xl bg-[#eee9df] flex items-center justify-center text-[#6d756f] shrink-0 group-hover:bg-[#e7f2eb] transition">
                              <ImageIcon className="w-5 h-5 text-[#869088]" />
                            </div>
                          )}
                          <div className="min-w-0 flex-1">
                            <h4 className="font-bold text-sm text-[#123324] leading-snug line-clamp-2 group-hover:text-[#1F5D42] transition underline-offset-2 group-hover:underline">
                              {item.name}
                            </h4>
                            <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                              {item.brand && (
                                <span className="text-[10px] font-bold text-[#8a5b1d] bg-[#fff3db] px-2 py-0.5 rounded-full border border-[#f5deb5]">
                                  {item.brand}
                                </span>
                              )}
                              <span className="text-[10px] font-medium text-[#1F5D42] bg-[#e7f2eb] px-2 py-0.5 rounded-full border border-[#cbe1d5]">
                                {item.category_name || (lang === "hi" ? "किराना" : "Grocery")}
                              </span>
                              {item.unit && (
                                <span className="text-[10px] font-semibold text-[#1F5D42] bg-[#FAF8F3] px-2 py-0.5 rounded-full border border-[#ddd6ca]">
                                  {item.unit}
                                </span>
                              )}
                              {item.mrp && (
                                <span className="text-[10px] font-mono font-bold text-[#123324] bg-[#F6F0E6] px-2 py-0.5 rounded-full">
                                  MRP: ₹{item.mrp}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {item.description && (
                          <p className="text-xs text-[#6d756f] line-clamp-2 mb-3">
                            {item.description}
                          </p>
                        )}
                      </div>

                      {/* Tick / Cross Status and Action Bar */}
                      <div className="pt-3 border-t border-[#eee9df] flex items-center justify-between gap-2">
                        {item.is_in_shop ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#1F5D42]">
                            <CheckCircle2 className="w-3.5 h-3.5 text-[#1F5D42]" />
                            <span>{lang === "hi" ? "दुकान में उपलब्ध (✓)" : "In My Dukaan (✓)"}</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#869088]">
                            <X className="w-3.5 h-3.5 text-[#869088]" />
                            <span>{lang === "hi" ? "दुकान में नहीं (✗)" : "Not in Dukaan (✗)"}</span>
                          </span>
                        )}

                        <button
                          type="button"
                          disabled={toggleMasterMutation.isPending}
                          onClick={() =>
                            toggleMasterMutation.mutate({
                              master_product_id: item.id,
                              selected: !item.is_in_shop,
                            })
                          }
                          className={`px-3 py-1.5 rounded-xl text-xs font-bold transition shadow-2xs cursor-pointer ${
                            item.is_in_shop
                              ? "bg-red-50 hover:bg-red-100 text-red-700 border border-red-200"
                              : "bg-[#1F5D42] hover:bg-[#123324] text-white"
                          }`}
                        >
                          {item.is_in_shop
                            ? (lang === "hi" ? "हटाएं ✗" : "Remove ✗")
                            : (lang === "hi" ? "+ जोड़ें ✓" : "+ Add to Dukaan ✓")}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {newProductOpen && (
          <ProductModal lang={lang} onClose={() => setNewProductOpen(false)} onSave={(payload) => productMutation.mutate(payload)} saving={productMutation.isPending} />
        )}
        {activeProductDetail && (
          <MerchantProductDetailModal
            product={activeProductDetail}
            onClose={() => setActiveProductDetail(null)}
            lang={lang}
          />
        )}
        {notice && <Toast text={notice} onClose={() => setNotice("")} />}
      </>
    );
  }

  // Orders History Section (formerly Customers)
  if (section === "customers") {
    return (
      <OrdersHistoryView
        orders={orders.data ?? []}
        loading={orders.isLoading}
        error={orders.error}
        onRefresh={() => refresh("orders")}
        lang={lang}
      />
    );
  }

  // Shop Settings Section
  if (section === "settings") {
    return <ShopSettings shop={shop.data} loading={shop.isLoading} error={shop.error} refetch={() => shop.refetch()} onSaved={() => refresh("shop")} lang={lang} />;
  }

  return (
    <div className="rounded-2xl border border-[#ddd6ca] bg-white p-8">
      <h1 className="text-xl font-semibold">{lang === "hi" ? "यह पेज उपलब्ध नहीं है" : "This page isn’t available"}</h1>
      <p className="mt-2 text-sm text-[#78867c]">{lang === "hi" ? "मेन्यू से कोई सेक्शन चुनें।" : "Choose a section from the navigation."}</p>
    </div>
  );
}

// -------------------------------------------------------------
// Visual Board Component 1: Home / My QR
// -------------------------------------------------------------
function MyQrHomePage({
  shop,
  analytics,
  orders,
  period,
  setPeriod,
  onToggleStatus,
  lang = "en",
}: {
  shop?: Shop;
  analytics: UseQueryResult<Overview>;
  orders: UseQueryResult<MerchantOrder[]>;
  period: string;
  setPeriod: (val: string) => void;
  onToggleStatus?: () => void;
  lang?: "en" | "hi";
}) {
  const [copied, setCopied] = useState(false);
  const data = analytics.data;

  // Determine current public URL
  const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
  const publicStoreUrl = shop?.public_slug ? `${origin}/shop/${shop.public_slug}` : `${origin}/shop/demo`;
  const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=${encodeURIComponent(publicStoreUrl)}&format=svg`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(publicStoreUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.write(`
      <html>
        <head>
          <title>${shop?.name || (lang === "hi" ? "दुकान" : "Shop")} - ${lang === "hi" ? "QR स्टिकर" : "QR Sticker"}</title>
          <style>
            body { font-family: Inter, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 90vh; margin: 0; background: #faf8f5; }
            .sticker { border: 4px solid #1F5D42; border-radius: 28px; padding: 36px 32px; text-align: center; max-width: 380px; background: #fff; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
            h1 { color: #123324; font-size: 26px; margin: 0 0 6px; font-weight: 800; }
            p { color: #555; margin: 0 0 20px; font-size: 13px; line-height: 1.4; }
            img { width: 220px; height: 220px; border-radius: 12px; }
            .url { font-family: monospace; font-size: 12px; font-weight: bold; color: #1F5D42; margin-top: 14px; word-break: break-all; }
            .badge { background: #E8A33D; color: #123324; font-weight: bold; padding: 6px 14px; border-radius: 99px; display: inline-block; margin-top: 14px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
          </style>
        </head>
        <body>
          <div class="sticker">
            <h1>${shop?.name || "Sharma Kirana"}</h1>
            <p>${lang === "hi" ? "ताज़ा किराना सामान सीधे व्हाट्सएप पर ऑर्डर करने के लिए फ़ोन कैमरे से स्कैन करें" : "Scan with phone camera to order fresh essentials directly on WhatsApp"}</p>
            <img src="${qrApiUrl}" alt="${lang === "hi" ? "दुकान का QR कोड" : "Shop QR Code"}" />
            <div class="url">${publicStoreUrl}</div>
            <div><span class="badge">${lang === "hi" ? "मोबाइल ऐप की ज़रूरत नहीं" : "No Mobile App Required"}</span></div>
          </div>
          <script>window.onload = () => { window.print(); }</script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  return (
    <div className="space-y-6">
      <Title
        eyebrow={lang === "hi" ? "मेरी दुकान" : "My Store Hub"}
        title={shop?.name ?? "Sharma Kirana"}
        description={lang === "hi" ? `मेरी दुकान · ${shop?.city ?? "Jaipur"} · व्हाट्सएप पर खरीदारी के लिए स्कैन करें` : `My shop · ${shop?.city ?? "Jaipur"} · Scan to shop on WhatsApp`}
        action={
          <div className="flex gap-2">
            <button onClick={handlePrint} className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-xs font-semibold text-[#123324] hover:bg-[#F6F0E6]">
              <Printer size={15} />
              <span>{lang === "hi" ? "स्टिकर प्रिंट करें" : "Print Sticker"}</span>
            </button>
            <PeriodSelect value={period} onChange={setPeriod} />
          </div>
        }
      />

      {/* Prominent Dukaan Status Banner & Switch */}
      <div
        className={`rounded-2xl p-4 sm:p-5 border transition flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs ${
          !shop?.is_temporarily_closed
            ? "bg-[#f2faf5] border-[#a2d5ba]"
            : "bg-[#fff6f3] border-[#f8c1b3]"
        }`}
      >
        <div className="flex items-center gap-3.5">
          <div
            className={`w-3.5 h-3.5 rounded-full shrink-0 ${
              !shop?.is_temporarily_closed ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
            }`}
          />
          <div>
            <h3
              className={`text-sm sm:text-base font-bold ${
                !shop?.is_temporarily_closed ? "text-[#1F5D42]" : "text-[#c2410c]"
              }`}
            >
              {!shop?.is_temporarily_closed
                ? (lang === "hi" ? "दुकान खुली है" : "Store is OPEN · Accepting Orders")
                : (lang === "hi" ? "दुकान अस्थायी रूप से बंद है" : "Store is CLOSED · Orders Paused")}
            </h3>
            <p className="text-xs text-[#6d756f] mt-0.5">
              {!shop?.is_temporarily_closed
                ? (lang === "hi"
                    ? "QR कोड स्कैन करके ग्राहक सीधे कैटलॉग देख और ऑर्डर कर सकते हैं।"
                    : "Customers scanning your QR can view catalog and place WhatsApp orders.")
                : (lang === "hi"
                    ? "स्टोरफ्रंट पर 'दुकान बंद है' सूचना दिखेगी। ग्राहक अभी ऑर्डर नहीं कर सकेंगे।"
                    : "Storefront displays closed notification. Customers cannot place orders right now.")}
            </p>
          </div>
        </div>

        {onToggleStatus && (
          <button
            type="button"
            onClick={onToggleStatus}
            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs shadow-xs transition active:scale-95 cursor-pointer shrink-0 ${
              !shop?.is_temporarily_closed
                ? "bg-white border border-[#cbe1d5] text-[#1F5D42] hover:bg-[#e7f2eb]"
                : "bg-[#c2410c] text-white hover:bg-[#9a3412]"
            }`}
          >
            <span>
              {!shop?.is_temporarily_closed
                ? (lang === "hi" ? "दुकान बंद करें ⏸" : "Pause / Close Store ⏸")
                : (lang === "hi" ? "दुकान खोलें ▶" : "Reopen Store ▶")}
            </span>
          </button>
        )}
      </div>

      {/* Visual Board Frame 1: Prominent QR Hub Card */}
      <div className="rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 sm:p-8 shadow-sm">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_1.4fr] items-center">
          {/* QR Display */}
          <div className="flex flex-col items-center justify-center p-6 bg-white rounded-2xl border border-[#ddd6ca] text-center shadow-xs">
            <h4 className="font-display font-bold text-base text-[#123324] mb-1">{lang === "hi" ? "स्कैन करके खरीदारी करें" : "Scan to shop"}</h4>
            <p className="text-[11px] text-[#6d756f] mb-4">{lang === "hi" ? "इसे दुकान के काउंटर, थैलों और स्टिकर पर लगाएं" : "Place on store counter, bags & stickers"}</p>

            <div className="p-3 bg-[#FFFDF8] border-2 border-[#1F5D42] rounded-2xl shadow-xs">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={qrApiUrl}
                alt={lang === "hi" ? "दुकान का QR कोड" : "Store QR Code"}
                className="w-44 h-44 object-contain rounded-lg"
              />
            </div>

            <div className="mt-3 flex items-center gap-1.5 px-3 py-1 bg-[#F6F0E6] rounded-full text-xs font-mono font-bold text-[#1F5D42]">
              <span>{shop?.public_slug ? `${shop.public_slug}.qrlocal` : "sharmakirana.local"}</span>
              <button onClick={handleCopyLink} title={lang === "hi" ? "लिंक कॉपी करें" : "Copy link"} className="text-[#6d756f] hover:text-[#123324]">
                {copied ? <Check size={12} className="text-[#1F5D42]" /> : <Copy size={12} />}
              </button>
            </div>

            {/* Actions */}
            <div className="mt-4 flex flex-wrap gap-2 justify-center w-full">
              <a
                href={qrApiUrl}
                download={`${shop?.name || "shop"}-qr.svg`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#E8A33D] hover:bg-[#d6902b] text-[#123324] font-bold text-xs shadow-xs transition"
              >
                <Download size={13} />
                <span>{lang === "hi" ? "QR डाउनलोड करें" : "Download QR"}</span>
              </a>
              <button
                onClick={handlePrint}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#eee8dc] hover:bg-[#e4dcce] text-[#123324] font-bold text-xs shadow-xs transition"
              >
                <Printer size={13} />
                <span>{lang === "hi" ? "स्टिकर प्रिंट करें" : "Print sticker"}</span>
              </button>
              {shop?.public_slug && (
                <Link
                  href={`/shop/${shop.public_slug}`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#ddd6ca] text-xs font-semibold text-[#1F5D42] hover:bg-[#F6F0E6]"
                >
                  <ExternalLink size={13} />
                  <span>{lang === "hi" ? "दुकान खोलें" : "Open store"}</span>
                </Link>
              )}
            </div>
          </div>

          {/* Value Pitch & Quick Overview */}
          <div className="space-y-4">
            <div className="rounded-2xl bg-[#e7f2eb] border border-[#cbe1d5] p-5">
              <h3 className="font-display font-bold text-base text-[#123324]">
                {lang === "hi" ? "ग्राहक आपकी दुकान से कैसे ऑर्डर करते हैं" : "How Customers Order from Your Dukaan"}
              </h3>
              <ul className="mt-2 space-y-2 text-xs text-[#2b4c39]">
                <li className="flex items-start gap-2">
                  <span className="font-bold text-[#E8A33D]">1.</span>
                  <span>
                    {lang === "hi"
                      ? "ग्राहक अपने फ़ोन कैमरे से यह QR कोड स्कैन करता है — कोई ऐप डाउनलोड करने की ज़रूरत नहीं।"
                      : "Customer scans this QR code with their phone camera — no app to install."}
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-[#E8A33D]">2.</span>
                  <span>
                    {lang === "hi"
                      ? "वे हिंदी या अंग्रेजी में सामान चुनते हैं और अपना नाम व व्हाट्सएप नंबर दर्ज करते हैं।"
                      : "They pick items in English or Hindi and enter their name + WhatsApp number."}
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-[#E8A33D]">3.</span>
                  <span>
                    {lang === "hi"
                      ? "आपको तुरंत अपने आर्डर डेस्क और व्हाट्सएप पर अलर्ट मिलता है ताकि आप पैक और डिलीवर कर सकें।"
                      : "You receive the alert on your order desk & WhatsApp instantly to pack and deliver."}
                  </span>
                </li>
              </ul>
            </div>

            {/* Quick Metrics */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-[#ddd6ca] bg-white p-4">
                <span className="text-[11px] font-medium text-[#6d756f]">
                  {lang === "hi" ? "कुल बिक्री" : "Sales realized"}
                </span>
                <p className="font-display text-xl font-bold text-[#1F5D42] mt-1">
                  {money(data?.sales.realized_sales)}
                </p>
              </div>
              <div className="rounded-xl border border-[#ddd6ca] bg-white p-4">
                <span className="text-[11px] font-medium text-[#6d756f]">
                  {lang === "hi" ? "आज के ऑर्डर्स" : "Orders today"}
                </span>
                <p className="font-display text-xl font-bold text-[#123324] mt-1">
                  {data?.orders.total_orders ?? 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Orders Overview */}
      <div className="rounded-2xl border border-[#ddd6ca] bg-white overflow-hidden shadow-xs">
        <div className="flex items-center justify-between border-b border-[#eee9df] px-5 py-4 bg-[#faf8f3]">
          <div>
            <h3 className="font-display font-bold text-sm text-[#123324]">
              {lang === "hi" ? "हालिया नए ऑर्डर्स" : "Recent incoming orders"}
            </h3>
            <p className="text-[11px] text-[#6d756f]">
              {lang === "hi" ? "नए ग्राहक ऑर्डर्स जो पूर्ति के इंतज़ार में हैं" : "Live customer orders awaiting fulfillment"}
            </p>
          </div>
          <Link href="/merchant/orders" className="text-xs font-bold text-[#1F5D42] hover:underline flex items-center gap-1">
            <span>{lang === "hi" ? "ऑर्डर डेस्क पर जाएं" : "Go to Order Desk"}</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        {orders.data?.length ? (
          <div className="divide-y divide-[#eee9df]">
            {orders.data.slice(0, 4).map((order) => (
              <div key={order.id} className="flex items-center justify-between p-4 text-xs">
                <div>
                  <p className="font-bold text-[#123324]">
                    #{order.id} · {order.customer_name_snapshot || (lang === "hi" ? "ग्राहक" : "Customer")}
                  </p>
                  <p className="text-[11px] text-[#6d756f] mt-0.5">
                    {order.items.length} {lang === "hi" ? "सामान" : "items"} · {lang === "hi" ? (STATUS_HI[order.fulfillment_type] ?? order.fulfillment_type) : order.fulfillment_type}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-bold font-mono text-sm text-[#123324]">{money(order.total_amount)}</span>
                  <StatusPill status={order.status} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-[#6d756f]">{lang === "hi" ? "अभी तक कोई ऑर्डर नहीं। ऑर्डर पाने के लिए अपना QR कोड लगाएं!" : "No orders yet. Place your QR code to start receiving orders!"}</div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Visual Board Component 2: Overhauled Inventory Row
// -------------------------------------------------------------
function InventoryTickRow({
  item,
  product,
  onSave,
  onEditPrice,
  busy,
  lang = "en",
}: {
  item: InventoryItem;
  product?: Product;
  onSave: (action: "set-stock" | "add-stock" | "subtract-stock", quantity: string) => void;
  onEditPrice: () => void;
  busy: boolean;
  lang?: "en" | "hi";
}) {
  const isOutOfStock = item.is_out_of_stock || Number(item.available_quantity) <= 0;
  const effectiveImg = product?.effective_image || product?.image;

  const handleToggleStock = () => {
    if (isOutOfStock) {
      // Toggle back in stock with default 5
      onSave("set-stock", "5");
    } else {
      // Set to 0 available (out of stock)
      onSave("set-stock", "0");
    }
  };

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-4 hover:bg-[#faf8f3] transition">
      {/* Left: Stock Status Toggle, Image & Product Info */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {/* Prominent In Stock / Out of Stock pill button */}
        <button
          type="button"
          onClick={handleToggleStock}
          disabled={busy}
          title={isOutOfStock ? (lang === "hi" ? "स्टॉक में दिखाने के लिए क्लिक करें" : "Click to mark as In Stock") : (lang === "hi" ? "स्टॉक ख़त्म दिखाने के लिए क्लिक करें" : "Click to mark as Out of Stock")}
          className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition flex items-center gap-1 cursor-pointer shadow-2xs ${
            !isOutOfStock
              ? "bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5] hover:bg-[#d8ebd2]"
              : "bg-[#fde8de] text-[#9a4d2a] border border-[#f7cdbb] hover:bg-[#fbd0bf]"
          }`}
        >
          {!isOutOfStock ? (
            <>
              <Check size={12} strokeWidth={3} />
              <span>{lang === "hi" ? "स्टॉक में है" : "In Stock"}</span>
            </>
          ) : (
            <>
              <X size={12} strokeWidth={3} />
              <span>{lang === "hi" ? "स्टॉक ख़त्म" : "Out of Stock"}</span>
            </>
          )}
        </button>

        {/* Thumbnail */}
        {effectiveImg ? (
          <img
            src={effectiveImg}
            alt={item.product_name}
            className="w-10 h-10 object-cover rounded-xl border border-[#ddd6ca] shrink-0 bg-white"
          />
        ) : (
          <div className="w-10 h-10 rounded-xl bg-[#eee9df] flex items-center justify-center text-[#6d756f] shrink-0">
            <ShoppingBag size={16} />
          </div>
        )}

        {/* Name and Tags */}
        <div className="min-w-0">
          <p className={`text-xs font-bold leading-tight truncate ${!isOutOfStock ? "text-[#123324]" : "text-[#858c86] line-through"}`}>
            {item.product_name}
            {item.variant_name ? ` · ${item.variant_name}` : ""}
          </p>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            {product?.brand && (
              <span className="text-[10px] font-bold text-[#8a5b1d] bg-[#fff3db] px-2 py-0.5 rounded-full border border-[#f5deb5]">
                {product.brand}
              </span>
            )}
            {product?.category_name && (
              <span className="text-[10px] font-medium text-[#1F5D42] bg-[#e7f2eb] px-2 py-0.5 rounded-full border border-[#cbe1d5]">
                {product.category_name}
              </span>
            )}
            <span className="text-[10px] text-[#6d756f]">
              {item.sku ? `SKU: ${item.sku}` : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Center: Selling Price & MRP with Edit Button */}
      <div className="flex items-center gap-3 shrink-0 px-2 py-1 bg-[#fcfbfa] rounded-xl border border-[#eee9df]">
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xs font-medium text-[#6d756f]">
              {lang === "hi" ? "मूल्य:" : "Price:"}
            </span>
            <span className="font-mono font-bold text-sm text-[#123324]">
              {money(product?.price)}
            </span>
          </div>
          {product?.mrp && Number(product.mrp) > Number(product.price) && (
            <span className="block text-[10px] text-[#869088] line-through font-mono">
              MRP: {money(product.mrp)}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={onEditPrice}
          className="inline-flex items-center gap-1 text-[11px] font-bold text-[#1F5D42] hover:text-[#123324] bg-white hover:bg-[#e7f2eb] px-2.5 py-1 rounded-lg border border-[#cbe1d5] shadow-2xs transition cursor-pointer"
          title={lang === "hi" ? "विक्रय मूल्य व MRP सीधे बदलें" : "Edit Selling Price & MRP directly"}
        >
          <Edit3 size={11} />
          <span>{lang === "hi" ? "बदलें" : "Edit"}</span>
        </button>
      </div>

      {/* Right: Direct Inline Stepper (+ / -) */}
      <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
        <button
          type="button"
          disabled={busy || Number(item.available_quantity) <= 0}
          onClick={() => onSave("subtract-stock", "1")}
          className="w-8 h-8 rounded-xl bg-white border border-[#ddd6ca] text-[#123324] hover:bg-[#f6f0e6] font-bold text-base shadow-xs disabled:opacity-30 flex items-center justify-center cursor-pointer transition active:scale-95"
          title={lang === "hi" ? "स्टॉक 1 घटाएं" : "Decrease stock by 1"}
        >
          <Minus size={14} />
        </button>

        <div className="min-w-14 text-center">
          <span className="font-mono font-bold text-sm text-[#123324]">
            {item.available_quantity}
          </span>
          <span className="block text-[9px] text-[#6d756f] uppercase font-semibold">
            {lang === "hi" ? "मात्रा" : "units"}
          </span>
        </div>

        <button
          type="button"
          disabled={busy}
          onClick={() => onSave("add-stock", "1")}
          className="w-8 h-8 rounded-xl bg-[#1F5D42] text-white hover:bg-[#123324] font-bold text-base shadow-xs disabled:opacity-30 flex items-center justify-center cursor-pointer transition active:scale-95"
          title={lang === "hi" ? "स्टॉक 1 बढ़ाएं" : "Increase stock by 1"}
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}

function getMerchantWhatsAppUrl(
  order: MerchantOrder,
  mode: "status" | "bill" | "pack" | "out_for_delivery" | "delivered" = "status",
  lang: "en" | "hi" = "en"
): string {
  const cleanPhone = (order.customer_phone_snapshot || "").replace(/\D/g, "");
  const phoneWithCountry = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone;
  if (!phoneWithCountry) return "";

  const customerName = order.customer_name_snapshot || (lang === "hi" ? "ग्राहक" : "Customer");
  const shortId = `#SK-${order.id}`;
  const total = parseFloat(order.total_amount || "0").toFixed(0);

  if (mode === "bill") {
    const itemsLines = (order.items || []).map(
      (item) => `• ${item.product_name_snapshot}${item.variant_name_snapshot ? ` (${item.variant_name_snapshot})` : ""} × ${parseFloat(item.quantity || "1")} = ₹${parseFloat(item.line_total || "0").toFixed(0)}`
    ).join("\n");
    const addr = order.delivery_address;
    const addrText = addr ? [addr.address_line, addr.area, addr.city, addr.pincode].filter(Boolean).join(", ") : "";

    const billMsg = [
      lang === "hi" ? `🛍️ *ऑर्डर ${shortId} बिल सारांश*` : `🛍️ *Order ${shortId} Bill Summary*`,
      ``,
      lang === "hi"
        ? `नमस्ते ${customerName} जी! आपके ऑर्डर का पक्का बिल विवरण:`
        : `Namaste ${customerName}! Here is the bill for your order:`,
      ``,
      itemsLines,
      ``,
      order.delivery_charge_snapshot && parseFloat(order.delivery_charge_snapshot) > 0
        ? `${lang === "hi" ? "डिलीवरी शुल्क" : "Delivery Charge"}: ₹${parseFloat(order.delivery_charge_snapshot).toFixed(0)}`
        : null,
      `*${lang === "hi" ? "कुल देय राशि" : "Total Payable"}: ₹${total}* (${order.payment_status === "PAID" ? (lang === "hi" ? "ऑनलाइन भुगतान हो गया" : "PAID Online") : (lang === "hi" ? "भुगतान बाकी / डिलीवरी पर कैश" : "Payment Pending / Cash on Delivery")})`,
      order.fulfillment_type === "HOME_DELIVERY" && addrText ? `📍 ${lang === "hi" ? "डिलीवरी पता" : "Delivering to"}: ${addrText}` : null,
      ``,
      lang === "hi" ? `हमारी दुकान से ख़रीदारी के लिए धन्यवाद! 🙏` : `Thank you for ordering with us! 🙏`,
    ].filter(Boolean).join("\n");

    return `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(billMsg)}`;
  }

  if (mode === "pack") {
    const msg = lang === "hi"
      ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} (₹${total}) पैक हो गया है! 📦 जल्द ही आपको प्राप्त होगा।`
      : `Namaste ${customerName}! Your order ${shortId} for ₹${total} has been packed and is ready! 📦`;
    return `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(msg)}`;
  }

  if (mode === "out_for_delivery") {
    const isPickup = order.fulfillment_type === "PICKUP";
    const msg = isPickup
      ? lang === "hi"
        ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} तैयार है। कृपया दुकान पर आकर अपना सामान प्राप्त करें। कुल राशि: ₹${total}।`
        : `Namaste ${customerName}! Your order ${shortId} is ready for store pickup. Please visit us to collect! Total: ₹${total}.`
      : lang === "hi"
        ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} दुकान से निकल चुका है और आपके पते पर डिलीवरी के लिए रास्ते में है! 🛵 कुल राशि: ₹${total}।`
        : `Namaste ${customerName}! Your order ${shortId} is out for delivery to your address and will reach you shortly! 🛵 Total: ₹${total}.`;
    return `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(msg)}`;
  }

  if (mode === "delivered") {
    const msg = lang === "hi"
      ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} (कुल राशि: ₹${total}) डिलीवर/पूर्ण हो चुका है। हमारी दुकान से जुड़ने के लिए बहुत धन्यवाद! 🙏`
      : `Namaste ${customerName}! Your order ${shortId} (Total: ₹${total}) has been delivered. Thank you for shopping with us! 🙏`;
    return `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(msg)}`;
  }

  // General Status update message
  let statusMsg = "";
  switch (order.status) {
    case "PENDING":
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी! हमें आपका ऑर्डर ${shortId} (₹${total}) मिल गया है। स्टॉक चेक करके तुरंत पुष्टि कर रहे हैं!`
        : `Namaste ${customerName}! We have received your order ${shortId} for ₹${total}. Checking items on shelves and confirming shortly!`;
      break;
    case "ACCEPTED":
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} (₹${total}) स्वीकार कर लिया गया है और अब पैक किया जा रहा है! 📦`
        : `Namaste ${customerName}! Your order ${shortId} for ₹${total} has been accepted and is now being packed! 📦`;
      break;
    case "PREPARING":
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} तैयार किया जा रहा है। जल्द तैयार होगा!`
        : `Namaste ${customerName}! Your order ${shortId} is currently being packed. It will be ready soon!`;
      break;
    case "READY":
      const actionText = order.fulfillment_type === "PICKUP"
        ? (lang === "hi" ? "दुकान से पिकअप के लिए तैयार है।" : "ready for store pickup. Please visit us to collect!")
        : (lang === "hi" ? "डिलीवरी के लिए निकल चुका है।" : "out for delivery to your address!");
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} तैयार है और ${actionText} कुल राशि: ₹${total}।`
        : `Namaste ${customerName}! Your order ${shortId} is ready and ${actionText} Total: ₹${total}.`;
      break;
    case "COMPLETED":
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी! आपका ऑर्डर ${shortId} डिलीवर/पूर्ण हो चुका है। धन्यवाद! 🙏`
        : `Namaste ${customerName}! Your order ${shortId} has been completed/delivered. Thank you! 🙏`;
      break;
    case "REJECTED":
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी, किसी कारणवश हम आपका ऑर्डर ${shortId} स्वीकार नहीं कर पाए हैं। असुविधा के लिए खेद है!`
        : `Namaste ${customerName}, we are unable to accept order ${shortId} at this time. Sorry for the inconvenience!`;
      break;
    default:
      statusMsg = lang === "hi"
        ? `नमस्ते ${customerName} जी! आपके ऑर्डर ${shortId} के बारे में: कुल राशि ₹${total}।`
        : `Namaste ${customerName}! Regarding your order ${shortId}: Total ₹${total}.`;
  }

  return `https://wa.me/${phoneWithCountry}?text=${encodeURIComponent(statusMsg)}`;
}

// -------------------------------------------------------------
// Visual Board Component 3: Orders with Per-Item Resolve
// -------------------------------------------------------------
function VisualOrderCard({
  order,
  onAction,
  busy,
  onItemResolved,
  lang = "en",
}: {
  order: MerchantOrder;
  onAction: (action: string) => void;
  busy: boolean;
  onItemResolved: (itemName: string) => void;
  lang?: "en" | "hi";
}) {
  const [missingItem, setMissingItem] = useState<string | null>(null);

  const transitions: Record<string, Array<[string, string]>> = {
    PENDING: [
      ["accept", lang === "hi" ? "स्वीकार करें" : "Accept"],
      ["reject", lang === "hi" ? "अस्वीकार करें" : "Reject"],
    ],
    ACCEPTED: [["prepare", lang === "hi" ? "पैकिंग शुरू करें" : "Start packing"]],
    PREPARING: [["ready", lang === "hi" ? "पैक हो गया / तैयार" : "Packed / Done"]],
    READY: [["complete", order.fulfillment_type === "PICKUP" ? (lang === "hi" ? "दुकान से उठाया गया" : "Picked up from store") : (lang === "hi" ? "डिलीवरी रवाना / पूर्ण" : "Out for delivery / Complete")]],
  };

  const handleRemoveMissingItem = (itemName: string) => {
    setMissingItem(null);
    onItemResolved(itemName);
  };

  return (
    <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-5 shadow-xs space-y-4">
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#eee9df] pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-sm text-[#123324]">#{order.id}</span>
            <span className="text-xs font-bold text-[#123324]">· {order.customer_name_snapshot || (lang === "hi" ? "ग्राहक" : "Customer")}</span>
          </div>
          <p className="text-[11px] text-[#6d756f] mt-0.5">
            {dateTime(order.created_at, lang)} · {order.customer_phone_snapshot} ·{" "}
            <span className="font-semibold text-[#1F5D42]">{order.fulfillment_type === "PICKUP" ? (lang === "hi" ? "दुकान से पिकअप" : "Store Pickup") : (lang === "hi" ? "होम डिलीवरी" : "Home Delivery")}</span>
          </p>
          {order.fulfillment_type === "HOME_DELIVERY" && order.delivery_address && (
            <p className="text-[11px] text-[#5e665f] mt-1 bg-[#f7f3eb] px-2.5 py-1 rounded-lg border border-[#e8e2d5] inline-flex items-center gap-1.5">
              <span>📍</span>
              <span className="font-semibold text-[#123324]">
                {[order.delivery_address.address_line, order.delivery_address.area, order.delivery_address.city, order.delivery_address.pincode].filter(Boolean).join(", ")}
              </span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="font-display font-bold text-base text-[#1F5D42]">{money(order.total_amount)}</span>
          <StatusPill status={order.status} />
        </div>
      </div>

      {/* Items List */}
      <div className="space-y-2">
        {order.items.map((item) => {
          const isItemFlagged = missingItem === item.product_name_snapshot;
          return (
            <div key={item.id} className="flex items-center justify-between text-xs py-1.5 border-b border-[#f3eee5] last:border-0">
              <div className="flex-1 min-w-0 pr-3">
                <span className="font-semibold text-[#123324]">
                  {item.quantity} × {item.product_name_snapshot}
                </span>
                {item.variant_name_snapshot && <span className="text-[10px] text-[#7d857e]"> · {item.variant_name_snapshot}</span>}
                {isItemFlagged && (
                  <span className="ml-2 inline-block text-[9px] font-bold bg-[#fde8de] text-[#9a4d2a] px-2 py-0.5 rounded-full">
                    {lang === "hi" ? "इन्वेंट्री में नहीं / स्टॉक ख़त्म" : "Not in inventory / Out of stock"}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="font-mono text-[#123324]">{money(item.line_total)}</span>
                {/* Resolve Trigger if order is PENDING or ACCEPTED */}
                {(order.status === "PENDING" || order.status === "ACCEPTED") && !isItemFlagged && (
                  <button
                    onClick={() => setMissingItem(item.product_name_snapshot)}
                    className="text-[10px] text-[#9a4d2a] hover:underline"
                    title={lang === "hi" ? "सामान को उपलब्ध नहीं के रूप में चिह्नित करें" : "Flag item as missing"}
                  >
                    {lang === "hi" ? "उपलब्ध नहीं" : "Flag missing"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Visual Board Frame 3: Per-Item Resolve Missing Item Banner */}
      {missingItem && (
        <div className="rounded-xl border border-[#f7cdbb] bg-[#fdf2ec] p-3 text-xs">
          <p className="font-bold text-[#803f24] mb-1">{lang === "hi" ? "अनुपलब्ध सामान सुलझाएं:" : "Resolve missing item:"} {missingItem}</p>
          <p className="text-[11px] text-[#803f24]/80 mb-2">
            {lang === "hi"
              ? "बाकी ऑर्डर चालू रखने के लिए आप यह एक सामान हटा सकते हैं, या अभी इसे इन्वेंट्री में जोड़ सकते हैं।"
              : "You can remove this single item to keep the rest of the order moving, or add it to inventory now."}
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleRemoveMissingItem(missingItem)}
              className="px-3 py-1.5 rounded-lg bg-[#f7d7ca] hover:bg-[#f1c3b1] text-[#803f24] font-bold text-xs transition"
            >
              {lang === "hi" ? "यह सामान हटाएं और कुल रकम ठीक करें" : "Remove this item & adjust total"}
            </button>
            <button
              onClick={() => setMissingItem(null)}
              className="px-3 py-1.5 rounded-lg bg-[#1F5D42] hover:bg-[#123324] text-white font-bold text-xs transition"
            >
              {lang === "hi" ? "अभी मेरी इन्वेंट्री में जोड़ें" : "Add to my inventory now"}
            </button>
          </div>
        </div>
      )}

      {/* Action Transition & WhatsApp Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#eee9df]">
        <div className="flex flex-wrap items-center gap-2">
          {transitions[order.status]?.map(([action, label]) => (
            <button
              disabled={busy}
              key={action}
              onClick={() => onAction(action)}
              className={`rounded-xl px-4 py-2 text-xs font-bold shadow-xs disabled:opacity-50 transition ${
                action === "reject"
                  ? "border border-[#ecd9d3] bg-white text-[#9a5244] hover:bg-[#fff6f3]"
                  : action === "accept"
                  ? "bg-[#1F5D42] text-white hover:bg-[#123324]"
                  : "bg-[#E8A33D] text-[#123324] hover:bg-[#d6902b]"
              }`}
            >
              {label}
            </button>
          ))}
          {!transitions[order.status] && <span className="text-xs text-[#89958c]">{lang === "hi" ? `ऑर्डर ${STATUS_HI[order.status] ?? order.status.toLowerCase()}` : `Order ${order.status.toLowerCase()}`}</span>}
        </div>

        {/* 1-Click WhatsApp Actions for Merchant */}
        {order.customer_phone_snapshot && (
          <div className="flex flex-wrap items-center gap-1.5">
            <a
              href={getMerchantWhatsAppUrl(order, "status", lang)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#25D366] hover:bg-[#1fb858] text-white text-[11px] font-bold shadow-xs transition active:scale-[0.98]"
              title={lang === "hi" ? "ग्राहक को व्हाट्सएप पर मौजूदा स्थिति भेजें" : "Message customer on WhatsApp with current status"}
            >
              <MessageCircle className="w-3.5 h-3.5 fill-white" />
              <span>{lang === "hi" ? "व्हाट्सएप चैट" : "WhatsApp"}</span>
            </a>

            <a
              href={getMerchantWhatsAppUrl(order, "pack", lang)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-[#cde0d5] bg-[#f0f7f3] hover:bg-[#e2efe7] text-[#1F5D42] text-[11px] font-bold shadow-xs transition active:scale-[0.98]"
              title={lang === "hi" ? "पैक हो गया संदेश भेजें" : "Send Pack Ho Gaya notification"}
            >
              <span>{lang === "hi" ? "पैक हो गया 📦" : "Pack Done 📦"}</span>
            </a>

            <a
              href={getMerchantWhatsAppUrl(order, "out_for_delivery", lang)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-[#cde0d5] bg-[#f0f7f3] hover:bg-[#e2efe7] text-[#1F5D42] text-[11px] font-bold shadow-xs transition active:scale-[0.98]"
              title={order.fulfillment_type === "PICKUP" ? (lang === "hi" ? "पिकअप के लिए तैयार संदेश भेजें" : "Send Ready for Pickup notification") : (lang === "hi" ? "डिलीवरी रवाना संदेश भेजें" : "Send Out for Delivery notification")}
            >
              <span>{order.fulfillment_type === "PICKUP" ? (lang === "hi" ? "पिकअप तैयार 🛍️" : "Pickup Ready 🛍️") : (lang === "hi" ? "डिलीवरी रवाना 🛵" : "Out for Delivery 🛵")}</span>
            </a>

            <a
              href={getMerchantWhatsAppUrl(order, "bill", lang)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-[#cde0d5] bg-[#f0f7f3] hover:bg-[#e2efe7] text-[#1F5D42] text-[11px] font-bold shadow-xs transition active:scale-[0.98]"
              title={lang === "hi" ? "ग्राहक को व्हाट्सएप पर सामान सहित बिल भेजें" : "Share pre-filled itemized bill with customer on WhatsApp"}
            >
              <Receipt className="w-3 h-3" />
              <span>{lang === "hi" ? "पक्का बिल 🧾" : "Share Bill 🧾"}</span>
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Visual Board Component 4: Simple Analytics
// -------------------------------------------------------------
function VisualAnalyticsPanel({
  data,
  period = "today",
  lang = "en",
}: {
  data: Overview;
  period?: string;
  lang?: "en" | "hi";
}) {
  const topProducts = data.top_products || [];
  const maxUnits = topProducts.reduce((max, item) => Math.max(max, Number(item.units_sold) || 0), 0) || 1;

  const totalOrders = data.orders?.total_orders ?? 0;
  const completedOrders = data.orders?.completed_orders ?? 0;
  const rejectedOrders = data.orders?.rejected_orders ?? 0;
  const outOfStockCount = data.inventory?.out_of_stock_items_count ?? 0;
  const distribution = data.orders?.status_distribution || {
    PENDING: 0,
    ACCEPTED: 0,
    PREPARING: 0,
    READY: 0,
    COMPLETED: 0,
    REJECTED: 0,
  };

  const periodLabels: Record<string, { en: string; hi: string }> = {
    today: { en: "Today", hi: "आज" },
    yesterday: { en: "Yesterday", hi: "कल" },
    this_week: { en: "This Week", hi: "इस सप्ताह" },
    this_month: { en: "This Month", hi: "इस माह" },
  };
  const activePeriodLabel = (periodLabels[period] || periodLabels.today)[lang === "hi" ? "hi" : "en"];

  const lifecycleStages = [
    {
      key: "PENDING",
      label: lang === "hi" ? "स्वीकृति प्रतीक्षित" : "Pending Acceptance",
      count: distribution.PENDING ?? 0,
      color: "bg-amber-500",
      badge: "bg-amber-50 text-amber-800 border-amber-200",
    },
    {
      key: "ACCEPTED",
      label: lang === "hi" ? "स्वीकृत" : "Accepted in Queue",
      count: distribution.ACCEPTED ?? 0,
      color: "bg-sky-500",
      badge: "bg-sky-50 text-sky-800 border-sky-200",
    },
    {
      key: "PREPARING",
      label: lang === "hi" ? "पैकिंग जारी" : "Preparing",
      count: distribution.PREPARING ?? 0,
      color: "bg-indigo-500",
      badge: "bg-indigo-50 text-indigo-800 border-indigo-200",
    },
    {
      key: "READY",
      label: lang === "hi" ? "तैयार" : "Ready for Pickup",
      count: distribution.READY ?? 0,
      color: "bg-purple-500",
      badge: "bg-purple-50 text-purple-800 border-purple-200",
    },
    {
      key: "COMPLETED",
      label: lang === "hi" ? "पूर्ण व डिलीवर्ड" : "Completed",
      count: distribution.COMPLETED ?? 0,
      color: "bg-[#1F5D42]",
      badge: "bg-emerald-50 text-emerald-800 border-emerald-200",
    },
    {
      key: "REJECTED",
      label: lang === "hi" ? "अस्वीकृत / रद्द" : "Rejected",
      count: distribution.REJECTED ?? 0,
      color: "bg-rose-500",
      badge: "bg-rose-50 text-rose-800 border-rose-200",
    },
  ];

  return (
    <div className="space-y-6">
      {/* 4 Canonical Headline Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1: Realized Sales */}
        <Metric
          icon={IndianRupee}
          label={lang === "hi" ? `वसूल की गई बिक्री (${activePeriodLabel})` : `Realized Sales (${activePeriodLabel})`}
          value={money(data.sales?.realized_sales ?? 0)}
          note={
            lang === "hi"
              ? `औसत ऑर्डर मूल्य: ${money(data.sales?.average_order_value ?? 0)}`
              : `Avg order value: ${money(data.sales?.average_order_value ?? 0)}`
          }
          tint="green"
        />

        {/* Metric 2: Total Orders */}
        <Metric
          icon={ShoppingBag}
          label={lang === "hi" ? `कुल ऑर्डर्स (${activePeriodLabel})` : `Total Orders (${activePeriodLabel})`}
          value={totalOrders}
          note={
            lang === "hi"
              ? `${completedOrders} पूर्ण · ${rejectedOrders} रद्द/अस्वीकृत`
              : `${completedOrders} fulfilled · ${rejectedOrders} rejected`
          }
          tint="yellow"
        />

        {/* Metric 3: Customer Telemetry */}
        <Metric
          icon={UsersRound}
          label={lang === "hi" ? `सक्रिय खरीदार (${activePeriodLabel})` : `Ordering Customers (${activePeriodLabel})`}
          value={data.customers?.ordering_customers ?? 0}
          note={
            lang === "hi"
              ? `${data.customers?.returning_customers ?? 0} दोबारा खरीदार (≥2 ऑर्डर)`
              : `${data.customers?.returning_customers ?? 0} returning (≥2 orders)`
          }
          tint="blue"
        />

        {/* Metric 4: Inventory Health (Strictly zero/negative available stock) */}
        <Metric
          icon={AlertTriangle}
          label={lang === "hi" ? "स्टॉक-आउट अलर्ट" : "Stock-Out Alerts"}
          value={`${outOfStockCount} ${lang === "hi" ? "आइटम" : "SKUs"}`}
          note={
            outOfStockCount > 0
              ? (lang === "hi" ? "शून्य उपलब्ध मात्रा · नया स्टॉक जोड़ें" : "Zero available stock · Restock item")
              : (lang === "hi" ? "सभी स्टॉक स्तर धनात्मक हैं" : "All stock balances positive")
          }
          tint={outOfStockCount > 0 ? "rose" : "green"}
        />
      </div>

      {/* Order Fulfillment Pipeline (6 Canonical States) */}
      <div className="rounded-2xl border border-[#ddd6ca] bg-white p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#eee9df] gap-2">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-[#1F5D42]" />
            <h4 className="font-display font-bold text-sm text-[#123324]">
              {lang === "hi" ? "ऑर्डर जीवनचक्र पाइपलाइन" : "Order Lifecycle Pipeline"}
            </h4>
          </div>
          <span className="text-[11px] text-[#6d756f]">
            {lang === "hi"
              ? `कुल दर्ज ऑर्डर्स: ${totalOrders}`
              : `Total recorded orders: ${totalOrders}`}
          </span>
        </div>

        {/* Segmented Pipeline Bar */}
        <div className="mt-4 h-3 w-full rounded-full bg-[#f4f1ea] overflow-hidden flex">
          {totalOrders === 0 ? (
            <div className="h-full w-full bg-[#e8e4db]" />
          ) : (
            lifecycleStages.map((stage) => {
              if (stage.count === 0) return null;
              const widthPct = (stage.count / totalOrders) * 100;
              return (
                <div
                  key={stage.key}
                  className={`h-full ${stage.color} transition-all`}
                  style={{ width: `${widthPct}%` }}
                  title={`${stage.label}: ${stage.count} (${Math.round(widthPct)}%)`}
                />
              );
            })
          )}
        </div>

        {/* Stage Status Cards Grid */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {lifecycleStages.map((stage) => {
            const pct = totalOrders > 0 ? Math.round((stage.count / totalOrders) * 100) : 0;
            return (
              <div
                key={stage.key}
                className="p-3 rounded-xl border border-[#eee9df] bg-[#FFFDF8] flex flex-col justify-between"
              >
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${stage.color}`} />
                  <span className="text-[10px] font-bold text-[#6d756f] uppercase truncate" title={stage.label}>
                    {stage.label}
                  </span>
                </div>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="font-display font-bold text-lg text-[#123324]">{stage.count}</span>
                  <span className="text-[10px] font-mono text-[#8a968d]">{pct}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top-Selling Products Leaderboard (Units Sold & Realized Revenue) */}
      <div className="rounded-2xl border border-[#ddd6ca] bg-white p-5 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-[#eee9df]">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#E8A33D]" />
            <h4 className="font-display font-bold text-sm text-[#123324]">
              {lang === "hi" ? "शीर्ष बिकने वाले उत्पाद" : "Top-Selling Products (Completed Orders)"}
            </h4>
          </div>
          <span className="text-[11px] text-[#6d756f]">
            {lang === "hi" ? "इकाई बिक्री व वसूल राजस्व" : "Ranked by units sold & revenue contribution"}
          </span>
        </div>

        {topProducts.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#869088]">
            {lang === "hi"
              ? "इस अवधि के दौरान पूर्ण किए गए ऑर्डर्स का कोई बिक्री डेटा उपलब्ध नहीं है।"
              : "No completed order sales recorded for this period yet."}
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {topProducts.map((item, idx) => {
              const units = Number(item.units_sold) || 0;
              const widthPct = Math.round((units / maxUnits) * 100);
              return (
                <div
                  key={`${item.product_name}-${item.sku ?? idx}`}
                  className="p-3 rounded-xl border border-[#eee9df] bg-[#FFFDF8] flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-[#1F5D42]/40 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-5 text-center text-xs font-mono font-bold text-[#8a968d]">
                      #{idx + 1}
                    </span>
                    <div>
                      <p className="font-semibold text-xs text-[#123324]">{item.product_name}</p>
                      <p className="text-[10px] text-[#6d756f] mt-0.5">
                        {item.variant_name && <span>{item.variant_name} · </span>}
                        {item.sku ? <span className="font-mono">SKU: {item.sku}</span> : (lang === "hi" ? "सामान्य" : "Standard")}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 justify-between sm:justify-end">
                    <div className="w-24 sm:w-36">
                      <div className="h-2 rounded-full bg-[#eee9df] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-[#1F5D42] to-[#5f967a]"
                          style={{ width: `${Math.max(widthPct, 10)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-[#6d756f] mt-0.5 block">
                        {units} {lang === "hi" ? "इकाइयाँ बिकीं" : "units sold"}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="font-display font-bold text-xs text-[#1F5D42]">
                        {money(item.total_revenue)}
                      </span>
                      <span className="text-[10px] text-[#8a968d] block">
                        {lang === "hi" ? "राजस्व" : "Revenue"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Helper Modals & Rows
// -------------------------------------------------------------
function EditPriceModal({
  item,
  loading,
  error,
  lang = "en",
  onClose,
  onSave,
}: {
  item: { productId: number; name: string; price: string; mrp: string };
  loading: boolean;
  error: string | null;
  lang?: "en" | "hi";
  onClose: () => void;
  onSave: (price: string, mrp: string) => void;
}) {
  const [price, setPrice] = useState(item.price);
  const [mrp, setMrp] = useState(item.mrp);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!price || Number(price) <= 0) return;
    onSave(price, mrp);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
          <div>
            <h3 className="font-display font-bold text-base text-[#123324]">
              {lang === "hi" ? "विक्रय मूल्य व MRP बदलें" : "Edit Selling Price & MRP"}
            </h3>
            <p className="text-xs text-[#6d756f] mt-0.5 line-clamp-1">{item.name}</p>
          </div>
          <button type="button" onClick={onClose} aria-label={lang === "hi" ? "बंद करें" : "Close"} className="rounded-lg p-1 text-[#6d756f] hover:bg-[#eee9df]">
            <X size={16} />
          </button>
        </div>

        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-3 text-xs text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-3 text-xs">
          <div>
            <label className="block font-bold text-[#123324] mb-1">
              {lang === "hi" ? "दुकान का विक्रय मूल्य (₹) *" : "Shop Selling Price (₹) *"}
            </label>
            <input
              type="number"
              step="0.5"
              min="0.1"
              required
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              className="w-full h-10 rounded-xl border border-[#ddd6ca] px-3 font-mono text-sm outline-none focus:border-[#1F5D42]"
            />
            <p className="text-[11px] text-[#6d756f] mt-1">
              {lang === "hi" ? "इस मूल्य पर ग्राहक आपकी दुकान से ख़रीदेगा।" : "The actual price charged to customer at checkout."}
            </p>
          </div>

          <div>
            <label className="block font-bold text-[#123324] mb-1">
              {lang === "hi" ? "प्रिंटेड MRP (₹ - वैकल्पिक)" : "Printed MRP (₹ - Optional)"}
            </label>
            <input
              type="number"
              step="0.5"
              min="0.1"
              value={mrp}
              onChange={(e) => setMrp(e.target.value)}
              placeholder="0.00"
              className="w-full h-10 rounded-xl border border-[#ddd6ca] px-3 font-mono text-sm outline-none focus:border-[#1F5D42]"
            />
            <p className="text-[11px] text-[#6d756f] mt-1">
              {lang === "hi" ? "यदि विक्रय मूल्य MRP से कम है, तो ग्राहक को छूट दिखेगी।" : "If MRP > Selling Price, customers see a discount tag."}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-3 border-t border-[#eee9df]">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold text-[#6d756f] hover:bg-[#eee9df] rounded-xl transition"
          >
            {lang === "hi" ? "रद्द करें" : "Cancel"}
          </button>
          <button
            type="submit"
            disabled={loading || !price}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#1F5D42] text-white text-xs font-bold hover:bg-[#123324] disabled:opacity-60 transition"
          >
            {loading ? (
              <>
                <RefreshCw size={13} className="animate-spin" />
                <span>{lang === "hi" ? "अपडेट हो रहा है..." : "Saving..."}</span>
              </>
            ) : (
              <span>{lang === "hi" ? "मूल्य सुरक्षित करें" : "Update Price"}</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

function ProductRow({
  product,
  onToggle,
  onDelete,
  onViewDetail,
  lang = "en",
}: {
  product: Product;
  onToggle: () => void;
  onDelete: () => void;
  onViewDetail?: () => void;
  lang?: "en" | "hi";
}) {
  const effectiveImg = product.effective_image || product.image;
  return (
    <div className="grid grid-cols-[1.4fr_.7fr_.7fr_.6fr] items-center gap-3 border-b border-[#eee9df] px-5 py-4 last:border-0 text-xs">
      <div
        className="flex min-w-0 items-center gap-3 cursor-pointer group"
        onClick={onViewDetail}
      >
        {effectiveImg ? (
          <img
            src={effectiveImg}
            alt={product.name}
            className="w-9 h-9 object-cover rounded-xl border border-[#ddd6ca] shrink-0 bg-white group-hover:scale-105 transition"
          />
        ) : (
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#F6F0E6] text-[#1F5D42] group-hover:bg-[#e7f2eb] transition">
            <ShoppingBag size={16} />
          </span>
        )}
        <div className="min-w-0">
          <p className="truncate font-bold text-[#123324] group-hover:text-[#1F5D42] transition underline-offset-2 group-hover:underline">
            {product.name}
          </p>
          <p className="mt-0.5 truncate text-[10px] text-[#7d857e]">
            {product.brand || (lang === "hi" ? "स्थानीय" : "Local")}{product.sku ? ` · ${product.sku}` : ""}
          </p>
        </div>
      </div>
      <div>
        <span className="font-mono font-bold text-[#123324]">{money(product.price)}</span>
        {product.mrp && Number(product.mrp) > Number(product.price) && (
          <span className="block text-[10px] text-[#869088] line-through font-mono">
            {money(product.mrp)}
          </span>
        )}
      </div>
      <span className={`text-[10px] font-bold ${product.is_visible && product.is_available ? "text-[#1F5D42]" : "text-[#9a4d2a]"}`}>
        {!product.is_visible
          ? (lang === "hi" ? "छिपा हुआ" : "Hidden")
          : product.is_available
          ? (lang === "hi" ? "दुकान में दिखेगा" : "Visible")
          : (lang === "hi" ? "आउट ऑफ स्टॉक" : "Out of stock")}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={onToggle}
          className="rounded-lg bg-[#F6F0E6] px-2.5 py-1.5 text-[10px] font-bold text-[#1F5D42] hover:bg-[#eee9df] cursor-pointer"
        >
          {product.is_visible ? (lang === "hi" ? "छिपाएं" : "Hide") : (lang === "hi" ? "दिखाएं" : "Show")}
        </button>
        <button
          aria-label={lang === "hi" ? `${product.name} हटाएं` : `Delete ${product.name}`}
          onClick={onDelete}
          className="rounded-lg p-1.5 text-[#9a4d2a] hover:bg-[#ffece6] cursor-pointer"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

function ProductModal({
  onClose,
  onSave,
  saving,
  lang = "en",
}: {
  onClose: () => void;
  onSave: (payload: (Partial<Product> & { name: string }) | FormData) => void;
  saving: boolean;
  lang?: "en" | "hi";
}) {
  const { register, trigger, getValues, setValue, watch } = useForm<ProductInput, unknown, ProductValues>({
    resolver: zodResolver(productSchema),
    defaultValues: { name: "", price: 0, brand: "", sku: "", description: "", unit: "" },
  });
  const selectedUnit = watch("unit") || "";

  const [images, setImages] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const productInputRef = useRef<HTMLInputElement>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const incoming = Array.from(e.target.files);
    const combined = [...images, ...incoming].slice(0, 4); // enforce max 4 images
    setImages(combined);
    setPreviews(combined.map((f) => URL.createObjectURL(f)));
  };

  const removeImage = (index: number) => {
    const updated = images.filter((_, i) => i !== index);
    setImages(updated);
    setPreviews(updated.map((f) => URL.createObjectURL(f)));
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!(await trigger())) return;
    const values = getValues();
    if (images.length > 0) {
      const formData = new FormData();
      formData.append("name", values.name);
      formData.append("price", String(values.price));
      if (values.brand) formData.append("brand", values.brand);
      if (values.unit) formData.append("unit", values.unit);
      if (values.sku) formData.append("sku", values.sku);
      if (values.description) formData.append("description", values.description);
      formData.append("image", images[0]); // primary image
      onSave(formData);
    } else {
      onSave({ ...values, price: String(values.price), unit: values.unit });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <form onSubmit={submit} className="w-full max-w-[500px] rounded-2xl bg-white p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
          <h2 className="font-display font-bold text-base text-[#123324]">
            {lang === "hi" ? "नया प्रोडक्ट जोड़ें" : "Add New Product"}
          </h2>
          <button type="button" onClick={onClose} aria-label={lang === "hi" ? "बंद करें" : "Close"} className="rounded-lg p-1 text-[#6d756f] hover:bg-[#eee9df]">
            <X size={16} />
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 text-xs">
          <label className="sm:col-span-2">
            <span className="block font-bold text-[#123324] mb-1">
              {lang === "hi" ? "प्रोडक्ट का नाम *" : "Product Name *"}
            </span>
            <input {...register("name")} required className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
          </label>
          <label>
            <span className="block font-bold text-[#123324] mb-1">
              {lang === "hi" ? "विक्रय मूल्य (₹) *" : "Selling Price (₹) *"}
            </span>
            <input {...register("price", { valueAsNumber: true })} type="number" min="0" step="0.5" required className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
          </label>
          <label>
            <span className="block font-bold text-[#123324] mb-1">
              {lang === "hi" ? "ब्रांड (वैकल्पिक)" : "Brand (Optional)"}
            </span>
            <input {...register("brand")} className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
          </label>

          {/* Unit / Measurement Selector */}
          <div className="sm:col-span-2">
            <div className="flex items-center justify-between mb-1">
              <span className="block font-bold text-[#123324]">
                {lang === "hi" ? "इकाई / माप (खुला सामान या पैक्ड)" : "Unit / Measurement (Loose or Packaged)"}
              </span>
              {selectedUnit && (
                <button
                  type="button"
                  onClick={() => setValue("unit", "")}
                  className="text-[10px] text-red-600 hover:underline font-semibold"
                >
                  {lang === "hi" ? "इकाई हटाएं" : "Clear Unit"}
                </button>
              )}
            </div>
            <input
              {...register("unit")}
              placeholder={lang === "hi" ? "उदा. kg, g, liter, ml, piece, packet, 1 kg, 500g" : "e.g. kg, g, liter, ml, piece, packet, 1 kg, 500g"}
              className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42] text-xs mb-2"
            />
            <div className="space-y-1.5 bg-[#FAF8F3] p-2 rounded-xl border border-[#eee9df]">
              <div>
                <span className="text-[9px] font-bold text-[#1F5D42] uppercase tracking-wider block mb-1">
                  {lang === "hi" ? "खुला सामान" : "Loose Units"}
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  {["kg", "g", "liter", "ml", "piece", "packet", "dozen"].map((u) => (
                    <button
                      key={u}
                      type="button"
                      onClick={() => setValue("unit", selectedUnit === u ? "" : u)}
                      className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold border transition cursor-pointer ${
                        selectedUnit === u
                          ? "bg-[#1F5D42] text-white border-[#1F5D42] shadow-2xs"
                          : "bg-white hover:bg-[#e7f2eb] text-[#123324] border-[#ddd6ca]"
                      }`}
                    >
                      {u}
                    </button>
                  ))}
                </div>
              </div>
              <div className="pt-1.5 border-t border-[#eee9df]">
                <span className="text-[9px] font-bold text-[#6d756f] uppercase tracking-wider block mb-1">
                  {lang === "hi" ? "पैक्ड मात्रा" : "Packaged Quantities"}
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  {["1 kg", "500g", "250g", "100g", "1 liter", "500 ml", "1 piece", "1 packet"].map((u) => (
                    <button
                      key={u}
                      type="button"
                      onClick={() => setValue("unit", selectedUnit === u ? "" : u)}
                      className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold border transition cursor-pointer ${
                        selectedUnit === u
                          ? "bg-[#1F5D42] text-white border-[#1F5D42] shadow-2xs"
                          : "bg-white hover:bg-[#e7f2eb] text-[#123324] border-[#ddd6ca]"
                      }`}
                    >
                      {u}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Product Images (Max 4) */}
          <div className="sm:col-span-2">
            <div className="flex items-center justify-between mb-1.5">
              <span className="block font-bold text-[#123324]">
                {lang === "hi" ? "प्रोडक्ट की तस्वीरें (अधिकतम 4)" : "Product Photos (Max 4 images)"}
              </span>
              <span className="text-[10px] font-semibold text-[#6d756f]">
                {images.length}/4
              </span>
            </div>

            <div className="grid grid-cols-4 gap-2">
              {previews.map((src, idx) => (
                <div key={idx} className="relative aspect-square rounded-xl border border-[#ddd6ca] overflow-hidden bg-[#FAF8F3]">
                  <img src={src} alt={lang === "hi" ? `प्रोडक्ट फोटो ${idx + 1}` : `Product thumbnail ${idx + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
                    aria-label={lang === "hi" ? "फोटो हटाएं" : "Remove photo"}
                    className="absolute top-1 right-1 h-5 w-5 rounded-full bg-red-600 text-white flex items-center justify-center hover:bg-red-700 shadow-sm"
                  >
                    <X size={10} />
                  </button>
                  {idx === 0 && (
                    <span className="absolute bottom-1 left-1 text-[8px] bg-[#1F5D42] text-white px-1 py-0.5 rounded font-bold">
                      {lang === "hi" ? "मुख्य" : "Main"}
                    </span>
                  )}
                </div>
              ))}

              {images.length < 4 && (
                <button
                  type="button"
                  onClick={() => productInputRef.current?.click()}
                  className="aspect-square rounded-xl border-2 border-dashed border-[#c8c0b2] hover:border-[#1F5D42] bg-[#FAF8F3] hover:bg-[#e7f2eb]/40 flex flex-col items-center justify-center text-[#6d756f] hover:text-[#1F5D42] transition"
                >
                  <Upload size={16} />
                  <span className="text-[9px] font-bold mt-1">{lang === "hi" ? "जोड़ें" : "Upload"}</span>
                </button>
              )}
            </div>

            <input
              ref={productInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              multiple
              className="hidden"
              onChange={handleImageChange}
            />
            <span className="mt-1 block text-[10px] text-[#869088]">
              {lang === "hi" ? "पहली फोटो ग्राहक को मुख्य कैटलॉग में दिखेगी।" : "The first image will be the primary catalog display photo."}
            </span>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-3 border-t border-[#eee9df]">
          <button type="button" onClick={onClose} className="px-4 py-2 text-xs font-semibold text-[#6d756f]">
            {lang === "hi" ? "रद्द करें" : "Cancel"}
          </button>
          <button disabled={saving} className="px-4 py-2 rounded-xl bg-[#1F5D42] text-white text-xs font-bold hover:bg-[#123324] disabled:opacity-60">
            {saving ? (lang === "hi" ? "जोड़ा जा रहा है…" : "Adding…") : (lang === "hi" ? "कैटलॉग में जोड़ें" : "Add to Catalog")}
          </button>
        </div>
      </form>
    </div>
  );
}

function ShopSettings({
  shop,
  loading,
  error,
  refetch,
  onSaved,
  lang = "en",
}: {
  shop?: Shop;
  loading: boolean;
  error: unknown;
  refetch: () => void;
  onSaved: () => void;
  lang?: "en" | "hi";
}) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [saveError, setSaveError] = useState("");

  interface ShopPhotoSlot {
    id: string;
    url: string;
    file?: File;
    labelEn: string;
    labelHi: string;
  }

  const [photos, setPhotos] = useState<ShopPhotoSlot[]>([
    { id: "cover", url: shop?.logo ?? "", labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" },
  ]);
  const [initialPhotos, setInitialPhotos] = useState<ShopPhotoSlot[]>([
    { id: "cover", url: shop?.logo ?? "", labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" },
  ]);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const [activeSlotIdx, setActiveSlotIdx] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && shop?.public_slug) {
      try {
        const stored = localStorage.getItem(`dukaandar_shop_photos_${shop.public_slug}`);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            const slotsMeta = [
              { labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" },
              { labelEn: "Store Entrance / Board", labelHi: "बोर्ड / प्रवेश द्वार" },
              { labelEn: "Shelves & Products", labelHi: "सामान के रैक" },
              { labelEn: "Counter & Inside", labelHi: "बिलिंग काउंटर" },
            ];
            const restored = parsed
              .map((item: any, idx: number) => {
                const url = typeof item === "string" ? item : item?.url || "";
                const meta = slotsMeta[idx] || slotsMeta[0];
                return {
                  id: `photo-${idx}`,
                  url,
                  labelEn: meta.labelEn,
                  labelHi: meta.labelHi,
                };
              })
              .filter((p: ShopPhotoSlot) => Boolean(p.url));

            if (restored.length > 0) {
              setPhotos(restored);
              setInitialPhotos(restored);
              return;
            }
          }
        }
      } catch {
        // fallback
      }
    }
    if (shop?.logo && (!photos[0] || !photos[0].url)) {
      const initPhotos = [
        { id: "cover", url: shop.logo, labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" },
      ];
      setPhotos(initPhotos);
      setInitialPhotos(initPhotos);
    }
  }, [shop?.logo, shop?.public_slug]);

  const handlePhotosSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    if (activeSlotIdx !== null) {
      // Replacing a specific slot
      const file = files[0];
      const newUrl = URL.createObjectURL(file);
      setPhotos((prev) => {
        const next = [...prev];
        next[activeSlotIdx] = {
          ...next[activeSlotIdx],
          url: newUrl,
          file,
        };
        return next;
      });
      setActiveSlotIdx(null);
    } else {
      // Adding new photos up to 4 total
      const slots: { labelEn: string; labelHi: string }[] = [
        { labelEn: "Main Storefront", labelHi: "मुख्य दुकान" },
        { labelEn: "Store Entrance / Board", labelHi: "बोर्ड / प्रवेश द्वार" },
        { labelEn: "Shelves & Products", labelHi: "सामान के रैक" },
        { labelEn: "Counter & Inside", labelHi: "बिलिंग काउंटर" },
      ];

      setPhotos((prev) => {
        const remaining = 4 - prev.length;
        const toAdd = files.slice(0, remaining).map((f, i) => {
          const slotMeta = slots[prev.length + i] || slots[0];
          return {
            id: `photo-${Date.now()}-${i}`,
            url: URL.createObjectURL(f),
            file: f,
            labelEn: slotMeta.labelEn,
            labelHi: slotMeta.labelHi,
          };
        });
        return [...prev, ...toAdd];
      });
    }

    if (photoInputRef.current) {
      photoInputRef.current.value = "";
    }
  };

  const handleRemovePhoto = (idx: number) => {
    setPhotos((prev) => {
      const filtered = prev.filter((_, i) => i !== idx);
      return filtered.length === 0
        ? [{ id: "cover", url: "", labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" }]
        : filtered;
    });
  };

  const settingsValues = useMemo(
    () =>
      shop
        ? {
            name: shop.name,
            logo: shop.logo ?? "",
            description: shop.description ?? "",
            address_line: shop.address_line,
            area: shop.area,
            city: shop.city,
            state: shop.state,
            pincode: shop.pincode,
            google_maps_url: shop.google_maps_url ?? "",
            opening_time: shop.opening_time?.slice(0, 5) ?? "",
            closing_time: shop.closing_time?.slice(0, 5) ?? "",
            is_home_delivery_enabled: shop.is_home_delivery_enabled,
            is_pickup_enabled: shop.is_pickup_enabled,
            is_temporarily_closed: shop.is_temporarily_closed,
            delivery_fee_type: shop.delivery_fee_type,
            delivery_charge: Number(shop.delivery_charge),
            pending_order_timeout_minutes: shop.pending_order_timeout_minutes,
          }
        : undefined,
    [shop]
  );

  const { register, handleSubmit, setValue, reset, watch } = useForm<ShopSettingsInput, unknown, ShopSettingsValues>({
    resolver: zodResolver(shopSettingsSchema),
    values: settingsValues,
  });

  const watched = watch();

  // Determine if form inputs differ from initial values
  const formHasChanges = useMemo(() => {
    if (!settingsValues || !watched) return false;

    // Check string fields
    const stringKeys: (keyof ShopSettingsValues)[] = [
      "name",
      "description",
      "address_line",
      "area",
      "city",
      "state",
      "pincode",
      "google_maps_url",
      "opening_time",
      "closing_time",
      "delivery_fee_type",
    ];
    for (const key of stringKeys) {
      const current = (watched[key] ?? "").toString().trim();
      const initial = (settingsValues[key] ?? "").toString().trim();
      if (current !== initial) return true;
    }

    // Check boolean fields
    const boolKeys: (keyof ShopSettingsValues)[] = [
      "is_home_delivery_enabled",
      "is_pickup_enabled",
      "is_temporarily_closed",
    ];
    for (const key of boolKeys) {
      if (Boolean(watched[key]) !== Boolean(settingsValues[key])) return true;
    }

    // Check number fields
    const currentCharge = Number.isNaN(Number(watched.delivery_charge)) ? 0 : Number(watched.delivery_charge);
    const initialCharge = Number(settingsValues.delivery_charge ?? 0);
    if (currentCharge !== initialCharge) return true;

    return false;
  }, [watched, settingsValues]);

  // Determine if photo slots differ from initial state
  const photosHaveChanges = useMemo(() => {
    if (photos.some((p) => p.file)) return true;
    const currentUrls = photos.map((p) => p.url).filter(Boolean);
    const initUrls = initialPhotos.map((p) => p.url).filter(Boolean);
    if (currentUrls.length !== initUrls.length) return true;
    return currentUrls.some((url, idx) => url !== initUrls[idx]);
  }, [photos, initialPhotos]);

  const hasChanges = formHasChanges || photosHaveChanges;

  const handleDiscard = () => {
    if (settingsValues) {
      reset(settingsValues);
    }
    setPhotos(initialPhotos);
    setMessage("");
    setSaveError("");
  };

  if (loading) return <LoadingRows />;
  if (error || !shop) return <Notice error={error ?? new Error("Shop not found")} onRetry={refetch} />;

  const submit = async (values: ShopSettingsValues) => {
    setSaving(true);
    setMessage("");
    setSaveError("");
    try {
      const { logo, ...restValues } = values;
      const primaryPhoto = photos.find((p) => p.file || (p.url && p.url.trim() !== ""));
      if (primaryPhoto?.file) {
        const formData = new FormData();
        Object.entries(restValues).forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== "") {
            formData.append(k, String(v));
          }
        });
        formData.append("delivery_charge", String(values.delivery_charge));
        if (values.opening_time) formData.append("opening_time", values.opening_time);
        if (values.closing_time) formData.append("closing_time", values.closing_time);
        if (values.google_maps_url) formData.append("google_maps_url", values.google_maps_url);
        formData.append("logo", primaryPhoto.file);
        await merchantApi.updateShop(formData);
      } else {
        const isPhotoDeleted = !primaryPhoto;
        await merchantApi.updateShop({
          ...restValues,
          delete_logo: isPhotoDeleted ? true : undefined,
          opening_time: values.opening_time || null,
          closing_time: values.closing_time || null,
          delivery_charge: String(values.delivery_charge),
          google_maps_url: values.google_maps_url || "",
        });
      }
      if (typeof window !== "undefined" && shop?.public_slug) {
        const processedUrls: string[] = [];
        for (const p of photos) {
          if (p.file) {
            try {
              const base64 = await new Promise<string>((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result as string);
                reader.onerror = reject;
                reader.readAsDataURL(p.file!);
              });
              processedUrls.push(base64);
            } catch {
              if (p.url && p.url.trim() !== "") processedUrls.push(p.url);
            }
          } else if (p.url && p.url.trim() !== "") {
            processedUrls.push(p.url);
          }
        }
        if (processedUrls.length > 0) {
          localStorage.setItem(`dukaandar_shop_photos_${shop.public_slug}`, JSON.stringify(processedUrls));
        } else {
          localStorage.removeItem(`dukaandar_shop_photos_${shop.public_slug}`);
        }
      }
      setMessage(lang === "hi" ? "दुकान का विवरण सफलतापूर्वक सहेजा गया।" : "Shop details saved successfully.");
      setInitialPhotos(photos.map((p) => ({ ...p, file: undefined })));
      onSaved();
      refetch();
    } catch (e) {
      setSaveError(getApiError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Title
        eyebrow={lang === "hi" ? "आपकी दुकान" : "Your store"}
        title={lang === "hi" ? "दुकान सेटिंग्स" : "Shop settings"}
        description={lang === "hi" ? "दुकान की जानकारी, 4 तस्वीरें और डिलीवरी सेटिंग्स को अपडेट रखें।" : "Keep your storefront details, 4 shop photos, and delivery settings up to date."}
      />
      <form id="shop-settings-form" onSubmit={handleSubmit(submit)} className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-5 sm:p-7 shadow-xs relative">
        <div className="mb-6 flex flex-col gap-4 border-b border-[#eee9df] pb-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            {photos[0]?.url ? (
              <img src={photos[0].url} alt={shop.name} className="h-12 w-12 rounded-2xl object-cover border border-[#ddd6ca]" />
            ) : (
              <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#e7f2eb] text-[#1F5D42]">
                <Store size={22} />
              </span>
            )}
            <div>
              <h2 className="font-display font-bold text-base text-[#123324]">{shop.name}</h2>
              <p className="text-[11px] text-[#6d756f]">{shop.city}, {shop.state}</p>
            </div>
          </div>
          {/* Modern Dukaan Open / Closed Toggle Switch Card */}
          <div
            onClick={() => {
              setValue("is_temporarily_closed", !watched.is_temporarily_closed, {
                shouldDirty: true,
                shouldTouch: true,
                shouldValidate: true,
              });
            }}
            className={`flex items-center gap-3 p-3 rounded-2xl border transition cursor-pointer select-none shadow-xs ${
              !watched.is_temporarily_closed
                ? "bg-[#f0f8f4] border-[#a9d7be]"
                : "bg-[#fff5f2] border-[#f8c0b0]"
            }`}
          >
            <div className="text-right">
              <span
                className={`block text-xs font-bold ${
                  !watched.is_temporarily_closed ? "text-[#1F5D42]" : "text-[#c2410c]"
                }`}
              >
                {!watched.is_temporarily_closed
                  ? lang === "hi"
                    ? "दुकान खुली है"
                    : "Store is OPEN"
                  : lang === "hi"
                  ? "दुकान अस्थायी रूप से बंद है"
                  : "Store is CLOSED"}
              </span>
              <span className="text-[10px] text-[#6d756f]">
                {!watched.is_temporarily_closed
                  ? lang === "hi"
                    ? "ग्राहक नए ऑर्डर दे सकते हैं"
                    : "Accepting orders"
                  : lang === "hi"
                  ? "नए ऑर्डर्स रोक दिए गए हैं"
                  : "Orders paused"}
              </span>
            </div>

            {/* iOS style toggle switch button */}
            <div
              className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                !watched.is_temporarily_closed ? "bg-[#1F5D42]" : "bg-neutral-300"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                  !watched.is_temporarily_closed ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 text-xs">
          {([
            ["name", lang === "hi" ? "दुकान का नाम *" : "Shop name *"],
            ["address_line", lang === "hi" ? "पता *" : "Address *"],
            ["area", lang === "hi" ? "इलाका / क्षेत्र *" : "Area *"],
            ["city", lang === "hi" ? "शहर *" : "City *"],
            ["state", lang === "hi" ? "राज्य *" : "State *"],
            ["pincode", lang === "hi" ? "पिन कोड *" : "PIN code *"],
          ] as const).map(([key, label]) => (
            <label key={key}>
              <span className="mb-1 block font-bold text-[#123324]">{label}</span>
              <input {...register(key)} className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
            </label>
          ))}

          {/* Storefront Photos: Up to 4 Photos Gallery (Google Maps Place style) */}
          <div className="sm:col-span-2">
            <div className="flex items-center justify-between mb-1.5">
              <span className="block font-bold text-[#123324]">
                {lang === "hi" ? "दुकान की तस्वीरें (अधिकतम 4 तस्वीरें)" : "Shop Storefront Photos (Up to 4 Photos)"}
              </span>
              <span className="text-[11px] text-[#6d756f] font-mono">
                {photos.filter((p) => p.url).length}/4 {lang === "hi" ? "अपलोड की गई" : "uploaded"}
              </span>
            </div>
            <p className="text-[11px] text-[#6d756f] mb-3">
              {lang === "hi"
                ? "दुकान की मुख्य तस्वीरें अपलोड करें (जैसे दुकान का बोर्ड, मुख्य गेट, सामान के रैक और बिलिंग काउंटर)। ये तस्वीरें ग्राहक को स्टोरफ्रंट पर दिखेंगी।"
                : "Upload real shop photos (main storefront, board, shelves, billing counter). These will appear on your customer storefront gallery."}
            </p>

            <input
              ref={photoInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              multiple
              onChange={handlePhotosSelected}
            />

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[0, 1, 2, 3].map((idx) => {
                const photo = photos[idx];
                const hasPhoto = Boolean(photo && photo.url);
                const slotLabels = [
                  { en: "1. Main Storefront", hi: "1. मुख्य स्टोरफ्रंट" },
                  { en: "2. Entrance / Board", hi: "2. बोर्ड / प्रवेश द्वार" },
                  { en: "3. Shelves & Racks", hi: "3. रैक व सामान" },
                  { en: "4. Inside / Counter", hi: "4. काउंटर व अंदर" },
                ];
                const slotLabel = lang === "hi" ? slotLabels[idx].hi : slotLabels[idx].en;

                return (
                  <div
                    key={idx}
                    className="relative flex flex-col rounded-2xl border border-[#ddd6ca] bg-[#FAF8F3] overflow-hidden shadow-2xs group"
                  >
                    <div className="relative h-28 w-full bg-[#eee9df] flex items-center justify-center">
                      {hasPhoto ? (
                        <>
                          <img
                            src={photo.url}
                            alt={slotLabel}
                            className="h-full w-full object-cover"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemovePhoto(idx)}
                            className="absolute top-1.5 right-1.5 rounded-full bg-red-600/90 hover:bg-red-700 text-white p-1 shadow-sm transition"
                            title={lang === "hi" ? "फोटो हटाएं" : "Remove photo"}
                          >
                            <Trash2 size={12} />
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setActiveSlotIdx(idx);
                            photoInputRef.current?.click();
                          }}
                          className="h-full w-full flex flex-col items-center justify-center gap-1.5 p-2 text-[#7d857e] hover:bg-[#e7f2eb]/60 hover:text-[#1F5D42] transition border-2 border-dashed border-[#c8c0b2] rounded-2xl m-1"
                        >
                          <Upload size={16} />
                          <span className="text-[10px] font-bold">
                            {lang === "hi" ? "+ फोटो जोड़ें" : "+ Add Photo"}
                          </span>
                        </button>
                      )}
                    </div>
                    <div className="p-2 bg-white border-t border-[#eee9df] text-center">
                      <p className="text-[10px] font-semibold text-[#123324] truncate">{slotLabel}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Google Maps Location Link */}
          <label className="sm:col-span-2">
            <span className="mb-1 block font-bold text-[#123324]">
              {lang === "hi" ? "गूगल मैप्स लोकेशन लिंक (वैकल्पिक)" : "Google Maps Location Link (Optional)"}
            </span>
            <input
              {...register("google_maps_url")}
              type="url"
              placeholder="https://maps.google.com/?q=..."
              className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]"
            />
            <span className="mt-1 block text-[10px] text-[#869088]">
              {lang === "hi"
                ? "ग्राहक आपकी दुकान के पते पर क्लिक करके सीधे गूगल मैप्स पर दिशा-निर्देश प्राप्त कर सकेंगे।"
                : "Customers can click your shop address on the storefront to open turn-by-turn directions on Google Maps."}
            </span>
          </label>

          {/* Description */}
          <label className="sm:col-span-2">
            <span className="mb-1 block font-bold text-[#123324]">
              {lang === "hi" ? "दुकान के बारे में / विवरण" : "About / Description"}
            </span>
            <textarea
              {...register("description")}
              rows={2}
              placeholder={lang === "hi" ? "ग्राहकों को अपनी दुकान के बारे में बताएं..." : "Tell customers about your shop..."}
              className="w-full rounded-xl border border-[#ddd6ca] p-3 outline-none focus:border-[#1F5D42]"
            />
          </label>
        </div>

        {/* Store Schedule & Timings (Matching Screenshot) */}
        <div className="mt-6 border-t border-[#eee9df] pt-5">
          <h3 className="font-display font-bold text-sm text-[#123324] mb-3 flex items-center gap-2">
            <Clock3 size={16} className="text-[#1F5D42]" />
            <span>{lang === "hi" ? "दुकान का समय व दैनिक शेड्यूल" : "Store Schedule & Daily Timings"}</span>
          </h3>
          <div className="grid gap-4 sm:grid-cols-2 text-xs">
            <label>
              <span className="mb-1 block font-bold text-[#123324]">
                {lang === "hi" ? "दुकान खुलने का समय" : "Opening Time (e.g. 07:00 AM)"}
              </span>
              <input
                {...register("opening_time")}
                type="time"
                className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42] bg-white font-mono"
              />
            </label>
            <label>
              <span className="mb-1 block font-bold text-[#123324]">
                {lang === "hi" ? "दुकान बंद होने का समय" : "Closing Time (e.g. 11:00 PM)"}
              </span>
              <input
                {...register("closing_time")}
                type="time"
                className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42] bg-white font-mono"
              />
            </label>
            <div className="sm:col-span-2 flex flex-wrap items-center gap-2 pt-1">
              <span className="text-[11px] text-[#6d756f] font-medium mr-1">
                {lang === "hi" ? "जल्दी चुनें:" : "Quick Presets:"}
              </span>
              <button
                type="button"
                onClick={() => {
                  setValue("opening_time", "07:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                  setValue("closing_time", "23:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                {lang === "hi" ? "सुबह 7:00 – रात 11:00" : "7:00 AM – 11:00 PM"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setValue("opening_time", "08:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                  setValue("closing_time", "22:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                {lang === "hi" ? "सुबह 8:00 – रात 10:00" : "8:00 AM – 10:00 PM"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setValue("opening_time", "09:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                  setValue("closing_time", "21:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                {lang === "hi" ? "सुबह 9:00 – रात 9:00" : "9:00 AM – 9:00 PM"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setValue("opening_time", "00:00", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                  setValue("closing_time", "23:59", { shouldDirty: true, shouldTouch: true, shouldValidate: true });
                }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                {lang === "hi" ? "24 घंटे खुली (24x7)" : "24 Hours Open (24x7)"}
              </button>
            </div>
          </div>
        </div>

        {/* Delivery & Fulfillment Preferences */}
        <div className="mt-6 border-t border-[#eee9df] pt-5">
          <h3 className="font-display font-bold text-sm text-[#123324] mb-3">
            {lang === "hi" ? "डिलीवरी एवं ऑर्डर पूर्ति सेटिंग्स" : "Delivery & Order Fulfillment"}
          </h3>
          <div className="grid gap-4 sm:grid-cols-2 text-xs">
            <label>
              <span className="mb-1 block font-bold text-[#123324]">
                {lang === "hi" ? "डिलीवरी शुल्क (₹)" : "Delivery Charge (₹)"}
              </span>
              <input
                {...register("delivery_charge", { valueAsNumber: true })}
                type="number"
                min="0"
                step="1"
                placeholder="0"
                className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]"
              />
              <span className="mt-1 block text-[10px] text-[#869088]">
                {lang === "hi"
                  ? "0 = मुफ्त डिलीवरी। कोई राशि डालने पर वह ग्राहक के ऑर्डर बिल में जुड़ेगी।"
                  : "0 = Free Delivery. Any amount set will be added to customer's order total."}
              </span>
            </label>

            <label>
              <span className="mb-1 block font-bold text-[#123324]">
                {lang === "hi" ? "डिलीवरी शुल्क प्रकार" : "Delivery Fee Mode"}
              </span>
              <select
                {...register("delivery_fee_type")}
                className="h-9 w-full rounded-xl border border-[#ddd6ca] bg-white px-3 outline-none focus:border-[#1F5D42]"
              >
                <option value="FIXED">{lang === "hi" ? "निर्धारित शुल्क" : "Fixed Amount"}</option>
                <option value="CONFIRMED_ON_WHATSAPP">{lang === "hi" ? "व्हाट्सएप पर पुष्टि" : "Confirm on WhatsApp"}</option>
              </select>
            </label>

            <div className="sm:col-span-2 flex flex-wrap gap-5 pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input {...register("is_home_delivery_enabled")} type="checkbox" className="accent-[#1F5D42]" />
                <span className="font-semibold text-[#123324]">
                  {lang === "hi" ? "होम डिलीवरी उपलब्ध है" : "Home Delivery Allowed"}
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input {...register("is_pickup_enabled")} type="checkbox" className="accent-[#1F5D42]" />
                <span className="font-semibold text-[#123324]">
                  {lang === "hi" ? "दुकान से पिकअप उपलब्ध है" : "Store Pickup Allowed"}
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* In-form Status / Feedback */}
        <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-[#eee9df] pt-4">
          <div className="flex items-center gap-2 text-xs text-[#6d756f]">
            <CheckCircle2 size={15} className={hasChanges ? "text-[#E8A33D]" : "text-[#1F5D42]"} />
            <span>
              {hasChanges
                ? lang === "hi"
                  ? "अनसेव्ड बदलाव मौजूद हैं — नीचे दिए गए फ्लोटिंग बार से सहेजें।"
                  : "You have unsaved changes — use the floating bar below to save."
                : lang === "hi"
                ? "सभी दुकान सेटिंग्स लाइव स्टोरफ्रंट पर अपडेटेड हैं।"
                : "All storefront details are up to date."}
            </span>
          </div>
          <p className="text-[11px] text-[#869088]">
            {hasChanges
              ? lang === "hi"
                ? "बदलाव पूर्ववत करने पर बार स्वतः हट जाएगा।"
                : "Undoing your changes will dismiss the save bar."
              : lang === "hi"
              ? "कोई भी बदलाव करने पर सहेजने का विकल्प स्वतः स्क्रीन के नीचे प्रकट होगा।"
              : "Modifying any setting above will pop up the save bar."}
          </p>
        </div>
        {saveError && (
          <div className="mt-3 rounded-xl bg-red-50 border border-red-200 p-3 text-xs text-red-700">
            {saveError}
          </div>
        )}
        {message && (
          <div className="mt-3 rounded-xl bg-[#e7f2eb] border border-[#cbe1d5] p-3 text-xs text-[#1F5D42] flex items-center gap-2">
            <CheckCircle2 size={15} className="text-[#1F5D42] shrink-0" />
            <span>{message}</span>
          </div>
        )}
      </form>

      {/* Floating Action Bar: Pops up whenever changes are made, goes back when undone */}
      <div
        className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-xl transition-all duration-300 ease-out ${
          hasChanges
            ? "translate-y-0 opacity-100 pointer-events-auto"
            : "translate-y-20 opacity-0 pointer-events-none"
        }`}
      >
        <div className="flex items-center justify-between gap-3 rounded-2xl border border-[#1F5D42]/40 bg-[#123324] px-4 py-3 sm:px-5 sm:py-3.5 text-white backdrop-blur-md shadow-2xl">
          <div className="flex items-center gap-3 min-w-0">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#E8A33D] text-[#123324] font-bold shadow-xs">
              <Sparkles size={17} />
            </span>
            <div className="min-w-0">
              <p className="font-display text-xs sm:text-sm font-bold text-white truncate">
                {lang === "hi" ? "दुकान में अनसेव्ड बदलाव हैं" : "Unsaved shop changes"}
              </p>
              <p className="text-[11px] text-[#b9cac0] truncate">
                {lang === "hi"
                  ? "लाइव स्टोरफ्रंट पर अपडेट करने के लिए सहेजें"
                  : "Save to update your live storefront"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleDiscard}
              disabled={saving}
              className="rounded-xl border border-white/20 bg-white/10 px-3.5 py-2 text-xs font-semibold text-[#dce6df] hover:bg-white/20 hover:text-white transition active:scale-95 disabled:opacity-50 cursor-pointer"
            >
              {lang === "hi" ? "रद्द करें" : "Discard"}
            </button>

            <button
              type="button"
              onClick={() => {
                const form = document.getElementById("shop-settings-form") as HTMLFormElement | null;
                if (form) form.requestSubmit();
              }}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-xl bg-[#1F5D42] hover:bg-[#164732] px-4 py-2 text-xs font-bold text-white shadow-xs transition active:scale-95 disabled:opacity-50 border border-[#2a684c] cursor-pointer"
            >
              {saving ? (
                <>
                  <RefreshCw size={13} className="animate-spin" />
                  <span>{lang === "hi" ? "सहेजा जा रहा है…" : "Saving…"}</span>
                </>
              ) : (
                <>
                  <Check size={14} className="text-[#E8A33D]" />
                  <span>{lang === "hi" ? "बदलाव सहेजें" : "Save changes"}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function PeriodSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const lang = useLang();
  return (
    <label className="flex h-10 items-center gap-2 rounded-xl border border-[#ddd6ca] bg-white px-3 text-xs text-[#5e665f]">
      <Clock3 size={14} />
      <select value={value} onChange={(e) => onChange(e.target.value)} className="bg-transparent font-bold outline-none">
        <option value="today">{lang === "hi" ? "आज" : "Today"}</option>
        <option value="yesterday">{lang === "hi" ? "कल" : "Yesterday"}</option>
        <option value="this_week">{lang === "hi" ? "इस सप्ताह" : "This week"}</option>
        <option value="this_month">{lang === "hi" ? "इस माह" : "This month"}</option>
      </select>
    </label>
  );
}

function Empty({ icon: Icon, title, text }: { icon: typeof Activity; title: string; text: string }) {
  return (
    <div className="px-6 py-12 text-center">
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-[#F6F0E6] text-[#1F5D42]">
        <Icon size={22} />
      </span>
      <h3 className="font-display font-bold mt-3 text-sm text-[#123324]">{title}</h3>
      <p className="mx-auto mt-1 max-w-sm text-xs text-[#6d756f]">{text}</p>
    </div>
  );
}

function Toast({ text, onClose }: { text: string; onClose: () => void }) {
  const lang = useLang();
  return (
    <div role="status" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-3 rounded-xl bg-[#123324] px-4 py-3 text-xs text-white shadow-xl">
      <Check size={15} className="text-[#E8A33D]" />
      <span>{text}</span>
      <button onClick={onClose} aria-label={lang === "hi" ? "बंद करें" : "Dismiss"} className="ml-2 text-white/70 hover:text-white">
        <X size={14} />
      </button>
    </div>
  );
}
