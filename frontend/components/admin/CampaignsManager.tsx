"use client";

import React, { useState, useMemo } from "react";
import {
  Megaphone,
  Plus,
  Calendar,
  Store,
  CheckCircle2,
  Play,
  Square,
  Trash2,
  AlertCircle,
  Search,
  CheckSquare,
  Square as UncheckedSquare,
  Clock,
  Layers,
  Upload,
  Image as ImageIcon,
  X,
  Pencil,
} from "lucide-react";
import { adminApi, CampaignItem } from "@/lib/api/admin";
import { MerchantShopItem } from "@/components/admin/MerchantTable";

// Re-export for any consumers that imported CampaignItem from here
export type { CampaignItem };

interface CampaignsManagerProps {
  campaigns?: CampaignItem[];
  merchants?: MerchantShopItem[];
  onRefresh?: () => void;
}

export function CampaignsManager({
  campaigns = [],
  merchants = [],
  onRefresh,
}: CampaignsManagerProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<CampaignItem | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);
  const bannerInputRef = React.useRef<HTMLInputElement>(null);
  const [shopScope, setShopScope] = useState<"ALL_SHOPS" | "SELECTED_SHOPS">("ALL_SHOPS");
  const [selectedShops, setSelectedShops] = useState<number[]>([]);
  const [shopSearch, setShopSearch] = useState("");
  const [startsAt, setStartsAt] = useState(
    new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  );
  const [endsAt, setEndsAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleOpenCreate = () => {
    setEditingCampaign(null);
    setTitle("");
    setContent("");
    setBannerPreview(null);
    setShopScope("ALL_SHOPS");
    setSelectedShops([]);
    setStartsAt(
      new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    );
    setEndsAt("");
    setActionError(null);
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (c: CampaignItem) => {
    setEditingCampaign(c);
    setTitle(c.title || "");

    let textContent = c.content || "";
    let imgPreview: string | null = null;
    if (c.content && c.content.trim().startsWith("{") && c.content.includes('"image"')) {
      try {
        const parsed = JSON.parse(c.content);
        textContent = parsed.text || "";
        imgPreview = parsed.image || null;
      } catch {
        // Plain text fallback
      }
    }
    setContent(textContent);
    setBannerPreview(imgPreview);
    setShopScope(c.shop_scope as "ALL_SHOPS" | "SELECTED_SHOPS");
    setSelectedShops(c.selected_shops || []);

    if (c.starts_at) {
      setStartsAt(new Date(c.starts_at).toISOString().slice(0, 16));
    } else {
      setStartsAt("");
    }
    if (c.ends_at) {
      setEndsAt(new Date(c.ends_at).toISOString().slice(0, 16));
    } else {
      setEndsAt("");
    }
    setActionError(null);
    setIsCreateOpen(true);
  };

  const handleBannerSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setBannerPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  // Filter available merchants for target shop selection
  const filteredMerchants = useMemo(() => {
    const activeWithShops = merchants.filter((m) => m.shopId > 0);
    if (!shopSearch.trim()) return activeWithShops;
    const q = shopSearch.toLowerCase();
    return activeWithShops.filter(
      (m) =>
        m.shopName.toLowerCase().includes(q) ||
        m.publicSlug.toLowerCase().includes(q) ||
        m.city.toLowerCase().includes(q)
    );
  }, [merchants, shopSearch]);

  const toggleShop = (shopId: number) => {
    setSelectedShops((prev) =>
      prev.includes(shopId) ? prev.filter((id) => id !== shopId) : [...prev, shopId]
    );
  };

  const selectAllFiltered = () => {
    const ids = filteredMerchants.map((m) => m.shopId);
    setSelectedShops((prev) => Array.from(new Set([...prev, ...ids])));
  };

  const deselectAllFiltered = () => {
    const ids = new Set(filteredMerchants.map((m) => m.shopId));
    setSelectedShops((prev) => prev.filter((id) => !ids.has(id)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);

    if (!title.trim()) {
      setActionError("Campaign title is required.");
      return;
    }

    if (shopScope === "SELECTED_SHOPS" && selectedShops.length === 0) {
      setActionError("Please select at least one shop for a targeted campaign.");
      return;
    }

    if (startsAt && endsAt && new Date(startsAt) > new Date(endsAt)) {
      setActionError("End time must be after the start time.");
      return;
    }

    setSubmitting(true);
    try {
      let finalContent = content.trim();
      if (bannerPreview) {
        finalContent = JSON.stringify({
          text: content.trim(),
          image: bannerPreview,
        });
      }

      const payload = {
        title: title.trim(),
        content: finalContent || undefined,
        shop_scope: shopScope,
        selected_shops: shopScope === "SELECTED_SHOPS" ? selectedShops : [],
        starts_at: startsAt ? new Date(startsAt).toISOString() : null,
        ends_at: endsAt ? new Date(endsAt).toISOString() : null,
      };

      if (editingCampaign) {
        await adminApi.updateCampaign(editingCampaign.id, payload);
      } else {
        await adminApi.createCampaign(payload);
      }

      setIsCreateOpen(false);
      setEditingCampaign(null);
      setTitle("");
      setContent("");
      setBannerPreview(null);
      setShopScope("ALL_SHOPS");
      setSelectedShops([]);
      setEndsAt("");
      if (onRefresh) onRefresh();
    } catch (err: any) {
      const msg =
        err?.response?.data?.selected_shops?.[0] ||
        err?.response?.data?.ends_at?.[0] ||
        err?.response?.data?.title?.[0] ||
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        "Failed to save campaign. Verify Super Admin authorization.";
      setActionError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleActivate = async (id: number) => {
    try {
      setActionError(null);
      await adminApi.activateCampaign(id);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setActionError(err?.response?.data?.error || "Could not activate campaign.");
    }
  };

  const handleEnd = async (id: number) => {
    try {
      setActionError(null);
      await adminApi.endCampaign(id);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setActionError(err?.response?.data?.error || "Could not end campaign.");
    }
  };

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete campaign "${title}"?`)) return;
    try {
      setActionError(null);
      await adminApi.deleteCampaign(id);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setActionError(err?.response?.data?.error || "Could not delete campaign.");
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Megaphone className="w-4 h-4 text-[#1F5D42]" />
            <h2 className="text-sm font-bold text-slate-900 tracking-tight">
              Network Marketing Campaigns
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Storefront announcements and banner campaigns across merchant shops.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1F5D42] text-white text-xs font-semibold rounded-lg hover:bg-[#164430] transition-colors shadow-2xs"
        >
          <Plus className="w-3.5 h-3.5" />
          Create Campaign
        </button>
      </div>

      {actionError && (
        <div className="mx-4 mt-3 p-2.5 bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-amber-600 hover:text-amber-800 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Mobile Card View (Zero horizontal scroll on phones) */}
      <div className="block sm:hidden divide-y divide-slate-100">
        {campaigns.length === 0 ? (
          <div className="py-10 text-center text-slate-400 text-xs px-4">
            <Megaphone className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-600">No campaigns created yet</p>
            <p className="text-[11px] text-slate-400 mt-1">
              Create platform-wide or shop-specific announcement banners to showcase on storefronts.
            </p>
          </div>
        ) : (
          campaigns.map((c) => (
            <div key={c.id} className="p-3.5 bg-white space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h4 className="font-semibold text-slate-900 text-xs leading-snug">{c.title}</h4>
                  {c.content && (
                    <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">{c.content}</p>
                  )}
                </div>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${
                    c.status === "ACTIVE"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                      : c.status === "DRAFT"
                      ? "bg-slate-100 text-slate-700 border border-slate-200"
                      : "bg-rose-100 text-rose-800 border border-rose-200"
                  }`}
                >
                  {c.status}
                </span>
              </div>

              <div className="flex items-center gap-2 flex-wrap text-[11px]">
                {c.shop_scope === "ALL_SHOPS" ? (
                  <span className="inline-flex items-center gap-1 font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px]">
                    <Layers className="w-3 h-3 text-emerald-600" />
                    All Shops
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 font-semibold text-indigo-800 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full text-[10px]">
                    <Store className="w-3 h-3 text-indigo-600" />
                    {c.selected_shops?.length ?? 0} Shops
                  </span>
                )}

                <div className="flex items-center gap-1 text-slate-500 text-[10px]">
                  <Calendar className="w-3 h-3 text-slate-400 shrink-0" />
                  <span>
                    {c.starts_at ? new Date(c.starts_at).toLocaleDateString("en-IN") : "Immediate"}
                    {c.ends_at && ` → ${new Date(c.ends_at).toLocaleDateString("en-IN")}`}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-100">
                <button
                  onClick={() => handleOpenEdit(c)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-50 hover:bg-[#e7f2eb] border border-slate-200 text-[#1F5D42] rounded text-[11px] font-semibold transition-colors"
                  title="Edit Campaign"
                >
                  <Pencil className="w-3 h-3 text-[#1F5D42]" />
                  Edit
                </button>
                {c.status === "DRAFT" && (
                  <button
                    onClick={() => handleActivate(c.id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-600 text-white rounded text-[11px] font-semibold hover:bg-emerald-700"
                  >
                    <Play className="w-3 h-3" />
                    Activate
                  </button>
                )}
                {c.status === "ACTIVE" && (
                  <button
                    onClick={() => handleEnd(c.id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-700 text-white rounded text-[11px] font-semibold hover:bg-slate-800"
                  >
                    <Square className="w-3 h-3" />
                    End
                  </button>
                )}
                <button
                  onClick={() => handleDelete(c.id, c.title)}
                  className="inline-flex items-center p-1 text-slate-400 hover:text-rose-600 rounded"
                  title="Delete Campaign"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Desktop Table View */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#FAF7F2] border-b border-[#E8E2D9] text-slate-600 uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="py-2.5 px-4">Campaign & Announcement</th>
              <th className="py-2.5 px-4">Target Scope</th>
              <th className="py-2.5 px-4">Status</th>
              <th className="py-2.5 px-4">Schedule</th>
              <th className="py-2.5 px-4 text-right">Lifecycle Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {campaigns.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-400 text-xs">
                  <div className="max-w-xs mx-auto space-y-2">
                    <Megaphone className="w-8 h-8 text-slate-300 mx-auto" />
                    <p className="font-semibold text-slate-600">No campaigns created yet</p>
                    <p className="text-[11px] text-slate-400">
                      Create platform-wide or shop-specific announcement banners to showcase on storefronts.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              campaigns.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                  {/* Campaign Title & Content */}
                  <td className="py-3 px-4 max-w-xs">
                    <div className="font-semibold text-slate-900 text-xs">{c.title}</div>
                    {c.content ? (
                      <div className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">
                        {c.content}
                      </div>
                    ) : (
                      <div className="text-[10px] text-slate-400 italic mt-0.5">
                        No announcement text
                      </div>
                    )}
                  </td>

                  {/* Target Scope */}
                  <td className="py-3 px-4">
                    {c.shop_scope === "ALL_SHOPS" ? (
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px]">
                        <Layers className="w-3 h-3 text-emerald-600" />
                        All Shops (Platform)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 font-semibold text-indigo-800 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full text-[10px]">
                        <Store className="w-3 h-3 text-indigo-600" />
                        {c.selected_shops?.length ?? 0} Selected Shops
                      </span>
                    )}
                  </td>

                  {/* Status Badge */}
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        c.status === "ACTIVE"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                          : c.status === "DRAFT"
                          ? "bg-slate-100 text-slate-700 border border-slate-200"
                          : "bg-rose-100 text-rose-800 border border-rose-200"
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>

                  {/* Schedule */}
                  <td className="py-3 px-4 text-slate-500 text-[11px]">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <div>
                        {c.starts_at ? (
                          <span>{new Date(c.starts_at).toLocaleDateString("en-IN")}</span>
                        ) : (
                          <span className="text-slate-400">Immediate</span>
                        )}
                        {c.ends_at && (
                          <span className="text-slate-600">
                            {" "}
                            → {new Date(c.ends_at).toLocaleDateString("en-IN")}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Lifecycle Actions */}
                  <td className="py-3 px-4 text-right">
                    <div className="inline-flex items-center gap-1.5">
                      <button
                        onClick={() => handleOpenEdit(c)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-50 hover:bg-[#e7f2eb] border border-slate-200 text-[#1F5D42] rounded text-[11px] font-semibold transition-colors shadow-2xs"
                        title="Edit Campaign"
                      >
                        <Pencil className="w-3 h-3 text-[#1F5D42]" />
                        Edit
                      </button>
                      {c.status === "DRAFT" && (
                        <button
                          onClick={() => handleActivate(c.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-600 text-white rounded text-[11px] font-semibold hover:bg-emerald-700 transition-colors shadow-2xs"
                        >
                          <Play className="w-3 h-3" />
                          Activate
                        </button>
                      )}
                      {c.status === "ACTIVE" && (
                        <button
                          onClick={() => handleEnd(c.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-700 text-white rounded text-[11px] font-semibold hover:bg-slate-800 transition-colors shadow-2xs"
                        >
                          <Square className="w-3 h-3" />
                          End
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(c.id, c.title)}
                        className="inline-flex items-center p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                        title="Delete Campaign"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal: Create or Edit Platform Campaign */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-slate-200 p-5 space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  {editingCampaign ? "Edit Storefront Campaign" : "Create Storefront Campaign"}
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {editingCampaign
                    ? "Update announcement details, schedule dates, or shop audience."
                    : "Configure an announcement banner and target specific merchant storefronts."}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsCreateOpen(false);
                  setEditingCampaign(null);
                }}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold p-1 rounded hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3.5 text-xs overflow-y-auto pr-1">
              {/* Campaign Title */}
              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  Campaign Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Weekend Kirana Festival"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-[#1F5D42] focus:border-[#1F5D42]"
                />
              </div>

              {/* Announcement Banner Content */}
              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  Announcement Text (Displayed on Storefront Header)
                </label>
                <textarea
                  rows={2}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="e.g. Free delivery on all orders above ₹299 this weekend!"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-[#1F5D42] focus:border-[#1F5D42]"
                />
              </div>

              {/* Promotional Banner Image (Direct Upload) */}
              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  Promotional Banner Image (Optional)
                </label>
                {bannerPreview ? (
                  <div className="relative rounded-xl border border-slate-200 overflow-hidden bg-slate-50">
                    <img
                      src={bannerPreview}
                      alt="Campaign Banner Preview"
                      className="w-full max-h-36 object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setBannerPreview(null);
                        if (bannerInputRef.current) bannerInputRef.current.value = "";
                      }}
                      className="absolute top-2 right-2 p-1 rounded-full bg-red-600 text-white hover:bg-red-700 shadow-sm"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => bannerInputRef.current?.click()}
                    className="w-full py-4 px-3 border-2 border-dashed border-slate-300 hover:border-[#1F5D42] rounded-xl flex flex-col items-center justify-center text-slate-500 hover:text-[#1F5D42] bg-slate-50/50 hover:bg-[#f0f7f3]/50 transition cursor-pointer"
                  >
                    <Upload className="w-5 h-5 mb-1" />
                    <span className="text-xs font-semibold">Upload Banner Image File</span>
                    <span className="text-[10px] text-slate-400 mt-0.5">PNG, JPG, or WEBP · 16:9 or wide format recommended</span>
                  </button>
                )}
                <input
                  ref={bannerInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={handleBannerSelect}
                />
              </div>

              {/* Scope Selection */}
              <div>
                <label className="block text-slate-700 font-semibold mb-1.5">
                  Target Storefront Scope <span className="text-rose-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <label
                    className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-all ${
                      shopScope === "ALL_SHOPS"
                        ? "border-[#1F5D42] bg-[#f0f7f3]"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="shop_scope"
                      value="ALL_SHOPS"
                      checked={shopScope === "ALL_SHOPS"}
                      onChange={() => setShopScope("ALL_SHOPS")}
                      className="mt-0.5 text-[#1F5D42] focus:ring-[#1F5D42]"
                    />
                    <div>
                      <div className="font-semibold text-slate-900 text-xs">All Shops</div>
                      <div className="text-[10px] text-slate-500">
                        Broadcast to every merchant storefront across the platform
                      </div>
                    </div>
                  </label>

                  <label
                    className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-pointer transition-all ${
                      shopScope === "SELECTED_SHOPS"
                        ? "border-[#1F5D42] bg-[#f0f7f3]"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="shop_scope"
                      value="SELECTED_SHOPS"
                      checked={shopScope === "SELECTED_SHOPS"}
                      onChange={() => setShopScope("SELECTED_SHOPS")}
                      className="mt-0.5 text-[#1F5D42] focus:ring-[#1F5D42]"
                    />
                    <div>
                      <div className="font-semibold text-slate-900 text-xs">Selected Shops</div>
                      <div className="text-[10px] text-slate-500">
                        Target specific shops ({selectedShops.length} selected)
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Shop Picker (When SELECTED_SHOPS is chosen) */}
              {shopScope === "SELECTED_SHOPS" && (
                <div className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-700 text-[11px]">
                      Choose Target Merchants ({selectedShops.length} of {merchants.length} selected)
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={selectAllFiltered}
                        className="text-[10px] text-[#1F5D42] font-semibold hover:underline"
                      >
                        Select All
                      </button>
                      <span className="text-slate-300">|</span>
                      <button
                        type="button"
                        onClick={deselectAllFiltered}
                        className="text-[10px] text-slate-500 hover:underline"
                      >
                        Deselect
                      </button>
                    </div>
                  </div>

                  {/* Search Filter */}
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                    <input
                      type="text"
                      value={shopSearch}
                      onChange={(e) => setShopSearch(e.target.value)}
                      placeholder="Search shops by name, city, or slug..."
                      className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded text-xs focus:ring-1 focus:ring-[#1F5D42]"
                    />
                  </div>

                  {/* List of Shops */}
                  <div className="max-h-36 overflow-y-auto space-y-1 bg-white border border-slate-200 rounded p-1.5">
                    {filteredMerchants.length === 0 ? (
                      <div className="text-center py-4 text-[11px] text-slate-400">
                        No shops found matching "{shopSearch}"
                      </div>
                    ) : (
                      filteredMerchants.map((m) => {
                        const isSelected = selectedShops.includes(m.shopId);
                        return (
                          <div
                            key={m.shopId}
                            onClick={() => toggleShop(m.shopId)}
                            className={`flex items-center justify-between p-1.5 rounded cursor-pointer transition-colors ${
                              isSelected ? "bg-emerald-50 text-[#1F5D42]" : "hover:bg-slate-50"
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate">
                              {isSelected ? (
                                <CheckSquare className="w-4 h-4 text-[#1F5D42] shrink-0" />
                              ) : (
                                <UncheckedSquare className="w-4 h-4 text-slate-300 shrink-0" />
                              )}
                              <span className="font-semibold text-xs truncate">{m.shopName}</span>
                              <span className="text-[10px] text-slate-400 truncate">
                                ({m.publicSlug})
                              </span>
                            </div>
                            <span className="text-[10px] text-slate-500 shrink-0">{m.city}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}

              {/* Schedule Dates */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Starts At</label>
                  <input
                    type="datetime-local"
                    value={startsAt}
                    onChange={(e) => setStartsAt(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Ends At (Optional)
                  </label>
                  <input
                    type="datetime-local"
                    value={endsAt}
                    onChange={(e) => setEndsAt(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreateOpen(false);
                    setEditingCampaign(null);
                  }}
                  className="px-3 py-1.5 border border-slate-200 text-slate-600 rounded-lg text-xs hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-[#1F5D42] text-white rounded-lg text-xs font-semibold hover:bg-[#164430] disabled:opacity-50 transition-colors shadow-2xs"
                >
                  {submitting ? "Saving..." : editingCampaign ? "Save Changes" : "Save Draft Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
