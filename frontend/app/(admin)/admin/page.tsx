"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/admin/Navbar";
import { Sidebar } from "@/components/admin/Sidebar";
import { MetricCard } from "@/components/admin/MetricCard";
import { OnboardMerchantModal } from "@/components/admin/OnboardMerchantModal";
import { MerchantTable, MerchantShopItem } from "@/components/admin/MerchantTable";
import { MasterCatalogTable } from "@/components/admin/MasterCatalogTable";
import { CampaignsManager, CampaignItem } from "@/components/admin/CampaignsManager";
import { TopProductsRankings, TopProductItem } from "@/components/admin/TopProductsRankings";
import { SecurityRecoveryModal } from "@/components/admin/SecurityRecoveryModal";
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
} from "lucide-react";
import { adminApi, PlatformAnalytics, MasterProduct } from "@/lib/api/admin";

export default function SuperAdminDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [isOnboardOpen, setIsOnboardOpen] = useState(false);
  const [isSecurityOpen, setIsSecurityOpen] = useState(false);
  const [analytics, setAnalytics] = useState<PlatformAnalytics | null>(null);
  const [masterProducts, setMasterProducts] = useState<MasterProduct[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [topProducts, setTopProducts] = useState<TopProductItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Demo fallback merchants if backend database is in dev initial state
  const [merchants, setMerchants] = useState<MerchantShopItem[]>([
    {
      id: 1,
      shopId: 1,
      shopName: "Fresh Grocer Bengaluru",
      merchantName: "fresh_grocer_merchant",
      mobileNumber: "+91 98880 00001",
      city: "Bengaluru, 560038",
      status: "ACTIVE",
      catalogItemsCount: 42,
      monthlyVolume: "₹1,49,200",
      publicSlug: "f4356ecdbbd6",
    },
    {
      id: 2,
      shopId: 2,
      shopName: "Mahalaxmi Super Market",
      merchantName: "mahalaxmi_admin",
      mobileNumber: "+91 98201 44521",
      city: "Mumbai, 400053",
      status: "ACTIVE",
      catalogItemsCount: 84,
      monthlyVolume: "₹2,21,500",
      publicSlug: "a18290bc91fe",
    },
    {
      id: 3,
      shopId: 3,
      shopName: "Gupta Daily Provisions",
      merchantName: "gupta_kirana",
      mobileNumber: "+91 99100 81290",
      city: "Delhi NCR, 110024",
      status: "PENDING_PASSWORD_CHANGE",
      catalogItemsCount: 18,
      monthlyVolume: "₹42,000",
      publicSlug: "b98210fe91ca",
    },
  ]);

  const loadData = async () => {
    try {
      const [analyticsData, catalogData, campaignsData, topProductsData] = await Promise.all([
        adminApi.getAnalytics().catch(() => null),
        adminApi.listMasterProducts().catch(() => ({ results: [] })),
        adminApi.listCampaigns().catch(() => []),
        adminApi.getTopProducts().catch(() => ({ top_products: [] })),
      ]);
      if (analyticsData) setAnalytics(analyticsData);
      if (catalogData && catalogData.results) setMasterProducts(catalogData.results);
      if (Array.isArray(campaignsData)) setCampaigns(campaignsData);
      if (topProductsData && topProductsData.top_products) setTopProducts(topProductsData.top_products);
    } catch {
      // Resilient fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
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
  const gmv = analytics?.sales?.realized_sales
    ? `₹${parseFloat(analytics.sales.realized_sales).toLocaleString("en-IN")}`
    : "₹1,48,920";
  const activeShops = analytics?.shops?.active_shops ?? merchants.length;
  const totalShops = analytics?.shops?.total_shops ?? merchants.length;
  const ordersToday = analytics?.orders?.total_orders ?? 142;
  const outOfStock = analytics?.inventory?.out_of_stock_items_count ?? 12;

  return (
    <div className="bg-slate-50 min-h-screen text-slate-900 font-sans antialiased">
      {/* Top Navbar */}
      <Navbar />

      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onOpenOnboard={() => setIsOnboardOpen(true)}
        merchantCount={merchants.length}
        catalogCount={masterProducts.length || 24}
        campaignCount={campaigns.length || 2}
      />

      {/* Main Content Viewport */}
      <main className="ml-64 mt-14 p-6 min-h-[calc(100vh-3.5rem)]">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header Title Section */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  Platform Governance Matrix
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700 tracking-wider uppercase">
                  {activeTab === "overview" ? "Pan-India Operations" : activeTab}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Multi-tenant telemetry, live SKU curation, campaigns, and merchant security administration.
              </p>
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
                onClick={() => setIsOnboardOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1F5D42] text-white text-xs font-semibold rounded hover:bg-[#164430] shadow-sm transition-all"
              >
                Onboard New Merchant
              </button>
            </div>
          </div>

          {/* KPI Metric Cards (Shown in Overview & Analytics tabs) */}
          {(activeTab === "overview" || activeTab === "analytics") && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Platform GMV (Today)"
                value={gmv}
                delta="+14.2%"
                isPositive={true}
                contextText="Realized Sales"
                icon={IndianRupee}
                accentColor="green"
              />
              <MetricCard
                title="Total Active Shops"
                value={`${activeShops} / ${totalShops}`}
                delta="95.8%"
                isPositive={true}
                contextText="Network Health"
                icon={Store}
                accentColor="emerald"
              />
              <MetricCard
                title="Completed Orders"
                value={ordersToday.toLocaleString("en-IN")}
                delta="+8.4%"
                isPositive={true}
                contextText="Avg Order ₹348"
                icon={Receipt}
                accentColor="slate"
              />
              <MetricCard
                title="Stock-Out Alerts"
                value={`${outOfStock} SKUs`}
                delta="-2.1%"
                isPositive={false}
                contextText="Action required"
                icon={AlertTriangle}
                accentColor="amber"
              />
            </div>
          )}

          {/* Top Performing Shops & Products (Shown in Overview & Analytics tabs) */}
          {(activeTab === "overview" || activeTab === "analytics") && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Shops Leaderboard */}
              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
                  <div className="flex items-center gap-2">
                    <Trophy className="w-4 h-4 text-amber-500" />
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Top Performing Merchant Nodes
                    </h3>
                  </div>
                  <span className="text-[11px] text-slate-400">Ranked by Realized Volume</span>
                </div>
                <div className="space-y-2.5">
                  {(analytics?.top_shops && analytics.top_shops.length > 0
                    ? analytics.top_shops.slice(0, 3)
                    : [
                        { shop_id: 1, shop_name: "Fresh Grocer Bengaluru", completed_orders: 86, realized_sales: "64200.00" },
                        { shop_id: 2, shop_name: "Mahalaxmi Super Market", completed_orders: 54, realized_sales: "48150.00" },
                        { shop_id: 3, shop_name: "Gupta Daily Provisions", completed_orders: 38, realized_sales: "29400.00" },
                      ]
                  ).map((s, idx) => (
                    <div
                      key={s.shop_id}
                      className="p-3 rounded border border-slate-100 bg-slate-50/50 flex items-center justify-between"
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
                        <span className="text-[10px] text-emerald-700 font-semibold flex items-center gap-0.5 justify-end">
                          <TrendingUp className="w-3 h-3" /> Top 5%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Products Rankings */}
              <TopProductsRankings products={topProducts} />
            </div>
          )}

          {/* Tenant Directory Section (Shown in Overview & Merchants tabs) */}
          {(activeTab === "overview" || activeTab === "merchants") && (
            <MerchantTable
              merchants={merchants}
              onRefresh={loadData}
            />
          )}

          {/* Master Product Catalog Curation (Shown in Overview & Catalog tabs) */}
          {(activeTab === "overview" || activeTab === "catalog") && (
            <MasterCatalogTable
              products={masterProducts}
              onRefresh={loadData}
            />
          )}

          {/* Marketing Campaigns (Shown in Overview & Campaigns tabs) */}
          {(activeTab === "overview" || activeTab === "campaigns") && (
            <CampaignsManager
              campaigns={campaigns}
              onRefresh={loadData}
            />
          )}
        </div>
      </main>

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
