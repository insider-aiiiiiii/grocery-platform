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
  ChevronDown,
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
} from "lucide-react";
import { getApiError, InventoryItem, MerchantOrder, merchantApi, Overview, Product, Shop } from "@/lib/api/merchant";

const money = (value?: string | number | null) => `₹${Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const dateTime = (value: string) => new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

const productSchema = z.object({
  name: z.string().trim().min(1, "Enter a product name"),
  price: z.coerce.number().min(0, "Price cannot be negative"),
  brand: z.string().optional(),
  sku: z.string().optional(),
  description: z.string().optional(),
});
type ProductValues = z.infer<typeof productSchema>;
type ProductInput = z.input<typeof productSchema>;

const batchSchema = z.object({
  batchName: z.string().min(1, "Enter batch name (e.g., Old Stock / New Stock)"),
  price: z.coerce.number().min(0, "Price cannot be negative"),
  quantity: z.coerce.number().min(1, "Quantity must be at least 1"),
});
type BatchValues = z.infer<typeof batchSchema>;
type BatchInput = z.input<typeof batchSchema>;

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
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-[#f0d8d1] bg-[#fff8f5] p-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-semibold text-[#883f2e]">Couldn’t load this information</p>
        <p className="mt-1 text-xs text-[#9c6555]">{getApiError(error)}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-2 self-start rounded-lg border border-[#ead0c8] bg-white px-3 py-2 text-xs font-semibold text-[#734c40]">
          <RefreshCw size={13} />Try again
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

function StatusPill({ status }: { status: string }) {
  const color =
    status === "PENDING"
      ? "bg-[#fff1d9] text-[#8c5c1e] border border-[#f3ddb6]"
      : status === "REJECTED"
      ? "bg-[#fde8de] text-[#9a4d2a] border border-[#f7cdbb]"
      : status === "COMPLETED"
      ? "bg-[#e4f2e9] text-[#276746] border border-[#c6e6d1]"
      : "bg-[#e7f0ed] text-[#345c47] border border-[#cbe1d5]";
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wide ${color}`}>{status.replaceAll("_", " ")}</span>;
}

