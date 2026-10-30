"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/admin/Navbar";
import { Sidebar } from "@/components/admin/Sidebar";
import { MetricCard } from "@/components/admin/MetricCard";
import { OnboardMerchantModal } from "@/components/admin/OnboardMerchantModal";
import { MerchantTable, MerchantShopItem } from "@/components/admin/MerchantTable";
import { MasterCatalogTable } from "@/components/admin/MasterCatalogTable";
import { CampaignsManager, CampaignItem } from "@/components/admin/CampaignsManager";
import { TopProductsRankings, TopProductItem } from "@/components/admin/TopProductsRankings";
import { OrderStatusBreakdown } from "@/components/admin/OrderStatusBreakdown";
import { AnalyticsToolbar } from "@/components/admin/AnalyticsToolbar";
import { SecurityRecoveryModal } from "@/components/admin/SecurityRecoveryModal";
import { ProductPromotionModal } from "@/components/admin/ProductPromotionModal";
import {
  IndianRupee,
  Store,
  Receipt,
  AlertTriangle,
  Trophy,
  TrendingUp,
  ShieldCheck,
  Megaphone,
  Boxes,
  CloudUpload,
  UserPlus,
  Users,
} from "lucide-react";
import { adminApi, PlatformAnalytics, MasterProduct } from "@/lib/api/admin";

