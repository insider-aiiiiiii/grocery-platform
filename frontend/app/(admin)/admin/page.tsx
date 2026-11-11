"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/admin/Sidebar";
import { MetricCard } from "@/components/admin/MetricCard";
import { OnboardMerchantModal } from "@/components/admin/OnboardMerchantModal";
import { MerchantTable, MerchantShopItem } from "@/components/admin/MerchantTable";
import { MasterCatalogTable } from "@/components/admin/MasterCatalogTable";
import { CampaignsManager, CampaignItem } from "@/components/admin/CampaignsManager";
import { TopProductsRankings, TopProductItem } from "@/components/admin/TopProductsRankings";
import { OrderStatusBreakdown } from "@/components/admin/OrderStatusBreakdown";
import { AnalyticsToolbar } from "@/components/admin/AnalyticsToolbar";
import {
  LayoutDashboard,
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
  Menu,
  Languages,
  X,
  KeyRound,
  QrCode,
  AlertOctagon,
} from "lucide-react";
import { adminApi, PlatformAnalytics, MasterProduct } from "@/lib/api/admin";

export default function SuperAdminDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isOnboardOpen, setIsOnboardOpen] = useState(false);
  const [showGovernanceModal, setShowGovernanceModal] = useState(false);
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
  const [lang, setLang] = useState<"en" | "hi">("en");

  useEffect(() => {
    const saved = localStorage.getItem("super_admin_language") as "en" | "hi" | null;
    if (saved === "hi" || saved === "en") setLang(saved);

    const onStorageChange = () => {
      const current = localStorage.getItem("super_admin_language") as "en" | "hi" | null;
      if (current === "hi" || current === "en") setLang(current);
    };
    window.addEventListener("admin-lang-changed", onStorageChange);
    return () => window.removeEventListener("admin-lang-changed", onStorageChange);
  }, []);

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

  const toggleLanguage = () => {
    const next = lang === "hi" ? "en" : "hi";
    setLang(next);
    localStorage.setItem("super_admin_language", next);
    window.dispatchEvent(new Event("admin-lang-changed"));
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
      if (catalogData) {
        if (Array.isArray(catalogData)) {
          setMasterProducts(catalogData);
        } else if (Array.isArray(catalogData.results)) {
          setMasterProducts(catalogData.results);
        }
      }
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
    setActiveTab(tabId);
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

  const realizedSales = analytics?.sales?.realized_sales
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
    <div className="bg-[#F6F0E6] min-h-screen text-[#17251e] font-sans antialiased">

      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        merchantCount={merchants.length}
        catalogCount={masterProducts.length}
        campaignCount={campaigns.length}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* Main Content Viewport */}
      <div className="lg:pl-[240px] flex flex-col min-h-screen w-full max-w-full min-w-0 overflow-x-hidden">
        {/* Top Global Navbar (Matching Merchant Portal Header) */}
        <header className="sticky top-0 z-30 flex h-[70px] items-center justify-between border-b border-[#ddd6ca] bg-white/80 px-4 backdrop-blur md:px-8 w-full max-w-full min-w-0">
          <div className="flex items-center gap-3">
            <button
              className="rounded-lg p-2 text-[#5e665f] hover:bg-[#eee9df] lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div>
              <h2 className="font-display font-bold text-lg md:text-xl text-[#123324] leading-tight">
                Dukandaar Super Admin Console
              </h2>
              <p className="text-[11px] text-[#6d756f]">
                {lang === "hi" ? "प्लेटफॉर्म नेटवर्क • सभी दुकानदार" : "Platform Network • All Tenants"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Language Switcher */}
            <button
              onClick={toggleLanguage}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#ddd6ca] bg-white hover:bg-[#eee9df] text-xs font-semibold text-[#123324] transition shadow-2xs"
              title="Switch Language / भाषा बदलें"
            >
              <Languages size={14} className="text-[#1F5D42]" />
              <span>{lang === "hi" ? "English" : "हिंदी"}</span>
            </button>

            <div className="flex items-center gap-2 pl-2 border-l border-[#ddd6ca]">
              <div className="grid h-8 w-8 place-items-center rounded-full bg-[#1F5D42] text-xs font-bold text-white shadow-xs">
                {adminUsername.slice(0, 1).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-xs font-bold text-[#123324] leading-none">{adminUsername}</p>
                <p className="text-[10px] text-[#6d756f] mt-0.5">{lang === "hi" ? "सुपर एडमिन" : "Super Admin"}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Mobile Quick Navigation Strip (1-tap tab switching on phones) */}
        <div className="lg:hidden sticky top-[70px] z-20 bg-white/95 backdrop-blur-md border-b border-[#ddd6ca] px-3 py-2 overflow-x-auto shadow-2xs">
          <div className="flex items-center gap-1.5 shrink-0">
            {[
              { id: "overview", label: lang === "hi" ? "अवलोकन" : "Overview", icon: LayoutDashboard },
              { id: "merchants", label: lang === "hi" ? "दुकानदार" : "Tenants", count: merchants.length, icon: Store },
              { id: "catalog", label: lang === "hi" ? "कैटलॉग" : "Catalog", count: masterProducts.length, icon: Boxes },
              { id: "campaigns", label: lang === "hi" ? "अभियान" : "Campaigns", count: campaigns.length, icon: Megaphone },
              { id: "analytics", label: lang === "hi" ? "विश्लेषण" : "Analytics", icon: TrendingUp },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    isActive
                      ? "bg-[#1F5D42] text-white shadow-xs"
                      : "bg-[#FAF8F3] text-[#123324] border border-[#ddd6ca] hover:bg-[#e7f2eb]"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#E8A33D]" : "text-[#1F5D42]"}`} />
                  <span>{tab.label}</span>
                  {tab.count !== undefined && (
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                        isActive ? "bg-[#123324] text-[#E8A33D]" : "bg-black/5 text-[#6d756f]"
                      }`}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <main className="flex-1 p-3 sm:p-6 min-h-screen w-full max-w-full min-w-0 overflow-x-hidden">
          <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6 w-full max-w-full min-w-0">
            {/* Header Title Section */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 pb-3 sm:pb-4 border-b border-[#ddd6ca] bg-[#FFFDF8] p-3.5 sm:p-5 rounded-2xl border shadow-xs">
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg sm:text-xl font-bold font-display text-[#123324] tracking-tight">
                    {lang === "hi" ? "प्लेटफॉर्म गवर्नेंस मैट्रिक्स" : "Platform Governance Matrix"}
                  </h1>
                  <span className="px-2 py-0.5 rounded-full text-[9px] sm:text-[10px] font-bold bg-[#e7f2eb] text-[#1F5D42] tracking-wider uppercase border border-[#cbe1d5]">
                    {activeTab}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
                  <p className="text-[11px] sm:text-xs text-[#6d756f]">
                    {lang === "hi" ? "लॉगिन किया गया: " : "Logged in as "}
                    <strong className="text-[#123324] font-semibold">{adminUsername}</strong> ({lang === "hi" ? "सुपर एडमिन" : "Super Admin"})
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={() => setShowGovernanceModal(true)}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2 sm:py-1.5 bg-white border border-[#ddd6ca] text-[#123324] text-xs font-semibold rounded-xl hover:bg-[#FAF8F3] shadow-xs transition-all cursor-pointer w-full sm:w-auto"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-[#1F5D42]" />
                  <span>{lang === "hi" ? "सुरक्षा नीति व गाइड" : "Governance Policy"}</span>
                </button>
                <button
                  onClick={() => setIsOnboardOpen(true)}
                  className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 sm:py-1.5 bg-[#1F5D42] text-white text-xs font-bold rounded-xl hover:bg-[#123324] shadow-xs transition-all cursor-pointer w-full sm:w-auto"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>{lang === "hi" ? "+ नया दुकानदार जोड़ें" : "+ Onboard New Merchant"}</span>
                </button>
              </div>
            </div>

            {/* TAB 1: NETWORK OVERVIEW (Executive summary, uncluttered) */}
            {activeTab === "overview" && (
              <div className="space-y-4 sm:space-y-6">
                {/* KPI Metric Cards (2-column on mobile, 4-column on desktop) */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4">
                  <MetricCard
                    title={`${scopePrefix} Sales`}
                    value={realizedSales}
                    contextText={avgOrderText}
                    icon={IndianRupee}
                    accentColor="green"
                  />
                  <MetricCard
                    title="Active Shops"
                    value={`${activeShops} / ${totalShops}`}
                    contextText="Network Health"
                    icon={Store}
                    accentColor="emerald"
                  />
                  <MetricCard
                    title={`Total Orders (${activePeriodLabel})`}
                    value={ordersTotal.toLocaleString("en-IN")}
                    contextText={`${analytics?.orders?.completed_orders ?? 0} done`}
                    icon={Receipt}
                    accentColor="slate"
                  />
                  <MetricCard
                    title="Stock-Out Alerts"
                    value={`${outOfStock} SKUs`}
                    contextText="Zero Stock"
                    icon={AlertTriangle}
                    accentColor="amber"
                  />
                </div>

                {/* 2-Column Summary Cards */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                  {/* Registered Tenants Preview */}
                  <div className="bg-white border border-[#ddd6ca] rounded-2xl p-4 sm:p-5 shadow-xs">
                    <div className="flex items-center justify-between pb-3 border-b border-[#eee9df]">
                      <div className="flex items-center gap-2">
                        <Store className="w-4 h-4 text-[#1F5D42]" />
                        <h3 className="text-xs sm:text-sm font-bold text-[#123324]">Tenant Directory Snapshot</h3>
                      </div>
                      <button
                        onClick={() => setActiveTab("merchants")}
                        className="text-xs font-semibold text-[#1F5D42] hover:underline"
                      >
                        View All {merchants.length} Tenants →
                      </button>
                    </div>
                    <div className="mt-3.5 space-y-2">
                      {merchants.length === 0 ? (
                        <div className="py-6 text-center text-xs text-[#869088]">
                          No merchants onboarded yet. Use the Onboard button above to add one.
                        </div>
                      ) : (
                        merchants.slice(0, 4).map((m) => (
                          <div
                            key={m.id}
                            className="flex items-center justify-between p-2.5 sm:p-3 rounded-xl bg-[#FAF8F3] border border-[#eee9df] hover:border-[#ddd6ca] transition-colors"
                          >
                            <div>
                              <div className="text-xs font-bold text-[#123324]">{m.shopName || m.merchantName}</div>
                              <div className="text-[11px] text-[#6d756f] font-mono">
                                Mobile: {m.mobileNumber} | {m.city || "Urban Node"}
                              </div>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${m.status === "ACTIVE"
                                ? "bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5]"
                                : "bg-amber-100 text-amber-800 border border-amber-200"
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
                  <div className="bg-white border border-[#ddd6ca] rounded-2xl p-4 sm:p-5 shadow-xs">
                    <div className="flex items-center justify-between pb-3 border-b border-[#eee9df]">
                      <div className="flex items-center gap-2">
                        <Boxes className="w-4 h-4 text-[#1F5D42]" />
                        <h3 className="text-xs sm:text-sm font-bold text-[#123324]">Master Catalog Snapshot</h3>
                      </div>
                      <button
                        onClick={() => setActiveTab("catalog")}
                        className="text-xs font-semibold text-[#1F5D42] hover:underline"
                      >
                        View All {masterProducts.length} SKUs →
                      </button>
                    </div>
                    <div className="mt-3.5 space-y-2">
                      {masterProducts.length === 0 ? (
                        <div className="py-6 text-center text-xs text-[#869088]">
                          No master catalog products found.
                        </div>
                      ) : (
                        masterProducts.slice(0, 4).map((p) => (
                          <div
                            key={p.id}
                            className="flex items-center justify-between p-2.5 sm:p-3 rounded-xl bg-[#FAF8F3] border border-[#eee9df]"
                          >
                            <div>
                              <div className="text-xs font-bold text-[#123324]">{p.name}</div>
                              <div className="text-[11px] text-[#6d756f]">
                                Brand: {p.brand || "Generic"} | {p.category_name || "General"}
                              </div>
                            </div>
                            <div className="text-right text-xs font-semibold text-[#1F5D42]">
                              {p.is_verified ? "Verified SKU" : "Standard"}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* Quick Navigation Panels */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
                  <div
                    onClick={() => setActiveTab("merchants")}
                    className="bg-white border border-[#ddd6ca] hover:border-[#1F5D42] p-4 rounded-2xl cursor-pointer transition-all shadow-xs group"
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
                    className="bg-white border border-[#ddd6ca] hover:border-[#1F5D42] p-4 rounded-2xl cursor-pointer transition-all shadow-xs group"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Boxes className="w-5 h-5 text-[#1F5D42]" />
                      <span className="text-xs font-bold text-[#869088] group-hover:text-[#1F5D42]">
                        {masterProducts.length} Items →
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-[#123324]">Master Catalog</h4>
                    <p className="text-[11px] text-[#6d756f] mt-1">
                      Universal barcode registry and categories.
                    </p>
                  </div>

                  <div
                    onClick={() => setActiveTab("campaigns")}
                    className="bg-white border border-[#ddd6ca] hover:border-[#1F5D42] p-4 rounded-2xl cursor-pointer transition-all shadow-xs group"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Megaphone className="w-5 h-5 text-[#1F5D42]" />
                      <span className="text-xs font-bold text-[#869088] group-hover:text-[#1F5D42]">
                        {campaigns.length} Active →
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-[#123324]">Marketing Campaigns</h4>
                    <p className="text-[11px] text-[#6d756f] mt-1">
                      Launch platform-wide banners, announcements, and storefront campaigns.
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
              />
            )}

            {/* TAB 4: MARKETING CAMPAIGNS (Exclusive dedicated view) */}
            {activeTab === "campaigns" && (
              <CampaignsManager
                campaigns={campaigns}
                merchants={merchants}
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

                {/* 5 KPI Metric Cards (2-column on mobile, 5-column on desktop) */}
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-2.5 sm:gap-4">
                  <MetricCard
                    title={`${scopePrefix} Sales`}
                    value={realizedSales}
                    contextText={avgOrderText}
                    icon={IndianRupee}
                    accentColor="green"
                  />
                  <MetricCard
                    title={currentFilteredShop ? "Tenant Status" : "Active Nodes"}
                    value={currentFilteredShop ? currentFilteredShop.status : `${activeShops} / ${totalShops}`}
                    contextText={currentFilteredShop ? (currentFilteredShop.city || "Single Tenant") : "Platform Coverage"}
                    icon={Store}
                    accentColor="emerald"
                  />
                  <MetricCard
                    title={`Orders (${activePeriodLabel})`}
                    value={ordersTotal.toLocaleString("en-IN")}
                    contextText={`${analytics?.orders?.completed_orders ?? 0} done`}
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
                  <div className="col-span-2 lg:col-span-1">
                    <MetricCard
                      title="Stock-Out Alerts"
                      value={`${outOfStock} SKUs`}
                      contextText="Zero Available Stock"
                      icon={AlertTriangle}
                      accentColor="amber"
                    />
                  </div>
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
                              className={`p-3 rounded border flex items-center justify-between ${selectedShopId === s.shop_id
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
      </div>

      {/* Onboard Merchant Slide-Over Modal */}
      <OnboardMerchantModal
        isOpen={isOnboardOpen}
        onClose={() => setIsOnboardOpen(false)}
        onSuccess={() => {
          loadData();
          setIsOnboardOpen(false);
        }}
      />

      {/* Governance & Policy Modal */}
      {showGovernanceModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-[#ddd6ca] shadow-2xl p-6 sm:p-7">
            <div className="flex items-start justify-between pb-4 border-b border-[#eee8df] mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-[#e7f2eb] border border-[#cbe1d5] flex items-center justify-center text-[#1F5D42]">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#123324] font-display">
                    {lang === "hi" ? "सुपर एडमिन सुरक्षा व गवर्नेंस गाइड" : "Super Admin Governance & Security Policy"}
                  </h3>
                  <p className="text-xs text-[#6d756f]">
                    {lang === "hi"
                      ? "मल्टी-टेनेंट सुरक्षा, यूआरएल रोटेशन और क्रेडेंशियल्स प्रबंधन नियम"
                      : "Multi-tenant tenant isolation, URL rotation rules, and credential policies"}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowGovernanceModal(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-[#6d756f] hover:bg-[#FAF8F3] hover:text-[#123324] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Policy 1: QR & Slug Rotation */}
              <div className="p-4 rounded-xl bg-[#FAF8F3] border border-[#eee8df]">
                <div className="flex items-center gap-2 mb-1.5">
                  <QrCode className="w-4 h-4 text-[#1F5D42]" />
                  <h4 className="text-sm font-bold text-[#123324]">
                    {lang === "hi" ? "1. स्लग व क्यूआर कोड रोटेशन (Slug & QR Rotation)" : "1. Slug & QR Code Rotation Policy"}
                  </h4>
                </div>
                <p className="text-xs text-[#4a554f] leading-relaxed">
                  {lang === "hi"
                    ? "दुकान का सार्वजनिक स्लग बदलने से ग्राहक का वेब यूआरएल बदल जाता है। दुकान पर पहले से लगे पुराने प्रिंटेड क्यूआर (QR) कोड काम करना बंद कर देंगे। स्लग अपडेट करने के बाद नया क्यूआर कोड प्रिंट करके काउंटर पर लगाना अनिवार्य है।"
                    : "Changing a shop's public slug alters its customer-facing storefront URL. Previously printed physical QR stickers will break immediately. Always inform the merchant to print and paste the updated QR code on their storefront."}
                </p>
              </div>

              {/* Policy 2: Password Reset */}
              <div className="p-4 rounded-xl bg-[#FAF8F3] border border-[#eee8df]">
                <div className="flex items-center gap-2 mb-1.5">
                  <KeyRound className="w-4 h-4 text-amber-700" />
                  <h4 className="text-sm font-bold text-[#123324]">
                    {lang === "hi" ? "2. पासवर्ड रीसेट व सुरक्षा नीति (Password Policy)" : "2. Password Reset & Verification"}
                  </h4>
                </div>
                <p className="text-xs text-[#4a554f] leading-relaxed">
                  {lang === "hi"
                    ? "मल्टी-टेनेंट सुरक्षा बनाए रखने के लिए दुकानदार स्वयं ओटीपी से पासवर्ड रीसेट नहीं कर सकते। सुपर एडमिन द्वारा जारी किया गया अस्थायी पासवर्ड केवल पहले लॉगिन के लिए होता है। दुकानदार को लॉगिन करते ही अपना नया स्थायी पासवर्ड सेट करना आवश्यक है।"
                    : "To prevent multi-tenant credential takeover, self-serve OTP reset is disabled for merchants. Temporary passwords issued by Super Admin are single-use tokens; merchants are forced to create a strong permanent password immediately on first sign-in."}
                </p>
              </div>

              {/* Policy 3: Shop Deactivation vs Deletion */}
              <div className="p-4 rounded-xl bg-[#FAF8F3] border border-[#eee8df]">
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertOctagon className="w-4 h-4 text-red-600" />
                  <h4 className="text-sm font-bold text-[#123324]">
                    {lang === "hi" ? "3. दुकान निष्क्रियता बनाम स्थायी विलोपन (Deactivation vs Deletion)" : "3. Shop Deactivation vs Deletion"}
                  </h4>
                </div>
                <p className="text-xs text-[#4a554f] leading-relaxed">
                  {lang === "hi"
                    ? "दुकान को 'निष्क्रिय (Deactivate)' करने से स्टोर ग्राहक के लिए बंद हो जाता है, परंतु दुकानदार के पिछले ऑर्डर्स, बिक्री और बहीखाता सुरक्षित रहते हैं। 'हटाएं (Delete)' करने पर दुकान और उसके सभी डेटा स्थायी रूप से नष्ट हो जाते हैं (अपरिवर्तनीय)।"
                    : "Deactivating a shop temporarily closes the customer storefront while safely preserving all historical order ledgers, audit records, and billing data. Deleting a shop permanently and irreversibly purges the tenant database record."}
                </p>
              </div>

              {/* Policy 4: Strict Tenant Isolation */}
              <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/80">
                <div className="flex items-center gap-2 mb-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-800" />
                  <h4 className="text-sm font-bold text-emerald-950">
                    {lang === "hi" ? "4. मल्टी-टेनेंट डेटा सुरक्षा (Tenant Data Isolation)" : "4. Strict Tenant Boundary Isolation"}
                  </h4>
                </div>
                <p className="text-xs text-emerald-900/90 leading-relaxed">
                  {lang === "hi"
                    ? "प्रत्येक दुकानदार का स्टॉक, बिक्री मूल्य (Selling Price), एमआरपी और ग्राहक ऑर्डर पूर्णतः सुरक्षित और पृथक (isolated) हैं। कोई भी दुकानदार अन्य दुकान का डेटा न तो देख सकता है और न ही संशोधित कर सकता है।"
                    : "Every merchant's catalog pricing, inventory quantities, customer order ledger, and phone records are strictly isolated. No merchant can access or modify another tenant's store data."}
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-[#eee8df] flex justify-end">
              <button
                type="button"
                onClick={() => setShowGovernanceModal(false)}
                className="px-4 py-2 bg-[#1F5D42] text-white text-xs font-bold rounded-xl hover:bg-[#123324] transition-colors cursor-pointer"
              >
                {lang === "hi" ? "समझ गया / बंद करें" : "Understood / Close"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