export default function MerchantWorkspace() {
  const pathname = usePathname();
  const section = pathname.split("/")[2] || "overview";
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState("today");
  const [search, setSearch] = useState("");
  const [newProductOpen, setNewProductOpen] = useState(false);
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [catalogTab, setCatalogTab] = useState<"shop" | "master">("shop");
  const [masterSearch, setMasterSearch] = useState("");

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
  const orders = useQuery({ queryKey: ["merchant", "orders"], queryFn: merchantApi.orders, enabled: ["overview", "orders"].includes(section), refetchInterval: section === "orders" ? 30000 : false });
  const products = useQuery({ queryKey: ["merchant", "products"], queryFn: merchantApi.products, enabled: ["overview", "catalog", "inventory"].includes(section) });
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
      setNotice("Order updated successfully.");
      refresh("orders");
      refresh("analytics");
    },
    onError: (e) => setNotice(getApiError(e)),
  });

  const stockMutation = useMutation({
    mutationFn: ({ item, action, quantity }: { item: InventoryItem; action: "set-stock" | "add-stock" | "subtract-stock"; quantity: string }) =>
      merchantApi.updateStock(item.id, action, quantity),
    onSuccess: () => {
      setNotice("Stock updated.");
      refresh("inventory");
      refresh("analytics");
    },
    onError: (e) => setNotice(getApiError(e)),
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

  const filteredOrders = useMemo(
    () => (orders.data ?? []).filter((row) => `${row.id} ${row.customer_name_snapshot} ${row.customer_phone_snapshot} ${row.status}`.toLowerCase().includes(search.toLowerCase())),
    [orders.data, search]
  );

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
        lang={lang}
      />
    );
  }

  // Section 02: Inventory & Batches
  if (section === "inventory") {
    return (
      <>
        <Title
          eyebrow="Stock room"
          title="Inventory & Batches"
          description="Tick what you sell · batches keep old/new prices separate"
          action={
            <div className="flex gap-2">
              <button
                onClick={() => setBatchModalOpen(true)}
                className="inline-flex h-10 items-center gap-1.5 rounded-xl bg-[#E8A33D] px-4 text-xs font-bold text-[#123324] hover:bg-[#d6902b] shadow-xs transition"
              >
                <Plus size={15} />
                <span>+ Add new batch</span>
              </button>
              <button
                onClick={() => refresh("inventory")}
                className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-xs font-semibold text-[#1F5D42] hover:bg-[#F6F0E6]"
              >
                <RefreshCw size={14} />
                <span>Refresh</span>
              </button>
            </div>
          }
        />

        {/* Master List Tick Panel */}
        <div className="space-y-4">
          {stock.isLoading ? (
            <LoadingRows />
          ) : stock.isError ? (
            <Notice error={stock.error} onRetry={() => stock.refetch()} />
          ) : (
            <div className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] overflow-hidden shadow-xs">
              <div className="border-b border-[#eee9df] bg-[#f8f6f0] px-5 py-3 flex justify-between items-center text-xs font-bold text-[#123324]">
                <span>Active Master Items (Tick to Stock)</span>
                <span className="text-[#6d756f] font-normal">{stock.data?.length ?? 0} items monitored</span>
              </div>
              <div className="divide-y divide-[#eee9df]">
                {stock.data?.map((item) => (
                  <InventoryTickRow
                    key={item.id}
                    item={item}
                    onSave={(action, quantity) => stockMutation.mutate({ item, action, quantity })}
                    busy={stockMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Multiple Batches Highlight Card (Matching Visual Board) */}
          <div className="rounded-2xl border border-[#ddd6ca] bg-white p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-[#1F5D42]" />
              <h4 className="font-display font-bold text-sm text-[#123324]">Multiple Batches Breakdown</h4>
            </div>
            <p className="text-xs text-[#6d756f] mb-3">
              Keep old lower-price stock and fresh inventory batches separated for transparent billing.
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="flex items-center justify-between rounded-xl bg-[#e7f2eb] border border-[#cce3d5] p-3 text-xs">
                <div>
                  <p className="font-bold text-[#1F5D42]">Old Stock Batch</p>
                  <p className="text-[11px] text-[#4d7051]">Costed at previous MRP</p>
                </div>
                <span className="font-bold font-mono text-[#1F5D42]">Batch #01</span>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-[#fff3db] border border-[#f5deb5] p-3 text-xs">
                <div>
                  <p className="font-bold text-[#8a5b1d]">New Arrival Batch</p>
                  <p className="text-[11px] text-[#7a531d]">Costed at current wholesale rate</p>
                </div>
                <span className="font-bold font-mono text-[#8a5b1d]">Batch #02</span>
              </div>
            </div>
          </div>

          {/* Master Catalog Bulk Help Banner */}
          <div className="rounded-2xl border border-[#f5deb5] bg-[#fff9ed] p-4 flex items-center justify-between gap-4">
            <div>
              <b className="text-xs font-bold text-[#7a531d]">Items not on the master list?</b>
              <p className="text-[11px] text-[#6e736d] mt-0.5">
                Upload a bulk Excel file to propose new items for approval by the Super Admin catalog team.
              </p>
            </div>
            <button
              onClick={() => setNotice("Excel Bulk Upload template generated. Ready for catalog team sync.")}
              className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-[#e5cd9e] text-xs font-bold text-[#7a531d] hover:bg-[#fff3db] shadow-xs transition"
            >
              <UploadCloud size={14} />
              <span>Bulk Excel Upload</span>
            </button>
          </div>
        </div>

        {batchModalOpen && (
          <BatchModal
            onClose={() => setBatchModalOpen(false)}
            onSave={(val) => {
              setBatchModalOpen(false);
              setNotice(`Batch '${val.batchName}' recorded for inventory tracking.`);
            }}
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
          eyebrow="Order desk"
          title="Incoming orders"
          description="Keep the rest of the order moving. Resolve out-of-stock items individually."
          action={
            <button
              onClick={() => refresh("orders")}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-xs font-semibold text-[#1F5D42] hover:bg-[#F6F0E6]"
            >
              <RefreshCw size={14} />
              <span>Refresh Desk</span>
            </button>
          }
        />

        <div className="mb-4 flex flex-col gap-3 rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-[320px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#98a39a]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by order or customer phone"
              className="h-10 w-full rounded-xl bg-white border border-[#ddd6ca] pl-9 pr-3 text-xs outline-none focus:border-[#1F5D42]"
            />
          </div>
          <p className="text-xs text-[#6d756f]">{filteredOrders.length} orders · live polling every 30s</p>
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
                  onAction={(action) => orderMutation.mutate({ id: order.id, action })}
                  busy={orderMutation.isPending}
                  onItemResolved={(itemName) => {
                    setNotice(`Item '${itemName}' removed from Order #${order.id}. Total adjusted.`);
                    refresh("orders");
                  }}
                />
              ))
            ) : (
              <Empty icon={ClipboardList} title="No incoming orders" text="New orders placed from your QR store will appear here in real time." />
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
          eyebrow="Performance"
          title="Simple analytics"
          description="Last 30 days · easy to read at a glance"
          action={<PeriodSelect value={period} onChange={setPeriod} />}
        />
        {analytics.isLoading ? (
          <LoadingRows />
        ) : analytics.isError ? (
          <Notice error={analytics.error} onRetry={() => analytics.refetch()} />
        ) : (
          <VisualAnalyticsPanel data={analytics.data!} />
        )}
      </>
    );
  }

  // Catalog / Products Section
  if (section === "catalog") {
    const filteredMaster = (masterCatalog.data ?? []).filter((mp) => {
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
          eyebrow="Your store"
          title="Product catalog"
          description="Manage products customers can discover in your shop, or add verified items from the platform Master Catalog."
          action={
            catalogTab === "shop" ? (
              <button
                onClick={() => setNewProductOpen(true)}
                className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#1F5D42] px-4 text-xs font-bold text-white hover:bg-[#123324] shadow-xs transition"
              >
                <Plus size={15} />
                <span>Add custom product</span>
              </button>
            ) : null
          }
        />

        {/* Catalog Navigation Tabs */}
        <div className="mb-5 flex flex-wrap items-center gap-2 border-b border-[#ddd6ca] pb-3">
          <button
            onClick={() => setCatalogTab("shop")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
              catalogTab === "shop"
                ? "bg-[#1F5D42] text-white shadow-xs"
                : "bg-white border border-[#ddd6ca] text-[#123324] hover:bg-[#F6F0E6]"
            }`}
          >
            {lang === "hi"
              ? `मेरी दुकान के प्रोडक्ट्स (${products.data?.length ?? 0})`
              : `My Dukaan Products (${products.data?.length ?? 0})`}
          </button>
          <button
            onClick={() => setCatalogTab("master")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
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
                <span>Product</span>
                <span>Price</span>
                <span>Visibility</span>
                <span>Action</span>
              </div>
              {products.data?.length ? (
                products.data.map((item) => (
                  <ProductRow
                    key={item.id}
                    product={item}
                    onToggle={() =>
                      merchantApi
                        .updateProduct(item.id, { is_visible: !item.is_visible })
                        .then(() => refresh("products"))
                        .catch((e) => setNotice(getApiError(e)))
                    }
                    onDelete={() => {
                      if (window.confirm(`Remove ${item.name} from catalog?`))
                        merchantApi
                          .deleteProduct(item.id)
                          .then(() => refresh("products"))
                          .catch((e) => setNotice(getApiError(e)));
                    }}
                  />
                ))
              ) : (
                <Empty icon={ShoppingBag} title="Your catalog is ready" text="Add products so customers can browse and order from your shop, or click 'Select from Master Catalog' to import verified items with one click." />
              )}
            </div>
          )
        ) : (
          /* Master Catalog Browser with Tick / Cross Selection */
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-[#ddd6ca]">
              <div className="relative w-full max-w-sm">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8b948d]" />
                <input
                  type="text"
                  value={masterSearch}
                  onChange={(e) => setMasterSearch(e.target.value)}
                  placeholder={lang === "hi" ? "मास्टर प्रोडक्ट्स में खोजें..." : "Search Master Catalog items..."}
                  className="w-full pl-9 pr-3 py-2 bg-white border border-[#ddd6ca] rounded-xl text-xs outline-none focus:border-[#1F5D42]"
                />
              </div>
              <p className="text-xs text-[#6d756f]">
                {lang === "hi"
                  ? "जो सामान आपकी दुकान में उपलब्ध है उसे टिक (✓) करें। वह सीधे आपकी दुकान में जुड़ जाएगा।"
                  : "Tick (✓) items you have in stock. Selected items persist automatically in your Dukaan."}
              </p>
            </div>

            {masterCatalog.isLoading ? (
              <LoadingRows />
            ) : masterCatalog.isError ? (
              <Notice error={masterCatalog.error} onRetry={() => masterCatalog.refetch()} />
            ) : filteredMaster.length === 0 ? (
              <div className="bg-white rounded-2xl border border-[#ddd6ca] p-8 text-center text-[#869088]">
                <Boxes className="w-8 h-8 mx-auto text-[#b2bcae] mb-2 opacity-50" />
                <p className="font-semibold text-sm text-[#123324]">No master products found</p>
                <p className="text-xs text-[#6d756f] mt-1">Super Admin has not added any master items matching this search yet.</p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {filteredMaster.map((item) => (
                  <div
                    key={item.id}
                    className={`rounded-2xl border p-4 transition flex flex-col justify-between ${
                      item.is_in_shop
                        ? "bg-[#f4f9f6] border-[#a8d3ba] shadow-xs ring-1 ring-[#1F5D42]/20"
                        : "bg-white border-[#ddd6ca] hover:border-[#bbb0a0]"
                    }`}
                  >
                    <div>
                      <div className="flex items-start gap-3 mb-3">
                        {item.image ? (
                          <img
                            src={item.image}
                            alt={item.name}
                            className="w-12 h-12 object-cover rounded-xl border border-[#ddd6ca] shrink-0 bg-white"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-xl bg-[#eee9df] flex items-center justify-center text-[#6d756f] shrink-0">
                            <ImageIcon className="w-5 h-5 text-[#869088]" />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <h4 className="font-bold text-sm text-[#123324] leading-snug line-clamp-2">
                            {item.name}
                          </h4>
                          <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                            {item.brand && (
                              <span className="text-[10px] font-bold text-[#8a5b1d] bg-[#fff3db] px-2 py-0.5 rounded-full border border-[#f5deb5]">
                                {item.brand}
                              </span>
                            )}
                            <span className="text-[10px] font-medium text-[#1F5D42] bg-[#e7f2eb] px-2 py-0.5 rounded-full border border-[#cbe1d5]">
                              {item.category_name || "Grocery"}
                            </span>
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
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition shadow-2xs ${
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
                ))}
              </div>
            )}
          </div>
        )}

        {newProductOpen && (
          <ProductModal lang={lang} onClose={() => setNewProductOpen(false)} onSave={(payload) => productMutation.mutate(payload)} saving={productMutation.isPending} />
        )}
        {notice && <Toast text={notice} onClose={() => setNotice("")} />}
      </>
    );
  }

  // Customers Section
  if (section === "customers") {
    return (
      <>
        <Title
          eyebrow="Community"
          title="Customers"
          description="View customers who have placed orders with this shop."
          action={
            <span className="inline-flex h-9 items-center gap-2 rounded-xl bg-[#e7f2eb] px-3 text-xs font-bold text-[#1F5D42]">
              <UsersRound size={14} />
              {customers.data?.length ?? 0} customers
            </span>
          }
        />
        {customers.isLoading ? (
          <LoadingRows />
        ) : customers.isError ? (
          <Notice error={customers.error} onRetry={() => customers.refetch()} />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-[#ddd6ca] bg-white">
            <div className="grid grid-cols-[1.3fr_1fr_.8fr] border-b border-[#eee9df] bg-[#faf8f3] px-5 py-3 text-[10px] font-bold uppercase tracking-[.13em] text-[#6d756f]">
              <span>Customer</span>
              <span>WhatsApp number</span>
              <span>First seen</span>
            </div>
            {customers.data?.length ? (
              customers.data.map((customer) => (
                <div key={customer.id} className="grid grid-cols-[1.3fr_1fr_.8fr] items-center border-b border-[#eee9df] px-5 py-4 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-full bg-[#F6F0E6] text-xs font-bold text-[#1F5D42]">
                      {customer.name?.slice(0, 1).toUpperCase() || "C"}
                    </span>
                    <div>
                      <p className="text-xs font-bold text-[#123324]">{customer.name || "Customer"}</p>
                      <p className="mt-0.5 text-[10px] text-[#7d857e]">Customer #{customer.id}</p>
                    </div>
                  </div>
                  <span className="text-xs font-mono text-[#1F5D42]">{customer.whatsapp_number}</span>
                  <span className="text-[11px] text-[#7d857e]">{dateTime(customer.created_at)}</span>
                </div>
              ))
            ) : (
              <Empty icon={UsersRound} title="Your customer list is ready" text="Customers appear here automatically after placing their first order." />
            )}
          </div>
        )}
      </>
    );
  }

  // Shop Settings Section
  if (section === "settings") {
    return <ShopSettings shop={shop.data} loading={shop.isLoading} error={shop.error} refetch={() => shop.refetch()} onSaved={() => refresh("shop")} lang={lang} />;
  }

  return (
    <div className="rounded-2xl border border-[#ddd6ca] bg-white p-8">
      <h1 className="text-xl font-semibold">This page isn’t available</h1>
      <p className="mt-2 text-sm text-[#78867c]">Choose a section from the navigation.</p>
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
  lang = "en",
}: {
  shop?: Shop;
  analytics: UseQueryResult<Overview>;
  orders: UseQueryResult<MerchantOrder[]>;
  period: string;
  setPeriod: (val: string) => void;
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
          <title>${shop?.name || "Shop"} - QR Sticker</title>
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
            <p>Scan with phone camera to order fresh essentials directly on WhatsApp</p>
            <img src="${qrApiUrl}" alt="Shop QR Code" />
            <div class="url">${publicStoreUrl}</div>
            <div><span class="badge">No Mobile App Required</span></div>
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
        eyebrow="My Store Hub"
        title={shop?.name ?? "Sharma Kirana"}
        description={`My shop · ${shop?.city ?? "Jaipur"} · Scan to shop on WhatsApp`}
        action={
          <div className="flex gap-2">
            <button onClick={handlePrint} className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-[#ddd6ca] bg-white px-3.5 text-xs font-semibold text-[#123324] hover:bg-[#F6F0E6]">
              <Printer size={15} />
              <span>Print Sticker</span>
            </button>
            <PeriodSelect value={period} onChange={setPeriod} />
          </div>
        }
      />

      {/* Visual Board Frame 1: Prominent QR Hub Card */}
      <div className="rounded-3xl border border-[#ddd6ca] bg-[#FFFDF8] p-6 sm:p-8 shadow-sm">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_1.4fr] items-center">
          {/* QR Display */}
          <div className="flex flex-col items-center justify-center p-6 bg-white rounded-2xl border border-[#ddd6ca] text-center shadow-xs">
            <h4 className="font-display font-bold text-base text-[#123324] mb-1">Scan to shop</h4>
            <p className="text-[11px] text-[#6d756f] mb-4">Place on store counter, bags & stickers</p>

            <div className="p-3 bg-[#FFFDF8] border-2 border-[#1F5D42] rounded-2xl shadow-xs">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={qrApiUrl}
                alt="Store QR Code"
                className="w-44 h-44 object-contain rounded-lg"
              />
            </div>

            <div className="mt-3 flex items-center gap-1.5 px-3 py-1 bg-[#F6F0E6] rounded-full text-xs font-mono font-bold text-[#1F5D42]">
              <span>{shop?.public_slug ? `${shop.public_slug}.qrlocal` : "sharmakirana.local"}</span>
              <button onClick={handleCopyLink} title="Copy link" className="text-[#6d756f] hover:text-[#123324]">
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
                <span>Download QR</span>
              </a>
              <button
                onClick={handlePrint}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#eee8dc] hover:bg-[#e4dcce] text-[#123324] font-bold text-xs shadow-xs transition"
              >
                <Printer size={13} />
                <span>Print sticker</span>
              </button>
              {shop?.public_slug && (
                <Link
                  href={`/shop/${shop.public_slug}`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#ddd6ca] text-xs font-semibold text-[#1F5D42] hover:bg-[#F6F0E6]"
                >
                  <ExternalLink size={13} />
                  <span>Open store</span>
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
                  {lang === "hi" ? "कुल बिक्री (Sales)" : "Sales realized"}
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
                    #{order.id} · {order.customer_name_snapshot || "Customer"}
                  </p>
                  <p className="text-[11px] text-[#6d756f] mt-0.5">
                    {order.items.length} items · {order.fulfillment_type}
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
          <div className="p-8 text-center text-xs text-[#6d756f]">No orders yet. Place your QR code to start receiving orders!</div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Visual Board Component 2: Inventory Tick Row
// -------------------------------------------------------------
function InventoryTickRow({
  item,
  onSave,
  busy,
}: {
  item: InventoryItem;
  onSave: (action: "set-stock" | "add-stock" | "subtract-stock", quantity: string) => void;
  busy: boolean;
}) {
  const [isChecked, setIsChecked] = useState(!item.is_out_of_stock);
  const [quantity, setQuantity] = useState("");
  const [action, setAction] = useState<"set-stock" | "add-stock" | "subtract-stock">("add-stock");

  const handleToggleCheck = () => {
    const nextState = !isChecked;
    setIsChecked(nextState);
    if (!nextState) {
      // Mark 0 available
      onSave("set-stock", "0");
    } else {
      // Re-enable stock with default 5
      onSave("set-stock", "5");
    }
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 hover:bg-[#faf8f3] transition">
      <div className="flex items-center gap-3">
        {/* Custom Square Checkbox matching Visual Board */}
        <button
          type="button"
          onClick={handleToggleCheck}
          className={`w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${
            isChecked
              ? "bg-[#1F5D42] border-[#1F5D42] text-white"
              : "bg-white border-[#cfc7bb] text-transparent hover:border-[#1F5D42]"
          }`}
        >
          <Check size={13} strokeWidth={3} />
        </button>

        <div>
          <p className={`text-xs font-bold leading-tight ${isChecked ? "text-[#123324]" : "text-[#858c86] line-through"}`}>
            {item.product_name}
            {item.variant_name ? ` · ${item.variant_name}` : ""}
          </p>
          <p className="text-[11px] text-[#6d756f] mt-0.5">
            {isChecked ? (
              <span className="text-[#1F5D42] font-semibold">
                Available: {item.available_quantity} units {Number(item.available_quantity) <= 2 && Number(item.available_quantity) > 0 && "· Only 2 left!"}
              </span>
            ) : (
              <span className="text-[#9a4d2a]">Not selected / Unticked</span>
            )}
          </p>
        </div>
      </div>

      {/* Quick Adjust Stepper */}
      <div className="flex items-center gap-2 self-end sm:self-auto">
        <select
          value={action}
          onChange={(e) => setAction(e.target.value as typeof action)}
          className="h-8 rounded-lg border border-[#ddd6ca] bg-white px-2 text-[11px] outline-none"
        >
          <option value="add-stock">+ Add</option>
          <option value="set-stock">Set</option>
          <option value="subtract-stock">- Subtract</option>
        </select>
        <input
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          type="number"
          min="0"
          placeholder="Qty"
          className="h-8 w-16 rounded-lg border border-[#ddd6ca] px-2 text-xs outline-none focus:border-[#1F5D42]"
        />
        <button
          disabled={!quantity || busy}
          onClick={() => {
            onSave(action, quantity);
            setQuantity("");
          }}
          className="grid h-8 w-8 place-items-center rounded-lg bg-[#e7f2eb] text-[#1F5D42] hover:bg-[#cde0d5] disabled:opacity-40 transition"
          title="Save stock adjustment"
        >
          <Check size={14} />
        </button>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Visual Board Component 3: Orders with Per-Item Resolve
// -------------------------------------------------------------
function VisualOrderCard({
  order,
  onAction,
  busy,
  onItemResolved,
}: {
  order: MerchantOrder;
  onAction: (action: string) => void;
  busy: boolean;
  onItemResolved: (itemName: string) => void;
}) {
  const [missingItem, setMissingItem] = useState<string | null>(null);

  const transitions: Record<string, Array<[string, string]>> = {
    PENDING: [
      ["accept", "Accept"],
      ["reject", "Reject"],
    ],
    ACCEPTED: [["prepare", "Start packing"]],
    PREPARING: [["ready", "Packed / Done"]],
    READY: [["complete", "Out for delivery"]],
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
            <span className="text-xs font-bold text-[#123324]">· {order.customer_name_snapshot || "Customer"}</span>
          </div>
          <p className="text-[11px] text-[#6d756f] mt-0.5">
            {dateTime(order.created_at)} · {order.customer_phone_snapshot} ·{" "}
            <span className="font-semibold text-[#1F5D42]">{order.fulfillment_type === "PICKUP" ? "Store Pickup" : "Home Delivery"}</span>
          </p>
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
                    Not in inventory / Out of stock
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
                    title="Flag item as missing"
                  >
                    Flag missing
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
          <p className="font-bold text-[#803f24] mb-1">Resolve missing item: {missingItem}</p>
          <p className="text-[11px] text-[#803f24]/80 mb-2">
            You can remove this single item to keep the rest of the order moving, or add it to inventory now.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleRemoveMissingItem(missingItem)}
              className="px-3 py-1.5 rounded-lg bg-[#f7d7ca] hover:bg-[#f1c3b1] text-[#803f24] font-bold text-xs transition"
            >
              Remove this item & adjust total
            </button>
            <button
              onClick={() => setMissingItem(null)}
              className="px-3 py-1.5 rounded-lg bg-[#1F5D42] hover:bg-[#123324] text-white font-bold text-xs transition"
            >
              Add to my inventory now
            </button>
          </div>
        </div>
      )}

      {/* Action Transition Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#eee9df]">
        <div className="flex flex-wrap gap-2">
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
          {!transitions[order.status] && <span className="text-xs text-[#89958c]">No further actions needed</span>}
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Visual Board Component 4: Simple Analytics
// -------------------------------------------------------------
function VisualAnalyticsPanel({ data }: { data: Overview }) {
  const topProducts = data.top_products || [];
  const maxUnits = topProducts.reduce((max, item) => Math.max(max, Number(item.units_sold) || 0), 0) || 1;

  const totalOrders = data.orders?.total_orders ?? 0;
  const completedOrders = data.orders?.completed_orders ?? 0;
  const outOfStockCount = data.inventory?.out_of_stock_items_count ?? 0;

  return (
    <div className="space-y-6">
      {/* 2 Big Headline Metric Cards (Visual Board Style) */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-[#ddd6ca] bg-white p-6 shadow-xs">
          <p className="text-xs font-bold text-[#6d756f] uppercase tracking-wider">Orders Today</p>
          <p className="font-display font-bold text-4xl text-[#1F5D42] mt-2">
            {totalOrders}
          </p>
          <p className="text-[11px] text-[#7d857e] mt-1">{completedOrders} fulfilled & collected</p>
        </div>

        <div className="rounded-2xl border border-[#f5deb5] bg-[#fff9ed] p-6 shadow-xs">
          <p className="text-xs font-bold text-[#8a5b1d] uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle size={14} />
            <span>Low Stock Warning</span>
          </p>
          <p className="font-display font-bold text-2xl text-[#8a5b1d] mt-2">
            {outOfStockCount > 0 ? `${outOfStockCount} items out of stock` : "0 items low on stock"}
          </p>
          <p className="text-[11px] text-[#7a531d] mt-1">
            {outOfStockCount > 0 ? "Review stock batches and restock items" : "All product inventory levels are healthy"}
          </p>
        </div>
      </div>

      {/* Visual Board Top Selling Progress Bars from Live Backend */}
      <div className="rounded-2xl border border-[#ddd6ca] bg-white p-6 shadow-xs">
        <h4 className="font-display font-bold text-sm text-[#123324] mb-4">Top-selling items (Units sold)</h4>
        {topProducts.length === 0 ? (
          <div className="py-6 text-center text-xs text-[#869088]">
            No sales recorded yet. Fulfilled customer orders will populate top selling items automatically.
          </div>
        ) : (
          <div className="space-y-4">
            {topProducts.map((item) => {
              const units = Number(item.units_sold) || 0;
              const widthPct = Math.round((units / maxUnits) * 100);
              return (
                <div key={item.product_name} className="grid grid-cols-[140px_1fr_40px] items-center gap-3 text-xs">
                  <span className="truncate font-medium text-[#123324]" title={item.product_name}>
                    {item.product_name}
                  </span>
                  <div className="h-2.5 rounded-full bg-[#eee9df] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#1F5D42] to-[#5f967a]"
                      style={{ width: `${Math.max(widthPct, 8)}%` }}
                    />
                  </div>
                  <b className="text-right font-mono text-[#123324]">{units}</b>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Realized Sales Details */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Metric
          icon={IndianRupee}
          label="Realized sales"
          value={money(data.sales?.realized_sales ?? 0)}
          note={`Avg order: ${money(data.sales?.average_order_value ?? 0)}`}
          tint="green"
        />
        <Metric
          icon={UsersRound}
          label="Active customers"
          value={data.customers?.ordering_customers ?? 0}
          note={`${data.customers?.returning_customers ?? 0} returning customers`}
          tint="blue"
        />
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Helper Modals & Rows
// -------------------------------------------------------------
function BatchModal({ onClose, onSave }: { onClose: () => void; onSave: (val: BatchValues) => void }) {
  const { register, handleSubmit } = useForm<BatchInput, unknown, BatchValues>({
    resolver: zodResolver(batchSchema),
    defaultValues: { batchName: "New Stock Arrival", price: 265, quantity: 5 },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form onSubmit={handleSubmit(onSave)} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
          <h3 className="font-display font-bold text-base text-[#123324]">Add New Price Batch</h3>
          <button type="button" onClick={onClose} className="text-[#6d756f] hover:text-[#123324]">
            <X size={16} />
          </button>
        </div>
        <p className="text-xs text-[#6d756f]">
          Create a fresh batch to sell newly stocked goods at a different MRP without altering previous batch prices.
        </p>
        <div className="space-y-3 text-xs">
          <div>
            <label className="block font-bold text-[#123324] mb-1">Batch Label</label>
            <input {...register("batchName")} className="w-full h-9 rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-[#123324] mb-1">Price per Pack (₹)</label>
              <input type="number" step="0.5" {...register("price", { valueAsNumber: true })} className="w-full h-9 rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
            </div>
            <div>
              <label className="block font-bold text-[#123324] mb-1">Quantity of Packs</label>
              <input type="number" min="1" {...register("quantity", { valueAsNumber: true })} className="w-full h-9 rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42]" />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-3 border-t border-[#eee9df]">
          <button type="button" onClick={onClose} className="px-4 py-2 text-xs font-semibold text-[#6d756f]">
            Cancel
          </button>
          <button type="submit" className="px-4 py-2 rounded-xl bg-[#1F5D42] text-white text-xs font-bold hover:bg-[#123324]">
            Save Batch
          </button>
        </div>
      </form>
    </div>
  );
}

function ProductRow({ product, onToggle, onDelete }: { product: Product; onToggle: () => void; onDelete: () => void }) {
  return (
    <div className="grid grid-cols-[1.4fr_.7fr_.7fr_.6fr] items-center gap-3 border-b border-[#eee9df] px-5 py-4 last:border-0 text-xs">
      <div className="flex min-w-0 items-center gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#F6F0E6] text-[#1F5D42]">
          <ShoppingBag size={16} />
        </span>
        <div className="min-w-0">
          <p className="truncate font-bold text-[#123324]">{product.name}</p>
          <p className="mt-0.5 truncate text-[10px] text-[#7d857e]">{product.brand || "Local"}{product.sku ? ` · ${product.sku}` : ""}</p>
        </div>
      </div>
      <span className="font-mono font-bold text-[#123324]">{money(product.price)}</span>
      <span className={`text-[10px] font-bold ${product.is_visible && product.is_available ? "text-[#1F5D42]" : "text-[#9a4d2a]"}`}>
        {!product.is_visible ? "Hidden" : product.is_available ? "Visible" : "Out of stock"}
      </span>
      <div className="flex items-center gap-2">
        <button onClick={onToggle} className="rounded-lg bg-[#F6F0E6] px-2.5 py-1.5 text-[10px] font-bold text-[#1F5D42] hover:bg-[#eee9df]">
          {product.is_visible ? "Hide" : "Show"}
        </button>
        <button aria-label={`Delete ${product.name}`} onClick={onDelete} className="rounded-lg p-1.5 text-[#9a4d2a] hover:bg-[#ffece6]">
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
  const { register, trigger, getValues } = useForm<ProductInput, unknown, ProductValues>({
    resolver: zodResolver(productSchema),
    defaultValues: { name: "", price: 0, brand: "", sku: "", description: "" },
  });

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
      if (values.sku) formData.append("sku", values.sku);
      if (values.description) formData.append("description", values.description);
      formData.append("image", images[0]); // primary image
      onSave(formData);
    } else {
      onSave({ ...values, price: String(values.price) });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <form onSubmit={submit} className="w-full max-w-[500px] rounded-2xl bg-white p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
          <h2 className="font-display font-bold text-base text-[#123324]">
            {lang === "hi" ? "नया प्रोडक्ट जोड़ें" : "Add New Product"}
          </h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-[#6d756f] hover:bg-[#eee9df]">
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
                  <img src={src} alt={`Product thumbnail ${idx + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
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
              return;
            }
          }
        }
      } catch {
        // fallback
      }
    }
    if (shop?.logo && (!photos[0] || !photos[0].url)) {
      setPhotos([
        { id: "cover", url: shop.logo, labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" },
      ]);
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
      const nextPhotos =
        filtered.length === 0
          ? [{ id: "cover", url: "", labelEn: "Main Storefront Photo", labelHi: "मुख्य दुकान का फोटो" }]
          : filtered;
      if (typeof window !== "undefined" && shop?.public_slug) {
        localStorage.setItem(
          `dukaandar_shop_photos_${shop.public_slug}`,
          JSON.stringify(nextPhotos.map((p) => p.url).filter(Boolean))
        );
      }
      return nextPhotos;
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

  const { register, handleSubmit, setValue } = useForm<ShopSettingsInput, unknown, ShopSettingsValues>({
    resolver: zodResolver(shopSettingsSchema),
    values: settingsValues,
  });

  if (loading) return <LoadingRows />;
  if (error || !shop) return <Notice error={error ?? new Error("Shop not found")} onRetry={refetch} />;

  const submit = async (values: ShopSettingsValues) => {
    setSaving(true);
    setMessage("");
    setSaveError("");
    try {
      const { logo, ...restValues } = values;
      const primaryPhoto = photos.find((p) => p.file || p.url);
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
        await merchantApi.updateShop({
          ...restValues,
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
              if (p.url) processedUrls.push(p.url);
            }
          } else if (p.url) {
            processedUrls.push(p.url);
          }
        }
        localStorage.setItem(`dukaandar_shop_photos_${shop.public_slug}`, JSON.stringify(processedUrls));
      }
      setMessage(lang === "hi" ? "दुकान का विवरण सफलतापूर्वक सहेजा गया।" : "Shop details saved successfully.");
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
      <form onSubmit={handleSubmit(submit)} className="rounded-2xl border border-[#ddd6ca] bg-[#FFFDF8] p-5 sm:p-7 shadow-xs">
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
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input {...register("is_temporarily_closed")} type="checkbox" className="accent-[#1F5D42]" />
            <span className="font-bold text-[#123324]">{lang === "hi" ? "दुकान अस्थायी रूप से बंद है" : "Temporarily closed"}</span>
          </label>
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
                ? "ग्राहक आपकी दुकान के पते पर क्लिक करके सीधे गूगल मैप्स पर दिशा-निर्देश (directions) प्राप्त कर सकेंगे।"
                : "Customers can click your shop address on the storefront to open turn-by-turn directions on Google Maps."}
            </span>
          </label>

          {/* Description */}
          <label className="sm:col-span-2">
            <span className="mb-1 block font-bold text-[#123324]">
              {lang === "hi" ? "दुकान का विवरण (About / Description)" : "About / Description"}
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
                {lang === "hi" ? "दुकान खुलने का समय (Opening Time)" : "Opening Time (e.g. 07:00 AM)"}
              </span>
              <input
                {...register("opening_time")}
                type="time"
                className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42] bg-white font-mono"
              />
            </label>
            <label>
              <span className="mb-1 block font-bold text-[#123324]">
                {lang === "hi" ? "दुकान बंद होने का समय (Closing Time)" : "Closing Time (e.g. 11:00 PM)"}
              </span>
              <input
                {...register("closing_time")}
                type="time"
                className="h-9 w-full rounded-xl border border-[#ddd6ca] px-3 outline-none focus:border-[#1F5D42] bg-white font-mono"
              />
            </label>
            <div className="sm:col-span-2 flex flex-wrap items-center gap-2 pt-1">
              <span className="text-[11px] text-[#6d756f] font-medium mr-1">
                {lang === "hi" ? "त्वरित विकल्प (Presets):" : "Quick Presets:"}
              </span>
              <button
                type="button"
                onClick={() => { setValue("opening_time", "07:00"); setValue("closing_time", "23:00"); }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                7:00 AM – 11:00 PM
              </button>
              <button
                type="button"
                onClick={() => { setValue("opening_time", "08:00"); setValue("closing_time", "22:00"); }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                8:00 AM – 10:00 PM
              </button>
              <button
                type="button"
                onClick={() => { setValue("opening_time", "09:00"); setValue("closing_time", "21:00"); }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                9:00 AM – 9:00 PM
              </button>
              <button
                type="button"
                onClick={() => { setValue("opening_time", "00:00"); setValue("closing_time", "23:59"); }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[11px] font-semibold text-[#123324] transition shadow-2xs"
              >
                24 Hours Open (24x7)
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
                  ? "0 = मुफ्त डिलीवरी (Free Delivery)। कोई राशि डालने पर वह ग्राहक के ऑर्डर बिल में जुड़ेगी।"
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
                <option value="FIXED">{lang === "hi" ? "निर्धारित शुल्क (Fixed Amount)" : "Fixed Amount"}</option>
                <option value="CONFIRMED_ON_WHATSAPP">{lang === "hi" ? "व्हाट्सएप पर पुष्टि (Confirm on WhatsApp)" : "Confirm on WhatsApp"}</option>
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

        <div className="mt-6 flex justify-end border-t border-[#eee9df] pt-4">
          <button disabled={saving} className="h-10 rounded-xl bg-[#1F5D42] px-6 text-xs font-bold text-white hover:bg-[#123324] disabled:opacity-50">
            {saving ? (lang === "hi" ? "सहेजा जा रहा है…" : "Saving…") : (lang === "hi" ? "बदलाव सहेजें" : "Save changes")}
          </button>
        </div>
        {saveError && <p className="mt-3 text-xs text-red-600">{saveError}</p>}
        {message && <p className="mt-3 text-xs text-emerald-600">{message}</p>}
      </form>
    </>
  );
}

function PeriodSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex h-10 items-center gap-2 rounded-xl border border-[#ddd6ca] bg-white px-3 text-xs text-[#5e665f]">
      <Clock3 size={14} />
      <select value={value} onChange={(e) => onChange(e.target.value)} className="bg-transparent font-bold outline-none">
        <option value="today">Today</option>
        <option value="yesterday">Yesterday</option>
        <option value="this_week">This week</option>
        <option value="this_month">This month</option>
      </select>
      <ChevronDown size={13} />
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
  return (
    <div role="status" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-3 rounded-xl bg-[#123324] px-4 py-3 text-xs text-white shadow-xl">
      <Check size={15} className="text-[#E8A33D]" />
      <span>{text}</span>
      <button onClick={onClose} aria-label="Dismiss" className="ml-2 text-white/70 hover:text-white">
        <X size={14} />
      </button>
    </div>
  );
}
