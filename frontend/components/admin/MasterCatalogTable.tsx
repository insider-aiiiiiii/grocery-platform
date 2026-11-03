"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  Boxes,
  Plus,
  CheckCircle,
  Tag,
  ArrowUpRight,
  Download,
  Upload,
  UploadCloud,
  Pencil,
  Trash2,
  Search,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FileCode,
  Image as ImageIcon,
  X,
  AlertCircle,
} from "lucide-react";
import { adminApi, MasterProduct } from "@/lib/api/admin";

interface MasterCatalogTableProps {
  products: MasterProduct[];
  onRefresh?: () => void;
  token?: string;
}

export function MasterCatalogTable({
  products,
  onRefresh,
  token,
}: MasterCatalogTableProps) {
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<MasterProduct | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);

  // Form states (Add / Edit)
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [brand, setBrand] = useState("");
  const [description, setDescription] = useState("");
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [newImageUrl, setNewImageUrl] = useState("");
  const imageUploadInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search and Pagination
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Import State
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [importLoading, setImportLoading] = useState(false);

  const resetForm = () => {
    setName("");
    setCategory("");
    setBrand("");
    setDescription("");
    setImageUrls([]);
    setImageFiles([]);
    setNewImageUrl("");
    setError(null);
  };

  const handleOpenAdd = () => {
    resetForm();
    setShowAddModal(true);
  };

  const handleOpenEdit = (p: MasterProduct) => {
    resetForm();
    setEditingProduct(p);
    setName(p.name || "");
    setCategory(p.category_name || (p.category ? String(p.category) : ""));
    setBrand(p.brand || "");
    setDescription(p.description || "");
    const initialImages: string[] = [];
    if (p.image) initialImages.push(p.image);
    if (Array.isArray(p.images)) {
      p.images.forEach((img) => {
        if (!initialImages.includes(img)) initialImages.push(img);
      });
    }
    setImageUrls(initialImages.slice(0, 6));
    setImageFiles([]);
  };

  const handleImageFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const remaining = 6 - imageUrls.length;
    const toAdd = files.slice(0, remaining);

    toAdd.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          setImageUrls((prev) => [...prev, reader.result as string]);
          setImageFiles((prev) => [...prev, file]);
        }
      };
      reader.readAsDataURL(file);
    });
    if (imageUploadInputRef.current) {
      imageUploadInputRef.current.value = "";
    }
  };

  const handleAddImageUrl = () => {
    const trimmed = newImageUrl.trim();
    if (!trimmed) return;
    if (imageUrls.length >= 6) {
      setError("Maximum 6 images allowed per master product.");
      return;
    }
    setImageUrls([...imageUrls, trimmed]);
    setNewImageUrl("");
  };

  const handleRemoveImageUrl = (index: number) => {
    setImageUrls((prev) => prev.filter((_, idx) => idx !== index));
    setImageFiles((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Product Name is required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (imageFiles.length > 0) {
        const formData = new FormData();
        formData.append("name", name.trim());
        if (brand.trim()) formData.append("brand", brand.trim());
        if (description.trim()) formData.append("description", description.trim());
        if (category.trim()) {
          const catNum = parseInt(category.trim(), 10);
          if (!isNaN(catNum)) formData.append("category", String(catNum));
        }
        formData.append("image", imageFiles[0]);
        await adminApi.createMasterProduct(formData, token);
      } else {
        const payload: any = {
          name: name.trim(),
          brand: brand.trim(),
          description: description.trim(),
        };
        if (category.trim()) {
          const catNum = parseInt(category.trim(), 10);
          if (!isNaN(catNum)) {
            payload.category = catNum;
          }
        }
        if (imageUrls.length > 0) {
          payload.image = imageUrls[0];
        }
        await adminApi.createMasterProduct(payload, token);
      }
      setShowAddModal(false);
      resetForm();
      onRefresh?.();
    } catch (e: any) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProduct) return;
    if (!name.trim()) {
      setError("Product Name is required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (imageFiles.length > 0) {
        const formData = new FormData();
        formData.append("name", name.trim());
        if (brand.trim()) formData.append("brand", brand.trim());
        if (description.trim()) formData.append("description", description.trim());
        if (category.trim()) {
          const catNum = parseInt(category.trim(), 10);
          if (!isNaN(catNum)) formData.append("category", String(catNum));
        }
        formData.append("image", imageFiles[0]);
        await adminApi.updateMasterProduct(editingProduct.id, formData, token);
      } else {
        const payload: any = {
          name: name.trim(),
          brand: brand.trim(),
          description: description.trim(),
        };
        if (category.trim()) {
          const catNum = parseInt(category.trim(), 10);
          if (!isNaN(catNum)) {
            payload.category = catNum;
          }
        }
        if (imageUrls.length > 0) {
          payload.image = imageUrls[0];
        }
        await adminApi.updateMasterProduct(editingProduct.id, payload, token);
      }
      setEditingProduct(null);
      resetForm();
      onRefresh?.();
    } catch (e: any) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProduct = async (id: number, productName: string) => {
    if (!window.confirm(`Are you sure you want to delete '${productName}' from Master Catalog?`)) {
      return;
    }
    try {
      await adminApi.deleteMasterProduct(id, token);
      onRefresh?.();
    } catch (e: any) {
      alert(`Failed to delete: ${e.response?.data ? JSON.stringify(e.response.data) : e.message}`);
    }
  };

  // Export to JSON
  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(products, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `master_catalog_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Export to CSV / Excel
  const handleExportCSV = () => {
    const headers = ["ID", "Name", "Category", "Brand", "Description", "Image"];
    const rows = products.map((p) => [
      p.id,
      `"${(p.name || "").replace(/"/g, '""')}"`,
      `"${(p.category_name || (p.category ? String(p.category) : "")).replace(/"/g, '""')}"`,
      `"${(p.brand || "").replace(/"/g, '""')}"`,
      `"${(p.description || "").replace(/"/g, '""')}"`,
      `"${(p.image || "").replace(/"/g, '""')}"`,
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", encodedUri);
    downloadAnchor.setAttribute("download", `master_catalog_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Bulk Import handler (supports JSON and CSV)
  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportLoading(true);
    setImportStatus("Reading file...");

    try {
      const text = await file.text();
      let importedItems: Array<{ name: string; brand?: string; description?: string; category?: number }> = [];

      if (file.name.endsWith(".json")) {
        const parsed = JSON.parse(text);
        if (Array.isArray(parsed)) {
          importedItems = parsed;
        } else if (parsed && Array.isArray(parsed.results)) {
          importedItems = parsed.results;
        } else {
          throw new Error("JSON must contain an array of products.");
        }
      } else if (file.name.endsWith(".csv")) {
        const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
        if (lines.length <= 1) throw new Error("CSV file has no data rows.");
        // Skip header
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
          if (cols[0] || cols[1]) {
            // Check if col 0 is ID or Name
            const isFirstColId = !isNaN(parseInt(cols[0], 10)) && cols.length > 2;
            const nameVal = isFirstColId ? cols[1] : cols[0];
            const brandVal = isFirstColId ? cols[3] : cols[2];
            const descVal = isFirstColId ? cols[4] : cols[3];
            if (nameVal) {
              importedItems.push({
                name: nameVal,
                brand: brandVal || "",
                description: descVal || "",
              });
            }
          }
        }
      } else {
        throw new Error("Please select a .json or .csv file.");
      }

      setImportStatus(`Uploading ${importedItems.length} products to master catalog...`);
      let successCount = 0;
      for (const item of importedItems) {
        if (!item.name) continue;
        try {
          await adminApi.createMasterProduct(
            {
              name: item.name,
              brand: item.brand || "",
              description: item.description || "",
              category: typeof item.category === "number" ? item.category : undefined,
            },
            token
          );
          successCount++;
        } catch {
          // Ignore individual row failure, continue with remaining
        }
      }

      setImportStatus(`Successfully imported ${successCount} of ${importedItems.length} products!`);
      setTimeout(() => {
        setShowImportModal(false);
        setImportStatus(null);
        onRefresh?.();
      }, 1500);
    } catch (err: any) {
      setImportStatus(`Error importing file: ${err.message}`);
    } finally {
      setImportLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Filter products by search query
  const filteredProducts = useMemo(() => {
    if (!searchQuery.trim()) return products;
    const q = searchQuery.toLowerCase();
    return products.filter(
      (p) =>
        p.name?.toLowerCase().includes(q) ||
        p.brand?.toLowerCase().includes(q) ||
        p.category_name?.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q)
    );
  }, [products, searchQuery]);

  // Paginated slice
  const totalPages = Math.ceil(filteredProducts.length / pageSize) || 1;
  const paginatedProducts = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredProducts.slice(start, start + pageSize);
  }, [filteredProducts, currentPage, pageSize]);

  return (
    <div className="bg-white border border-[#ddd6ca] rounded-2xl overflow-hidden shadow-xs">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-[#ddd6ca] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FFFDF8]">
        <div>
          <h2 className="text-base font-bold font-display text-[#123324]">
            Master Product Catalog ({products.length})
          </h2>
          <p className="text-xs text-[#6d756f] mt-0.5">
            Platform-wide verified SKU repository. Merchants can browse and select these templates for their shops.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Export Dropdown / Buttons */}
          <div className="inline-flex rounded-xl border border-[#ddd6ca] bg-white shadow-2xs overflow-hidden">
            <button
              onClick={handleExportCSV}
              title="Download CSV for Excel"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#123324] hover:bg-[#F6F0E6] transition-colors border-r border-[#ddd6ca]"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
              <span>Export CSV</span>
            </button>
            <button
              onClick={handleExportJSON}
              title="Download JSON format"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#123324] hover:bg-[#F6F0E6] transition-colors"
            >
              <FileCode className="w-3.5 h-3.5 text-blue-600" />
              <span>Export JSON</span>
            </button>
          </div>

          {/* Import Button */}
          <button
            onClick={() => setShowImportModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#ddd6ca] text-[#123324] text-xs font-semibold rounded-xl hover:bg-[#F6F0E6] shadow-2xs transition-colors"
          >
            <Upload className="w-3.5 h-3.5 text-[#1F5D42]" />
            <span>Import Catalog</span>
          </button>

          {/* Add Product Button */}
          <button
            onClick={handleOpenAdd}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#1F5D42] text-white text-xs font-bold rounded-xl hover:bg-[#123324] shadow-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add Master Product</span>
          </button>
        </div>
      </div>

      {/* Search Filter Bar */}
      <div className="p-3 bg-[#FAF8F3] border-b border-[#eee9df] flex items-center justify-between gap-3 text-xs">
        <div className="relative w-full max-w-sm">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8b948d]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search products by name, brand, or category..."
            className="w-full pl-9 pr-3 py-1.5 bg-white border border-[#ddd6ca] rounded-xl text-xs outline-none focus:border-[#1F5D42]"
          />
        </div>
        <div className="text-[11px] font-medium text-[#6d756f] shrink-0">
          Showing {paginatedProducts.length} of {filteredProducts.length} results
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#123324] text-white text-[10px] uppercase font-bold tracking-wider">
              <th className="py-3 px-4">Product Name</th>
              <th className="py-3 px-3">Category</th>
              <th className="py-3 px-3">Brand</th>
              <th className="py-3 px-3">Description</th>
              <th className="py-3 px-3">Photos</th>
              <th className="py-3 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eee9df]">
            {paginatedProducts.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-[#869088]">
                  <Boxes className="w-8 h-8 mx-auto text-[#b2bcae] mb-2 opacity-50" />
                  <p className="font-semibold text-sm text-[#123324]">No master products found</p>
                  <p className="text-xs text-[#6d756f] mt-1">
                    {searchQuery ? "Try a different search term." : "Click 'Add Master Product' or 'Import Catalog' to curate verified items."}
                  </p>
                </td>
              </tr>
            ) : (
              paginatedProducts.map((p) => (
                <tr key={p.id} className="hover:bg-[#FAF8F3] transition-colors">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      {p.image ? (
                        <img
                          src={p.image}
                          alt={p.name}
                          className="w-9 h-9 object-cover rounded-lg border border-[#ddd6ca] shrink-0"
                        />
                      ) : (
                        <div className="w-9 h-9 rounded-lg bg-[#eee9df] flex items-center justify-center text-[#6d756f] shrink-0">
                          <ImageIcon className="w-4 h-4" />
                        </div>
                      )}
                      <div>
                        <div className="font-bold text-[#123324]">{p.name}</div>
                        <div className="text-[10px] text-[#869088]">ID: #{p.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5]">
                      <Tag className="w-3 h-3 text-[#1F5D42]" />
                      {p.category_name || (p.category ? `Cat #${p.category}` : "General")}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-[#123324] font-medium">{p.brand || "—"}</td>
                  <td className="py-3 px-3 text-[#6d756f] max-w-xs truncate">{p.description || "—"}</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#6d756f]">
                      <ImageIcon className="w-3 h-3 text-[#1F5D42]" />
                      <span>{p.image ? "1+ photo" : "No photo"}</span>
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <div className="inline-flex items-center gap-1.5">
                      <button
                        onClick={() => handleOpenEdit(p)}
                        className="p-1.5 text-[#1F5D42] hover:bg-[#e7f2eb] rounded-lg transition-colors"
                        title="Edit Master Product"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteProduct(p.id, p.name)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete Master Product"
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

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-3 bg-[#FFFDF8] border-t border-[#ddd6ca] flex items-center justify-between text-xs">
          <div className="text-[#6d756f] font-medium">
            Page {currentPage} of {totalPages}
          </div>
          <div className="inline-flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
              className="p-1.5 border border-[#ddd6ca] rounded-lg hover:bg-[#FAF8F3] disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <ChevronLeft className="w-4 h-4 text-[#123324]" />
            </button>
            {Array.from({ length: totalPages }).map((_, idx) => {
              const pageNum = idx + 1;
              if (pageNum < currentPage - 2 || pageNum > currentPage + 2) return null;
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-7 h-7 rounded-lg text-xs font-semibold ${
                    currentPage === pageNum
                      ? "bg-[#1F5D42] text-white"
                      : "border border-[#ddd6ca] hover:bg-[#FAF8F3] text-[#123324]"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="p-1.5 border border-[#ddd6ca] rounded-lg hover:bg-[#FAF8F3] disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <ChevronRight className="w-4 h-4 text-[#123324]" />
            </button>
          </div>
        </div>
      )}

      {/* Modal: Add or Edit Master Product */}
      {(showAddModal || editingProduct) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white border border-[#ddd6ca] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
              <h3 className="text-base font-bold font-display text-[#123324]">
                {editingProduct ? "Edit Master Product" : "Add Master Product"}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowAddModal(false);
                  setEditingProduct(null);
                }}
                className="text-[#6d756f] hover:text-[#123324] p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form
              onSubmit={editingProduct ? handleUpdateProduct : handleCreateProduct}
              className="space-y-3.5 text-xs"
            >
              <div>
                <label className="block font-bold text-[#123324] mb-1">
                  Product Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Amul Gold Full Cream Milk 1L"
                  className="w-full px-3 py-2 border border-[#ddd6ca] rounded-xl outline-none focus:border-[#1F5D42] text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-[#123324] mb-1">
                    Category (Optional)
                  </label>
                  <input
                    type="text"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    placeholder="e.g. Dairy or Category ID"
                    className="w-full px-3 py-2 border border-[#ddd6ca] rounded-xl outline-none focus:border-[#1F5D42] text-xs"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#123324] mb-1">
                    Brand Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={brand}
                    onChange={(e) => setBrand(e.target.value)}
                    placeholder="e.g. Amul"
                    className="w-full px-3 py-2 border border-[#ddd6ca] rounded-xl outline-none focus:border-[#1F5D42] text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-[#123324] mb-1">
                  Description (Optional)
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Standard verified package specifications, ingredients or weight details..."
                  className="w-full px-3 py-2 border border-[#ddd6ca] rounded-xl outline-none focus:border-[#1F5D42] text-xs"
                />
              </div>

              {/* Photos Management (Max 6 photos) */}
              <div className="border-t border-[#eee9df] pt-3">
                <div className="flex items-center justify-between mb-2">
                  <label className="font-bold text-[#123324]">
                    Product Photos (Max 6)
                  </label>
                  <span className="text-[10px] text-[#6d756f] font-mono">
                    {imageUrls.length}/6 photos added
                  </span>
                </div>

                {/* Thumbnails list */}
                {imageUrls.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {imageUrls.map((url, idx) => (
                      <div
                        key={idx}
                        className="relative w-14 h-14 rounded-xl border border-[#ddd6ca] overflow-hidden bg-slate-50 group"
                      >
                        <img src={url} alt={`Photo ${idx + 1}`} className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => handleRemoveImageUrl(idx)}
                          className="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-600 text-white flex items-center justify-center opacity-80 hover:opacity-100"
                        >
                          <X className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {imageUrls.length < 6 && (
                  <div className="space-y-2">
                    <input
                      ref={imageUploadInputRef}
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={handleImageFilesSelected}
                      className="hidden"
                    />

                    <div
                      onClick={() => imageUploadInputRef.current?.click()}
                      className="flex flex-col items-center justify-center p-3.5 border-2 border-dashed border-[#cbe1d5] bg-[#f0f7f3] hover:bg-[#e7f2eb] rounded-xl cursor-pointer transition text-center group"
                    >
                      <UploadCloud className="w-5 h-5 text-[#1F5D42] mb-1 group-hover:scale-110 transition-transform" />
                      <span className="text-xs font-bold text-[#1F5D42]">
                        Upload Pictures from Device
                      </span>
                      <span className="text-[10px] text-[#6d756f]">
                        Select image files directly (PNG, JPG, WebP)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <span className="text-[10px] text-slate-400 font-medium">Or via link:</span>
                      <input
                        type="url"
                        value={newImageUrl}
                        onChange={(e) => setNewImageUrl(e.target.value)}
                        placeholder="https://..."
                        className="flex-1 px-2.5 py-1 border border-[#ddd6ca] rounded-lg outline-none focus:border-[#1F5D42] text-[11px]"
                      />
                      <button
                        type="button"
                        onClick={handleAddImageUrl}
                        className="px-2.5 py-1 bg-[#FAF8F3] hover:bg-[#e7f2eb] border border-[#ddd6ca] text-[#1F5D42] text-xs font-semibold rounded-lg"
                      >
                        Add Link
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#eee9df]">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingProduct(null);
                  }}
                  className="px-4 py-2 border border-[#ddd6ca] text-[#123324] font-semibold rounded-xl hover:bg-[#FAF8F3]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-5 py-2 bg-[#1F5D42] text-white font-bold rounded-xl hover:bg-[#123324] shadow-xs disabled:opacity-50"
                >
                  {loading
                    ? "Saving..."
                    : editingProduct
                    ? "Update Product"
                    : "Save Master Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Bulk Import Catalog */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white border border-[#ddd6ca] rounded-2xl w-full max-w-md overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eee9df] pb-3">
              <h3 className="text-base font-bold font-display text-[#123324]">
                Bulk Import Master Catalog
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowImportModal(false);
                  setImportStatus(null);
                }}
                className="text-[#6d756f] hover:text-[#123324] p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[#6d756f]">
              Upload a <strong>JSON (.json)</strong> or <strong>CSV / Excel (.csv)</strong> file with columns:{" "}
              <code className="text-[#1F5D42] bg-[#e7f2eb] px-1 py-0.5 rounded font-mono">
                Name, Category, Brand, Description
              </code>
              . The catalog items will be automatically parsed and added.
            </p>

            <div className="border-2 border-dashed border-[#ddd6ca] rounded-2xl p-6 text-center hover:bg-[#FAF8F3] transition cursor-pointer">
              <Upload className="w-8 h-8 text-[#1F5D42] mx-auto mb-2 opacity-70" />
              <label className="cursor-pointer block">
                <span className="font-bold text-xs text-[#1F5D42]">Select JSON or CSV file</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,.csv"
                  onChange={handleFileImport}
                  disabled={importLoading}
                  className="hidden"
                />
              </label>
              <p className="text-[10px] text-[#869088] mt-1">Supports UTF-8 CSV from Excel or JSON export</p>
            </div>

            {importStatus && (
              <div className="p-3 bg-[#e7f2eb] border border-[#cbe1d5] text-[#1F5D42] font-semibold text-xs rounded-xl flex items-center gap-2">
                <span>{importStatus}</span>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowImportModal(false);
                  setImportStatus(null);
                }}
                className="px-4 py-2 border border-[#ddd6ca] text-[#123324] font-semibold rounded-xl hover:bg-[#FAF8F3] text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
