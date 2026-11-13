"use client";

import React, { useState, useRef } from "react";
import {
  X,
  Download,
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Plus,
} from "lucide-react";
import { merchantApi, getApiError } from "@/lib/api/merchant";

interface ParsedProductRow {
  name: string;
  brand: string;
  price: number;
  mrp?: number;
  description: string;
  isValid: boolean;
  validationError?: string;
}

interface BulkExcelUploadModalProps {
  onClose: () => void;
  onSuccess: (count: number) => void;
  lang?: "en" | "hi";
}

export function BulkExcelUploadModal({
  onClose,
  onSuccess,
  lang = "en",
}: BulkExcelUploadModalProps) {
  const isHi = lang === "hi";
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fileName, setFileName] = useState<string>("");
  const [parsedRows, setParsedRows] = useState<ParsedProductRow[]>([]);
  const [importing, setImporting] = useState<boolean>(false);
  const [progress, setProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
  const [importError, setImportError] = useState<string>("");
  const [importSuccessCount, setImportSuccessCount] = useState<number | null>(null);

  // 1. Download official CSV template
  const handleDownloadTemplate = () => {
    const csvContent =
      "Product Name,Brand,Price,MRP,Description\n" +
      "Fortune Sunlite Sunflower Oil 1L,Fortune,155,175,Refined sunflower oil for healthy cooking\n" +
      "Aashirvaad Shudh Chakki Atta 5kg,Aashirvaad,245,275,100% whole wheat flour\n" +
      "Amul Butter 500g,Amul,275,285,Pasteurised table butter\n" +
      "Tata Salt 1kg,Tata,28,30,Vacuum evaporated iodised salt\n" +
      "Maggi 2-Minute Noodles 280g,Nestle,56,60,Instant noodles with tastemaker\n";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "dukandaar_catalog_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 2. Parse uploaded CSV file
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setImportError("");
    setImportSuccessCount(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        if (!text) {
          setImportError(isHi ? "फ़ाइल खाली है।" : "File is empty.");
          return;
        }

        const lines = text
          .split(/\r?\n/)
          .map((l) => l.trim())
          .filter((l) => l.length > 0);

        if (lines.length < 2) {
          setImportError(
            isHi
              ? "फ़ाइल में कोई डेटा पंक्ति नहीं मिली।"
              : "No data rows found in the CSV file."
          );
          return;
        }

        // Header check
        const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
        const nameIdx = headers.findIndex((h) => h.includes("product") || h.includes("name") || h.includes("item"));
        const brandIdx = headers.findIndex((h) => h.includes("brand"));
        const priceIdx = headers.findIndex((h) => h === "price" || h.includes("selling") || h.includes("rate"));
        const mrpIdx = headers.findIndex((h) => h.includes("mrp"));
        const descIdx = headers.findIndex((h) => h.includes("desc"));

        const rows: ParsedProductRow[] = [];

        for (let i = 1; i < lines.length; i++) {
          const rawLine = lines[i];
          if (!rawLine.trim()) continue;

          // Simple CSV line splitter handling basic quotes
          const cols: string[] = [];
          let current = "";
          let inQuotes = false;

          for (let j = 0; j < rawLine.length; j++) {
            const char = rawLine[j];
            if (char === '"' || char === "'") {
              inQuotes = !inQuotes;
            } else if (char === "," && !inQuotes) {
              cols.push(current.trim());
              current = "";
            } else {
              current += char;
            }
          }
          cols.push(current.trim());

          const name = (nameIdx >= 0 && cols[nameIdx]) || cols[0] || "";
          const brand = (brandIdx >= 0 && cols[brandIdx]) || (cols[1] || "");
          const rawPrice = (priceIdx >= 0 && cols[priceIdx]) || (cols[2] || "");
          const rawMrp = (mrpIdx >= 0 && cols[mrpIdx]) || (cols[3] || "");
          const desc = (descIdx >= 0 && cols[descIdx]) || (cols[4] || "");

          const priceNum = parseFloat(rawPrice.replace(/[^0-9.]/g, ""));
          const mrpNum = rawMrp ? parseFloat(rawMrp.replace(/[^0-9.]/g, "")) : undefined;

          let isValid = true;
          let validationError = "";

          if (!name || name.trim().length === 0) {
            isValid = false;
            validationError = isHi ? "नाम आवश्यक है" : "Name required";
          } else if (Number.isNaN(priceNum) || priceNum < 0) {
            isValid = false;
            validationError = isHi ? "गलत कीमत" : "Invalid price";
          }

          rows.push({
            name: name.trim(),
            brand: brand.trim(),
            price: Number.isNaN(priceNum) ? 0 : priceNum,
            mrp: mrpNum && !Number.isNaN(mrpNum) ? mrpNum : undefined,
            description: desc.trim(),
            isValid,
            validationError,
          });
        }

        setParsedRows(rows);
      } catch {
        setImportError(
          isHi
            ? "फ़ाइल पढ़ने में गड़बड़ी हुई। कृपया टेम्पलेट वाला CSV फ़ॉर्मेट जांचें।"
            : "Failed to parse CSV file. Please ensure standard CSV format."
        );
      }
    };
    reader.readAsText(file);
  };

  // 3. Batch submit valid rows to backend
  const handleImport = async () => {
    const validRows = parsedRows.filter((r) => r.isValid);
    if (validRows.length === 0) return;

    setImporting(true);
    setImportError("");
    setProgress({ current: 0, total: validRows.length });

    let successCount = 0;
    const errors: string[] = [];

    for (let i = 0; i < validRows.length; i++) {
      const row = validRows[i];
      try {
        await merchantApi.createProduct({
          name: row.name,
          brand: row.brand || undefined,
          price: String(row.price),
          description: row.description || undefined,
          is_visible: true,
          is_available: true,
        });
        successCount++;
      } catch (err: any) {
        errors.push(`${row.name}: ${getApiError(err)}`);
      }
      setProgress({ current: i + 1, total: validRows.length });
    }

    setImporting(false);
    setImportSuccessCount(successCount);

    if (errors.length > 0 && successCount === 0) {
      setImportError(errors.slice(0, 3).join("; "));
    } else {
      onSuccess(successCount);
    }
  };

  const validCount = parsedRows.filter((r) => r.isValid).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-2xl rounded-3xl bg-[#FFFDF8] border border-[#ddd6ca] p-6 shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#eee9df] pb-4">
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#fef3db] text-[#8a5b1d] border border-[#f5deb5]">
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3 className="font-display font-bold text-base text-[#123324]">
                {isHi ? "एक्सेल / CSV से एक साथ सामान जोड़ें" : "Bulk Excel / CSV Catalog Upload"}
              </h3>
              <p className="text-xs text-[#6d756f]">
                {isHi
                  ? "एक साथ कई सामान अपनी दुकान में आयात करें"
                  : "Import multiple products at once into your dukaan"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label={isHi ? "बंद करें" : "Close"}
            className="text-[#6d756f] hover:text-[#123324] p-1.5 rounded-xl hover:bg-[#eee9df] transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto py-5 space-y-5 text-xs">
          {/* Step 1: Download Template */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-2xl bg-[#faf8f3] border border-[#eee9df]">
            <div>
              <p className="font-bold text-[#123324]">
                {isHi ? "1. सैंपल एक्सेल / CSV टेम्पलेट डाउनलोड करें" : "1. Download Sample Excel / CSV Template"}
              </p>
              <p className="text-[11px] text-[#6d756f] mt-0.5">
                {isHi
                  ? "इस टेम्पलेट में सामान का नाम, ब्रांड, कीमत, एमआरपी और विवरण भरें।"
                  : "Use this template with predefined columns: Product Name, Brand, Price, MRP, Description."}
              </p>
            </div>
            <button
              onClick={handleDownloadTemplate}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-[#ddd6ca] text-[#1F5D42] font-bold text-xs hover:bg-[#e7f2eb] shadow-2xs transition shrink-0 cursor-pointer"
            >
              <Download size={14} />
              <span>{isHi ? "टेम्पलेट डाउनलोड करें (.csv)" : "Download Template (.csv)"}</span>
            </button>
          </div>

          {/* Step 2: Upload File Box */}
          <div className="space-y-2">
            <p className="font-bold text-[#123324]">
              {isHi ? "2. भरी हुई CSV फ़ाइल अपलोड करें" : "2. Upload your prepared CSV file"}
            </p>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-[#ddd6ca] hover:border-[#1F5D42] rounded-2xl p-6 text-center bg-white cursor-pointer transition hover:bg-[#faf8f3] space-y-2"
            >
              <UploadCloud size={28} className="mx-auto text-[#1F5D42]" />
              <div>
                <p className="font-bold text-xs text-[#123324]">
                  {fileName ? (
                    <span className="text-[#1F5D42]">{fileName}</span>
                  ) : isHi ? (
                    "फ़ाइल चुनने के लिए यहाँ क्लिक करें या ड्रैग करें"
                  ) : (
                    "Click to browse or drag & drop CSV file"
                  )}
                </p>
                <p className="text-[11px] text-[#869088] mt-0.5">
                  {isHi ? ".CSV फ़ाइल चलेगी (अधिकतम 5MB)" : ".CSV format supported (Max 5MB)"}
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          </div>

          {/* Error Banner */}
          {importError && (
            <div className="flex items-start gap-2 p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{importError}</span>
            </div>
          )}

          {/* Success Banner */}
          {importSuccessCount !== null && (
            <div className="flex items-center gap-2 p-3.5 rounded-xl bg-[#e7f2eb] border border-[#cbe1d5] text-xs text-[#1F5D42]">
              <CheckCircle2 size={16} className="shrink-0" />
              <span>
                {isHi
                  ? `सफलतापूर्वक ${importSuccessCount} सामान आपकी दुकान में जोड़ दिए गए हैं!`
                  : `Successfully imported ${importSuccessCount} products into your dukaan!`}
              </span>
            </div>
          )}

          {/* Step 3: Parsed Preview Table */}
          {parsedRows.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-[#123324]">
                  {isHi ? "3. डेटा की झलक" : "3. Parsed Data Preview"}
                </span>
                <span className="text-[11px] text-[#6d756f]">
                  {validCount} / {parsedRows.length} {isHi ? "मान्य पंक्तियाँ" : "valid rows"}
                </span>
              </div>
              <div className="max-h-48 overflow-y-auto rounded-xl border border-[#ddd6ca] bg-white divide-y divide-[#eee9df]">
                {parsedRows.slice(0, 15).map((row, idx) => (
                  <div
                    key={idx}
                    className={`p-2.5 flex items-center justify-between text-xs ${
                      !row.isValid ? "bg-red-50/50" : ""
                    }`}
                  >
                    <div className="min-w-0 pr-3">
                      <p className="font-semibold text-[#123324] truncate">{row.name}</p>
                      <p className="text-[10px] text-[#6d756f]">
                        {row.brand && <span>{row.brand} · </span>}
                        <span>₹{row.price}</span>
                        {row.mrp && <span className="line-through text-[#869088] ml-1">{isHi ? "एमआरपी" : "MRP"} ₹{row.mrp}</span>}
                      </p>
                    </div>
                    {row.isValid ? (
                      <span className="text-[10px] font-bold text-[#1F5D42] bg-[#e7f2eb] px-2 py-0.5 rounded-full shrink-0">
                        {isHi ? "तैयार ✓" : "Ready ✓"}
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded-full shrink-0">
                        {row.validationError}
                      </span>
                    )}
                  </div>
                ))}
                {parsedRows.length > 15 && (
                  <div className="p-2 text-center text-[10px] text-[#6d756f] bg-[#faf8f3]">
                    {isHi
                      ? `+ ${parsedRows.length - 15} और पंक्तियाँ पढ़ी गईं`
                      : `+ ${parsedRows.length - 15} more rows parsed`}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[#eee9df] pt-4 flex items-center justify-between gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-[#6d756f] hover:text-[#123324]"
          >
            {isHi ? "बंद करें" : "Cancel"}
          </button>

          <button
            onClick={handleImport}
            disabled={importing || validCount === 0 || importSuccessCount !== null}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-[#1F5D42] hover:bg-[#123324] text-white text-xs font-bold shadow-xs transition active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            {importing ? (
              <>
                <RefreshCw size={13} className="animate-spin" />
                <span>
                  {isHi ? "जोड़ा जा रहा है…" : "Importing"} ({progress.current}/{progress.total})
                </span>
              </>
            ) : (
              <>
                <Plus size={14} />
                <span>
                  {isHi
                    ? `${validCount} सामान दुकान में जोड़ें`
                    : `Import ${validCount} Products to Dukaan`}
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
