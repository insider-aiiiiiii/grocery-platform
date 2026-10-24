"use client";

import React, { useState } from "react";
import { Megaphone, Plus, Calendar, Tag, CheckCircle2, Play, Square, AlertCircle } from "lucide-react";
import { adminApi } from "@/lib/api/admin";

export interface CampaignItem {
  id: number;
  name: string;
  banner_url?: string;
  discount_percentage?: string;
  status: "DRAFT" | "ACTIVE" | "ENDED";
  starts_at: string;
  ends_at?: string;
}

interface CampaignsManagerProps {
  campaigns?: CampaignItem[];
  onRefresh?: () => void;
}

export function CampaignsManager({ campaigns = [], onRefresh }: CampaignsManagerProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [discount, setDiscount] = useState("15.00");
  const [bannerUrl, setBannerUrl] = useState("");
  const [startsAt, setStartsAt] = useState(new Date().toISOString().slice(0, 16));
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Default fallback campaigns for visualization
  const displayCampaigns = campaigns.length > 0 ? campaigns : [
    {
      id: 1,
      name: "Diwali Mahabachat Festive Sale",
      discount_percentage: "20.00",
      status: "ACTIVE" as const,
      starts_at: "2026-10-20T00:00:00Z",
      ends_at: "2026-11-05T23:59:59Z",
    },
    {
      id: 2,
      name: "Weekend Fresh Veggies Blast",
      discount_percentage: "10.00",
      status: "DRAFT" as const,
      starts_at: "2026-10-26T06:00:00Z",
      ends_at: "2026-10-27T22:00:00Z",
    },
  ];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setActionError(null);
    try {
      await adminApi.createCampaign({
        name,
        discount_percentage: discount,
        banner_url: bannerUrl || undefined,
        starts_at: new Date(startsAt).toISOString(),
      });
      setIsCreateOpen(false);
      setName("");
      if (onRefresh) onRefresh();
    } catch {
      setActionError("Failed to create campaign. Verify Super Admin authorization.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleActivate = async (id: number) => {
    try {
      await adminApi.activateCampaign(id);
      if (onRefresh) onRefresh();
    } catch {
      setActionError("Could not activate campaign.");
    }
  };

  const handleEnd = async (id: number) => {
    try {
      await adminApi.endCampaign(id);
      if (onRefresh) onRefresh();
    } catch {
      setActionError("Could not end campaign.");
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Megaphone className="w-4 h-4 text-[#1F5D42]" />
            <h2 className="text-sm font-bold text-slate-900 tracking-tight">
              Network Marketing Campaigns
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-tenant promotional banners, discounts, and regional broadcast sales.
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1F5D42] text-white text-xs font-semibold rounded hover:bg-[#164430] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Create Campaign
        </button>
      </div>

      {actionError && (
        <div className="mx-4 mt-3 p-2 bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {actionError}
        </div>
      )}

      {/* Campaign List Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="py-2.5 px-4">Campaign Name</th>
              <th className="py-2.5 px-4">Discount</th>
              <th className="py-2.5 px-4">Status</th>
              <th className="py-2.5 px-4">Schedule</th>
              <th className="py-2.5 px-4 text-right">Lifecycle Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {displayCampaigns.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3 px-4 font-semibold text-slate-900">
                  {c.name}
                </td>
                <td className="py-3 px-4">
                  <span className="inline-flex items-center gap-1 font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded text-[11px] font-bold">
                    <Tag className="w-3 h-3" />
                    {c.discount_percentage ? `${c.discount_percentage}% OFF` : "Banner Only"}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      c.status === "ACTIVE"
                        ? "bg-emerald-100 text-emerald-800"
                        : c.status === "DRAFT"
                        ? "bg-slate-100 text-slate-700"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="py-3 px-4 text-slate-500 text-[11px]">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>{new Date(c.starts_at).toLocaleDateString("en-IN")}</span>
                    {c.ends_at && <span>→ {new Date(c.ends_at).toLocaleDateString("en-IN")}</span>}
                  </div>
                </td>
                <td className="py-3 px-4 text-right">
                  <div className="inline-flex items-center gap-1.5">
                    {c.status === "DRAFT" && (
                      <button
                        onClick={() => handleActivate(c.id)}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-600 text-white rounded text-[11px] font-semibold hover:bg-emerald-700"
                      >
                        <Play className="w-3 h-3" />
                        Activate
                      </button>
                    )}
                    {c.status === "ACTIVE" && (
                      <button
                        onClick={() => handleEnd(c.id)}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 text-white rounded text-[11px] font-semibold hover:bg-slate-800"
                      >
                        <Square className="w-3 h-3" />
                        End Early
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal: Create Platform Campaign */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-slate-200 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Launch Platform Campaign</h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Campaign Title</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Republic Day Grocery Bonanza"
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#1F5D42] focus:border-[#1F5D42]"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Discount (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                  placeholder="15.00"
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Banner Image URL (Optional)</label>
                <input
                  type="url"
                  value={bannerUrl}
                  onChange={(e) => setBannerUrl(e.target.value)}
                  placeholder="https://images.unsplash.com/..."
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Starts At</label>
                <input
                  type="datetime-local"
                  required
                  value={startsAt}
                  onChange={(e) => setStartsAt(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-3 py-1.5 border border-slate-200 text-slate-600 rounded text-xs hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-3 py-1.5 bg-[#1F5D42] text-white rounded text-xs font-semibold hover:bg-[#164430] disabled:opacity-50"
                >
                  {submitting ? "Creating..." : "Save Draft Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