export default function SuperAdminDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("overview");
  const [isOnboardOpen, setIsOnboardOpen] = useState(false);
  const [isSecurityOpen, setIsSecurityOpen] = useState(false);
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const [analytics, setAnalytics] = useState<PlatformAnalytics | null>(null);
  const [masterProducts, setMasterProducts] = useState<MasterProduct[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [topProducts, setTopProducts] = useState<TopProductItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Analytics filter and horizon controls
  const [selectedPeriod, setSelectedPeriod] = useState<string>("today");
  const [selectedShopId, setSelectedShopId] = useState<number | null>(null);
  const [customStartDate, setCustomStartDate] = useState<string>("");
  const [customEndDate, setCustomEndDate] = useState<string>("");
  const [analyticsLoading, setAnalyticsLoading] = useState<boolean>(false);

  // Merchants state populated from live backend API
  const [merchants, setMerchants] = useState<MerchantShopItem[]>([]);

  // Admin username detection
  const [adminUsername, setAdminUsername] = useState<string>("Super Admin");

  useEffect(() => {
    const explicitUsername = localStorage.getItem("admin_username");
    if (explicitUsername && explicitUsername.trim() !== "") {
      setAdminUsername(explicitUsername);
      return;
    }
    const storedUser = localStorage.getItem("admin_user");
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        if (parsed?.username || parsed?.email) {
          setAdminUsername(parsed.username || parsed.email);
          return;
        }
      } catch {
        // Fallback
      }
    }
  }, []);

  const refreshAnalytics = async (
    period = selectedPeriod,
    shopId = selectedShopId,
    start = customStartDate,
    end = customEndDate
  ) => {
    if (period === "custom" && (!start || !end)) {
      return;
    }
    setAnalyticsLoading(true);
    try {
      const [analyticsData, topProductsData] = await Promise.all([
        adminApi.getAnalytics(undefined, period, shopId, start, end).catch(() => null),
        adminApi.getTopProducts(undefined, period, 10, shopId, start, end).catch(() => ({ top_products: [] })),
      ]);
      if (analyticsData) setAnalytics(analyticsData);
      if (topProductsData && topProductsData.top_products) setTopProducts(topProductsData.top_products);
    } catch {
      // Live API error
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const handlePeriodChange = (newPeriod: string) => {
    setSelectedPeriod(newPeriod);
    if (newPeriod !== "custom") {
      refreshAnalytics(newPeriod, selectedShopId, customStartDate, customEndDate);
    }
  };

  const handleShopChange = (newShopId: number | null) => {
    setSelectedShopId(newShopId);
    refreshAnalytics(selectedPeriod, newShopId, customStartDate, customEndDate);
  };

  const handleCustomDatesChange = (start: string, end: string) => {
    setCustomStartDate(start);
    setCustomEndDate(end);
    if (start && end) {
      refreshAnalytics("custom", selectedShopId, start, end);
    }
  };

  const loadData = async () => {
    try {
      const [analyticsData, catalogData, campaignsData, topProductsData, liveShops] = await Promise.all([
        adminApi.getAnalytics(undefined, selectedPeriod, selectedShopId, customStartDate, customEndDate).catch(() => null),
        adminApi.listMasterProducts().catch(() => ({ results: [] })),
        adminApi.listCampaigns().catch(() => []),
        adminApi.getTopProducts(undefined, selectedPeriod, 10, selectedShopId, customStartDate, customEndDate).catch(() => ({ top_products: [] })),
        adminApi.listShops().catch(() => null),
      ]);
      if (analyticsData) setAnalytics(analyticsData);
      if (catalogData && catalogData.results) setMasterProducts(catalogData.results);
      if (Array.isArray(campaignsData)) setCampaigns(campaignsData);
      if (topProductsData && topProductsData.top_products) setTopProducts(topProductsData.top_products);
      if (liveShops && Array.isArray(liveShops)) {
        setMerchants(liveShops);
      }
    } catch {
      // Live API error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("admin_access_token");
    if (!token) {
      router.push("/admin/login");
      return;
    }
    loadData();
  }, []);

  const handleTabChange = (tabId: string) => {
    if (tabId === "security") {
      setIsSecurityOpen(true);
    } else {
      setActiveTab(tabId);
    }
  };

  // Formatted Metric Values
  const periodLabels: Record<string, string> = {
    today: "Today",
    yesterday: "Yesterday",
    this_week: "This Week",
    this_month: "This Month",
    custom: "Custom Range",
  };
  const activePeriodLabel = periodLabels[selectedPeriod] || selectedPeriod;

  const currentFilteredShop = merchants.find((m) => m.shopId === selectedShopId);
  const scopePrefix = currentFilteredShop ? currentFilteredShop.shopName : "Platform";

  const gmv = analytics?.sales?.realized_sales
    ? `₹${parseFloat(analytics.sales.realized_sales).toLocaleString("en-IN")}`
    : "₹0";
  const activeShops = analytics?.shops?.active_shops ?? merchants.length;
  const totalShops = analytics?.shops?.total_shops ?? merchants.length;
  const ordersTotal = analytics?.orders?.total_orders ?? 0;
  const orderingCustomers = analytics?.customers?.ordering_customers ?? 0;
  const outOfStock = analytics?.inventory?.out_of_stock_items_count ?? 0;
  const avgOrderText = analytics?.sales?.average_order_value
    ? `Avg Order ₹${parseFloat(analytics.sales.average_order_value).toLocaleString("en-IN")}`
    : "Avg Order ₹0";

  return (
    <div className="bg-slate-50 min-h-screen text-slate-900 font-sans antialiased">
      {/* Top Navbar */}
      <Navbar />

      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        merchantCount={merchants.length}
        catalogCount={masterProducts.length}
        campaignCount={campaigns.length}
      />

      {/* Main Content Viewport */}
      <main className="ml-64 mt-14 p-6 min-h-[calc(100vh-3.5rem)]">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header Title Section */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 bg-white p-5 rounded-lg border shadow-sm">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  Platform Governance Matrix
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#1F5D42]/10 text-[#1F5D42] tracking-wider uppercase">
                  {activeTab}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
                <p className="text-xs text-slate-600">
                  Logged in as <strong className="text-slate-900 font-semibold">{adminUsername}</strong> (Super Admin)
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsSecurityOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 bg-white text-slate-700 text-xs font-semibold rounded hover:bg-slate-50 transition-all shadow-sm"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                Security & Recovery
              </button>
              <button
                onClick={() => setIsPromoteOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded hover:bg-emerald-100 transition-all shadow-sm"
              >
                <CloudUpload className="w-3.5 h-3.5 text-emerald-700" />
                Promote Merchant SKU
              </button>
              <button
                onClick={() => setIsOnboardOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1F5D42] text-white text-xs font-semibold rounded hover:bg-[#164430] shadow-sm transition-all"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Onboard New Merchant</span>
              </button>
            </div>
          </div>

          {/* TAB 1: NETWORK OVERVIEW (Executive summary, uncluttered) */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* KPI Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title={`${scopePrefix} GMV (${activePeriodLabel})`}
                  value={gmv}
                  contextText="Realized Sales"
                  icon={IndianRupee}
                  accentColor="green"
                />
                <MetricCard
                  title="Total Active Shops"
                  value={`${activeShops} / ${totalShops}`}
                  contextText="Network Health"
                  icon={Store}
                  accentColor="emerald"
                />
                <MetricCard
                  title={`Completed Orders (${activePeriodLabel})`}
                  value={ordersTotal.toLocaleString("en-IN")}
                  contextText={avgOrderText}
                  icon={Receipt}
                  accentColor="slate"
                />
                <MetricCard
                  title="Stock-Out Alerts"
                  value={`${outOfStock} SKUs`}
                  contextText="Critical Replenishment"
                  icon={AlertTriangle}
                  accentColor="amber"
                />
              </div>

              {/* 2-Column Summary Cards */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Registered Tenants Preview */}
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <Store className="w-4 h-4 text-[#1F5D42]" />
                      <h3 className="text-sm font-bold text-slate-900">Tenant Directory Snapshot</h3>
                    </div>
                    <button
                      onClick={() => setActiveTab("merchants")}
                      className="text-xs font-semibold text-[#1F5D42] hover:underline"
                    >
                      View All {merchants.length} Tenants →
                    </button>
                  </div>
                  <div className="mt-4 space-y-2.5">
                    {merchants.length === 0 ? (
                      <div className="py-8 text-center text-xs text-slate-400">
                        No merchants onboarded yet. Use the Onboard button above to add one.
                      </div>
                    ) : (
                      merchants.slice(0, 4).map((m) => (
                        <div
                          key={m.id}
                          className="flex items-center justify-between p-3 rounded-md bg-slate-50 border border-slate-100 hover:border-slate-200 transition-colors"
                        >
                          <div>
                            <div className="text-xs font-bold text-slate-900">{m.shopName || m.merchantName}</div>
                            <div className="text-[11px] text-slate-500 font-mono">
                              Mobile: {m.mobileNumber} | {m.city || "Urban Node"}
                            </div>
                          </div>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              m.status === "ACTIVE"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {m.status}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Master Catalog Preview */}
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <Boxes className="w-4 h-4 text-[#1F5D42]" />
                      <h3 className="text-sm font-bold text-slate-900">Master Catalog Snapshot</h3>
                    </div>
                    <button
                      onClick={() => setActiveTab("catalog")}
                      className="text-xs font-semibold text-[#1F5D42] hover:underline"
                    >
                      View All {masterProducts.length} SKUs →
                    </button>
                  </div>
                  <div className="mt-4 space-y-2.5">
                    {masterProducts.length === 0 ? (
                      <div className="py-8 text-center text-xs text-slate-400">
                        No master catalog products found.
                      </div>
                    ) : (
                      masterProducts.slice(0, 4).map((p) => (
                        <div
                          key={p.id}
                          className="flex items-center justify-between p-3 rounded-md bg-slate-50 border border-slate-100"
                        >
                          <div>
                            <div className="text-xs font-bold text-slate-900">{p.name}</div>
                            <div className="text-[11px] text-slate-500">
                              Brand: {p.brand || "Generic"} | {p.category_name || "General"}
                            </div>
                          </div>
                          <div className="text-right text-xs font-semibold text-emerald-700">
                            {p.is_verified ? "Verified SKU" : "Standard"}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Quick Navigation Panels */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div
                  onClick={() => setActiveTab("merchants")}
                  className="bg-white border border-slate-200 hover:border-[#1F5D42] p-4 rounded-lg cursor-pointer transition-all shadow-sm group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <Store className="w-5 h-5 text-[#1F5D42]" />
                    <span className="text-xs font-bold text-slate-400 group-hover:text-[#1F5D42]">
                      {merchants.length} Shops →
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900">Tenant Directory</h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Manage tenant credentials, activate/deactivate shops, and view store configs.
                  </p>
                </div>

                <div
                  onClick={() => setActiveTab("catalog")}
                  className="bg-white border border-slate-200 hover:border-[#1F5D42] p-4 rounded-lg cursor-pointer transition-all shadow-sm group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <Boxes className="w-5 h-5 text-[#1F5D42]" />
                    <span className="text-xs font-bold text-slate-400 group-hover:text-[#1F5D42]">
                      {masterProducts.length} Items →
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900">Master Catalog</h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Universal barcode registry, categories, and merchant SKU promotions.
                  </p>
                </div>

                <div
                  onClick={() => setActiveTab("campaigns")}
                  className="bg-white border border-slate-200 hover:border-[#1F5D42] p-4 rounded-lg cursor-pointer transition-all shadow-sm group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <Megaphone className="w-5 h-5 text-[#1F5D42]" />
                    <span className="text-xs font-bold text-slate-400 group-hover:text-[#1F5D42]">
                      {campaigns.length} Active →
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900">Marketing Campaigns</h4>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Launch platform-wide banners, discounts, and customer incentives.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: TENANT DIRECTORY (Exclusive dedicated view) */}
          {activeTab === "merchants" && (
            <MerchantTable
              merchants={merchants}
              onRefresh={loadData}
            />
          )}

          {/* TAB 3: MASTER CATALOG (Exclusive dedicated view) */}
          {activeTab === "catalog" && (
            <MasterCatalogTable
              products={masterProducts}
              onRefresh={loadData}
              onOpenPromote={() => setIsPromoteOpen(true)}
            />
          )}

          {/* TAB 4: MARKETING CAMPAIGNS (Exclusive dedicated view) */}
          {activeTab === "campaigns" && (
            <CampaignsManager
              campaigns={campaigns}
              onRefresh={loadData}
            />
          )}

          {/* TAB 5: PLATFORM ANALYTICS (Metrics & Performance) */}
          {activeTab === "analytics" && (
            <div className="space-y-6">
              {/* Analytics Interactive Filter Toolbar */}
              <AnalyticsToolbar
                selectedPeriod={selectedPeriod}
                onPeriodChange={handlePeriodChange}
                selectedShopId={selectedShopId}
                onShopChange={handleShopChange}
                customStartDate={customStartDate}
                customEndDate={customEndDate}
                onCustomDatesChange={handleCustomDatesChange}
                merchants={merchants}
                loading={analyticsLoading}
                onRefresh={() => refreshAnalytics()}
              />

              {/* 5 KPI Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <MetricCard
                  title={`${scopePrefix} GMV (${activePeriodLabel})`}
                  value={gmv}
                  contextText="Realized Sales"
                  icon={IndianRupee}
                  accentColor="green"
                />
                <MetricCard
                  title={currentFilteredShop ? "Tenant Status" : "Active Merchant Nodes"}
                  value={currentFilteredShop ? currentFilteredShop.status : `${activeShops} / ${totalShops}`}
                  contextText={currentFilteredShop ? (currentFilteredShop.city || "Single Tenant") : "Platform Coverage"}
                  icon={Store}
                  accentColor="emerald"
                />
                <MetricCard
                  title={`Orders (${activePeriodLabel})`}
                  value={ordersTotal.toLocaleString("en-IN")}
                  contextText={avgOrderText}
                  icon={Receipt}
                  accentColor="slate"
                />
                <MetricCard
                  title="Unique Buyers"
                  value={orderingCustomers.toLocaleString("en-IN")}
                  contextText="Active in period"
                  icon={Users}
                  accentColor="blue"
                />
                <MetricCard
                  title="Stock-Out Alerts"
                  value={`${outOfStock} SKUs`}
                  contextText="Zero Available Stock"
                  icon={AlertTriangle}
                  accentColor="amber"
                />
              </div>

              {/* Order Status Breakdown + Top Performers */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 1. Order Lifecycle & Fulfillment Pipeline */}
                <OrderStatusBreakdown
                  distribution={analytics?.orders?.status_distribution}
                  totalOrders={ordersTotal}
                />

                {/* 2. Top Shops Leaderboard */}
                <div className="bg-white border border-slate-200 rounded p-4 shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <Trophy className="w-4 h-4 text-amber-500" />
                        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                          Top Performing Shops
                        </h3>
                      </div>
                      <span className="text-[11px] text-slate-400">Ranked by Sales</span>
                    </div>
                    <div className="space-y-2.5">
                      {!analytics?.top_shops || analytics.top_shops.length === 0 ? (
                        <div className="p-8 text-center text-xs text-slate-400">
                          No merchant order history recorded for this period.
                        </div>
                      ) : (
                        analytics.top_shops.slice(0, 5).map((s, idx) => (
                          <div
                            key={s.shop_id}
                            className={`p-3 rounded border flex items-center justify-between ${
                              selectedShopId === s.shop_id
                                ? "border-emerald-500 bg-emerald-50/40"
                                : "border-slate-100 bg-slate-50/50"
                            }`}
                          >
                            <div>
                              <div className="text-[10px] font-bold text-slate-400">RANK #{idx + 1}</div>
                              <div className="text-xs font-bold text-slate-900">{s.shop_name}</div>
                              <div className="text-[11px] text-slate-500">{s.completed_orders} orders completed</div>
                            </div>
                            <div className="text-right">
                              <div className="text-xs font-mono font-bold text-[#1F5D42]">
                                ₹{parseFloat(s.realized_sales).toLocaleString("en-IN")}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. Top SKUs Leaderboard */}
                <TopProductsRankings products={topProducts} />
              </div>
            </div>
          )}

          {/* TAB 6: CONSOLE SETTINGS */}
          {activeTab === "settings" && (
            <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-6">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Platform Console Settings</h3>
                <p className="text-xs text-slate-500 mt-1">Super Admin runtime session configuration and environment telemetry.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                  <div className="font-semibold text-slate-800">Authenticated Super Admin</div>
                  <div className="text-slate-600">Identifier: <span className="font-mono text-slate-900 font-bold">{adminUsername}</span></div>
                  <div className="text-slate-600">Role: <span className="font-semibold text-emerald-700">SUPER_ADMIN</span></div>
                  <div className="text-slate-600">Permissions: <span className="font-mono text-slate-700">Global Read/Write/Elevated</span></div>
                </div>

                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                  <div className="font-semibold text-slate-800">API Service Node</div>
                  <div className="text-slate-600">Backend Endpoint: <span className="font-mono text-slate-900">http://localhost:8000/api/v1/</span></div>
                  <div className="text-slate-600">Auth Gateway: <span className="font-mono text-slate-900">/api/v1/auth/super-admin/</span></div>
                  <div className="text-slate-600">Status: <span className="text-emerald-700 font-semibold">Connected (PostgreSQL Neon Active)</span></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Product Promotion Moderation Modal */}
      <ProductPromotionModal
        isOpen={isPromoteOpen}
        onClose={() => setIsPromoteOpen(false)}
        onSuccess={() => {
          loadData();
          setIsPromoteOpen(false);
        }}
      />

      {/* Onboard Merchant Slide-Over Modal */}
      <OnboardMerchantModal
        isOpen={isOnboardOpen}
        onClose={() => setIsOnboardOpen(false)}
        onSuccess={() => {
          loadData();
          setIsOnboardOpen(false);
        }}
      />

      {/* Security & Recovery Modal */}
      <SecurityRecoveryModal
        isOpen={isSecurityOpen}
        onClose={() => setIsSecurityOpen(false)}
      />
    </div>
  );
}
