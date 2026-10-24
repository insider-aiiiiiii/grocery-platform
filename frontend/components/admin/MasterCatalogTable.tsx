"use client";

import React, { useState } from "react";
import { Boxes, Plus, CheckCircle, AlertCircle, Tag, ArrowUpRight } from "lucide-react";
import { adminApi, MasterProduct } from "@/lib/api/admin";

interface MasterCatalogTableProps {
  products: MasterProduct[];
  onRefresh?: () => void;
  token?: string;
}

export function MasterCatalogTable({ products, onRefresh, token }: MasterCatalogTableProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("1");
  const [brand, setBrand] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await adminApi.createMasterProduct(
        {
          name: name.trim(),
          category: parseInt(category) || 1,
          brand: brand.trim(),
          description: description.trim(),
        },
        token
      );
      setName("");
      setBrand("");
      setDescription("");
      setShowAddModal(false);
      onRefresh?.();
    } catch (e: any) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Master Product Catalog Curation</h2>
          <p className="text-xs text-slate-500">
            Platform-wide standard product taxonomy and verified SKU specifications.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1F5D42] text-white text-xs font-semibold rounded hover:bg-[#164430] shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add Master Product</span>
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#0F172A] text-slate-100 text-[10px] uppercase font-bold tracking-wider">
              <th className="py-2.5 px-3">Product Name</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3">Brand</th>
              <th className="py-2.5 px-3">Description</th>
              <th className="py-2.5 px-3 text-right">Verification</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {products.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-400">
                  No master products found in the platform catalog.
                </td>
              </tr>
            ) : (
              products.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-slate-900">{p.name}</td>
                  <td className="py-2.5 px-3">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
                      <Tag className="w-3 h-3 text-slate-400" />
                      {p.category_name || `Cat #${p.category}`}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 font-medium">{p.brand || "—"}</td>
                  <td className="py-2.5 px-3 text-slate-500 max-w-xs truncate">{p.description || "—"}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800">
                      <CheckCircle className="w-3 h-3 text-emerald-600" />
                      Verified Master
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal to add master product */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white border border-slate-200 rounded-lg w-full max-w-md overflow-hidden shadow-xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-900">Add Master Product</h3>
            {error && <div className="p-2 bg-red-50 text-red-700 text-xs rounded">{error}</div>}
            <form onSubmit={handleCreateProduct} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Product Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Amul Gold Full Cream Milk 1L"
                  className="w-full px-3 py-1.5 border border-slate-200 rounded outline-none focus:border-[#1F5D42]"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Category ID *</label>
                  <input
                    type="number"
                    required
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-200 rounded outline-none focus:border-[#1F5D42]"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Brand Name *</label>
                  <input
                    type="text"
                    required
                    value={brand}
                    onChange={(e) => setBrand(e.target.value)}
                    placeholder="e.g. Amul"
                    className="w-full px-3 py-1.5 border border-slate-200 rounded outline-none focus:border-[#1F5D42]"
                  />
                </div>
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Standard verified package specifications..."
                  className="w-full px-3 py-1.5 border border-slate-200 rounded outline-none focus:border-[#1F5D42]"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 border border-slate-200 rounded hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 bg-[#1F5D42] text-white font-semibold rounded hover:bg-[#164430] disabled:opacity-50"
                >
                  {loading ? "Creating..." : "Save Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
