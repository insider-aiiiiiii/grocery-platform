"use client";

import React, { useState } from "react";
import {
  MapPin,
  Phone,
  Bike,
  ShoppingBag,
  CheckCircle2,
  Languages,
  ExternalLink,
  Share2,
  Clock,
  ChevronRight,
  ChevronLeft,
  MessageSquare,
  Store,
  Check,
} from "lucide-react";
import { PublicShopInfo } from "@/lib/api/customer";

interface ShopHeaderProps {
  shop: PublicShopInfo;
  language?: "en" | "hi";
  onToggleLanguage?: () => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export function ShopHeader({
  shop,
  language = "en",
  onToggleLanguage,
  searchQuery = "",
  onSearchChange,
}: ShopHeaderProps) {
  const [copied, setCopied] = useState(false);
  const isClosed = shop.is_temporarily_closed;
  const isHindi = language === "hi";

  const [photoIndex, setPhotoIndex] = useState(0);
  const [touchStart, setTouchStart] = useState<number | null>(null);

  // Gallery Photos Resolution: check localStorage for any uploaded photos for this shop
  const [galleryPhotos, setGalleryPhotos] = useState<string[]>(() => {
    return shop.logo && shop.logo.trim() !== "" ? [shop.logo] : [];
  });

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const found: string[] = [];
    if (shop.logo && shop.logo.trim() !== "") found.push(shop.logo);

    try {
      const stored = localStorage.getItem(`dukaandar_shop_photos_${shop.public_slug}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          parsed.forEach((item: any) => {
            const url = typeof item === "string" ? item : item?.url;
            if (url && !found.includes(url)) found.push(url);
          });
        }
      }
    } catch {
      // Ignore
    }

    setGalleryPhotos(found);
  }, [shop.logo, shop.public_slug]);

  const handlePrevPhoto = (e: React.MouseEvent) => {
    e.stopPropagation();
    setPhotoIndex((prev) => (prev > 0 ? prev - 1 : galleryPhotos.length - 1));
  };

  const handleNextPhoto = (e: React.MouseEvent) => {
    e.stopPropagation();
    setPhotoIndex((prev) => (prev < galleryPhotos.length - 1 ? prev + 1 : 0));
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStart(e.targetTouches[0].clientX);
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStart === null) return;
    const touchEnd = e.changedTouches[0].clientX;
    const diff = touchStart - touchEnd;
    if (diff > 50) {
      // Swiped left -> next photo
      setPhotoIndex((prev) => (prev < galleryPhotos.length - 1 ? prev + 1 : 0));
    } else if (diff < -50) {
      // Swiped right -> previous photo
      setPhotoIndex((prev) => (prev > 0 ? prev - 1 : galleryPhotos.length - 1));
    }
    setTouchStart(null);
  };

  const handleShare = () => {
    if (typeof window === "undefined") return;
    const url = window.location.href;
    if (navigator.share) {
      navigator.share({ title: shop.name, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const currentPhoto = galleryPhotos[photoIndex] || galleryPhotos[0];

  const initials = shop.name
    .split(" ")
    .map((word) => word[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase() || "DU";

  const openTime = shop.opening_time ? shop.opening_time.slice(0, 5) : "07:00 AM";
  const closeTime = shop.closing_time ? shop.closing_time.slice(0, 5) : "11:00 PM";

  return (
    <header className="relative w-full z-20 pb-2">
      {/* 1. Top Dukandaar Brand Header Bar */}
      <div className="sticky top-0 z-30 flex h-14 items-center justify-between bg-[#123324] px-4 shadow-md border-b border-[#1F5D42]/30">
        <div className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center rounded-xl bg-[#E8A33D] text-[#123324] font-bold shadow-sm shrink-0">
            <Store size={18} />
          </div>
          <div>
            <span className="font-display font-bold text-base text-white tracking-tight">Dukandaar</span>
            <span className="ml-2 text-[10px] font-medium text-[#a2b5a8] hidden sm:inline">
              {isHindi ? "स्थानीय ऑनलाइन दुकान" : "Local Verified Store"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Share Button */}
          <button
            onClick={handleShare}
            className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition border border-white/10"
            title={isHindi ? "दुकान शेयर करें" : "Share shop"}
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
          </button>

          {/* Language Switcher */}
          {onToggleLanguage && (
            <button
              onClick={onToggleLanguage}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white text-xs font-semibold border border-white/15 transition shadow-2xs"
              title="Switch Language / भाषा बदलें"
            >
              <Languages className="w-3.5 h-3.5 text-[#E8A33D]" />
              <span>{isHindi ? "English" : "हिंदी"}</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. Storefront Photo Gallery Card (Mobile-First with Swipe & Multi-photo support) */}
      <div className="max-w-xl mx-auto px-3.5 pt-3">
        {galleryPhotos.length > 0 ? (
          <div
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            className="relative h-44 sm:h-52 w-full overflow-hidden rounded-2xl border border-[#e8e2d5] shadow-sm bg-[#123324] select-none"
          >
            <img
              src={currentPhoto}
              alt={`${shop.name} photo ${photoIndex + 1}`}
              className="h-full w-full object-cover transition-opacity duration-200"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-transparent to-black/30 pointer-events-none" />

            {/* Badges on Storefront Photo */}
            <div className="absolute top-2.5 left-2.5 flex items-center gap-2 z-10 pointer-events-none">
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-black/60 backdrop-blur-md text-white text-[10px] font-bold border border-white/20">
                <span>🏪</span>
                <span>{isHindi ? "दुकान का स्टोरफ्रंट" : "Storefront"}</span>
              </span>
            </div>

            {/* Carousel Navigation Arrows & Indicators if > 1 photo */}
            {galleryPhotos.length > 1 && (
              <>
                <button
                  type="button"
                  onClick={handlePrevPhoto}
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 backdrop-blur-xs transition z-20 shadow-md"
                  aria-label="Previous storefront photo"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleNextPhoto}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 backdrop-blur-xs transition z-20 shadow-md"
                  aria-label="Next storefront photo"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>

                <div className="absolute top-2.5 right-2.5 inline-flex items-center px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-white text-[10px] font-mono font-bold border border-white/20 z-10">
                  {photoIndex + 1} / {galleryPhotos.length}
                </div>
              </>
            )}

            {/* Bottom Bar on Photo: Verified Local Store and Location */}
            <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between text-white text-xs z-10 pointer-events-none">
              <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#1F5D42]/90 backdrop-blur-md text-white font-bold text-[11px] shadow-sm border border-emerald-400/30">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />
                <span>{isHindi ? "सत्यापित स्थानीय दुकान" : "Verified Store"}</span>
              </div>

              <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-black/60 backdrop-blur-md text-white text-[11px] font-medium border border-white/20">
                <MapPin className="w-3 h-3 text-emerald-400" />
                <span>{shop.area || shop.city || (isHindi ? "नजदीकी दुकान" : "Near you")}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="relative h-28 sm:h-32 w-full overflow-hidden rounded-2xl border border-[#e8e2d5] shadow-xs bg-gradient-to-br from-[#123324] via-[#1F5D42] to-[#123324] p-4 flex flex-col justify-between text-white select-none">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/15 backdrop-blur-md text-white text-[10px] font-bold border border-white/20">
                <Store className="w-3.5 h-3.5 text-[#E8A33D]" />
                <span>{isHindi ? "किराना स्टोर" : "Kirana Store"}</span>
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 text-[10px] font-bold">
                <CheckCircle2 className="w-3 h-3" />
                <span>{isHindi ? "सत्यापित दुकान" : "Verified"}</span>
              </span>
            </div>
            <div>
              <h3 className="font-display font-bold text-base sm:text-lg text-white leading-tight">
                {shop.name}
              </h3>
              <p className="text-xs text-white/80 flex items-center gap-1 mt-0.5">
                <MapPin className="w-3 h-3 text-[#E8A33D]" />
                <span>{shop.area || shop.city}</span>
              </p>
            </div>
          </div>
        )}

        {/* Multi-Photo Thumbnail Bar if multiple photos exist */}
        {galleryPhotos.length > 1 && (
          <div className="flex items-center gap-2 mt-2 px-1 overflow-x-auto pb-1">
            {galleryPhotos.map((imgUrl, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setPhotoIndex(idx)}
                className={`relative h-12 w-14 rounded-xl overflow-hidden border-2 shrink-0 transition ${
                  photoIndex === idx
                    ? "border-[#1F5D42] shadow-xs ring-2 ring-[#1F5D42]/20"
                    : "border-[#e8e2d5] opacity-60 hover:opacity-100"
                }`}
              >
                <img src={imgUrl} alt={`Thumbnail ${idx + 1}`} className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 3. Storefront Profile Card (Google Maps Place Detail) */}
      <div className="max-w-xl mx-auto px-3.5 mt-2.5 relative z-20">
        <div className="bg-white rounded-2xl p-4 sm:p-5 shadow-sm border border-[#e8e2d5] space-y-3.5">
          {/* Header Row: Title, Verification, Call Shop */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h1 className="font-display font-bold text-xl sm:text-2xl text-[#123324] leading-tight truncate">
                {shop.name}
              </h1>
              <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>{isHindi ? "सत्यापित स्थानीय दुकान" : "VERIFIED DUKAAN"}</span>
                </span>
                <span className="text-[11px] text-[#6d756f]">
                  {shop.city}, {shop.state}
                </span>
              </div>
            </div>

            {/* Call Shop Button */}
            {shop.contact_number && (
              <a
                href={`tel:${shop.contact_number}`}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs font-bold hover:bg-emerald-100 transition shadow-2xs shrink-0"
                title={isHindi ? "दुकानदार को कॉल करें" : "Call Shop"}
              >
                <Phone className="w-3.5 h-3.5 text-emerald-600" />
                <span>{isHindi ? "कॉल करें" : "Call"}</span>
              </a>
            )}
          </div>

          {/* Description Quote Box */}
          <div className="rounded-xl border border-[#e8e2d5] bg-[#faf8f3] px-3.5 py-2 text-xs italic text-[#556057] leading-relaxed">
            &ldquo;{shop.description || (isHindi ? "100% शुद्ध गुणवत्ता • घर तक डिलीवरी एवं स्टोर पिकअप सुविधा उपलब्ध" : "100% Genuine Quality • Fast Home Delivery & Store Pickup Available")}&rdquo;
          </div>

          {/* Address with Google Maps link */}
          {shop.google_maps_url ? (
            <a
              href={shop.google_maps_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-xs text-[#1F5D42] hover:text-[#123324] hover:underline font-medium transition"
              title={isHindi ? "गूगल मैप्स पर दिशा-निर्देश देखें" : "Get directions on Google Maps"}
            >
              <MapPin className="w-4 h-4 text-[#E8A33D] shrink-0" />
              <span className="truncate">
                {shop.address_line ? `${shop.address_line}, ` : ""}
                {shop.area ? `${shop.area}, ` : ""}
                {shop.city} - {shop.pincode}
              </span>
              <ExternalLink className="w-3 h-3 text-[#1F5D42]/80 shrink-0" />
            </a>
          ) : (
            <div className="flex items-center gap-2 text-xs text-[#556057]">
              <MapPin className="w-4 h-4 text-[#1F5D42] shrink-0" />
              <span className="truncate">
                {shop.address_line ? `${shop.address_line}, ` : ""}
                {shop.area ? `${shop.area}, ` : ""}
                {shop.city} - {shop.pincode}
              </span>
            </div>
          )}

          {/* 4. STORE OPEN NOW & TIMINGS GREEN BANNER (Schedule dropdown removed per instructions) */}
          <div className="rounded-2xl bg-[#0c4a2f] text-white p-3.5 shadow-sm border border-[#1b6a45]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 font-bold text-xs sm:text-sm tracking-wide">
                  <span className={`w-2.5 h-2.5 rounded-full ${isClosed ? "bg-red-400" : "bg-emerald-400 animate-pulse"}`} />
                  <span>
                    {isClosed
                      ? isHindi
                        ? "STORE CLOSED (दुकान अभी बंद है)"
                        : "STORE CURRENTLY CLOSED"
                      : isHindi
                      ? "STORE OPEN NOW (दुकान खुली है)"
                      : "STORE OPEN NOW"}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-emerald-200/90 mt-1">
                  <Clock className="w-3.5 h-3.5 text-[#E8A33D]" />
                  <span>
                    {isHindi ? "आज का समय" : "Today"}: {openTime} - {closeTime}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 4. Delivery Mode & Fulfillment Badges (Fixed WhatsApp confirmation display) */}
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-0.5 text-xs">
            {shop.is_home_delivery_enabled && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#e7f2eb] text-[#1F5D42] border border-[#cbe1d5] text-xs font-bold shrink-0">
                {shop.delivery_fee_type === "CONFIRMED_ON_WHATSAPP" ? (
                  <>
                    <MessageSquare className="w-3.5 h-3.5 text-[#1F5D42]" />
                    <span>{isHindi ? "डिलीवरी शुल्क: व्हाट्सएप पर तय होगा" : "Delivery: Confirm on WhatsApp"}</span>
                  </>
                ) : (
                  <>
                    <Bike className="w-3.5 h-3.5 text-[#1F5D42]" />
                    <span>
                      {parseFloat(shop.delivery_charge) === 0
                        ? isHindi
                          ? "मुफ्त होम डिलीवरी"
                          : "Free Home Delivery"
                        : `${isHindi ? "डिलीवरी शुल्क" : "Delivery"} ₹${shop.delivery_charge}`}
                    </span>
                  </>
                )}
              </div>
            )}

            {shop.is_pickup_enabled && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#FAF8F3] text-[#556057] border border-[#ddd6ca] text-xs font-semibold shrink-0">
                <ShoppingBag className="w-3.5 h-3.5 text-[#1F5D42]" />
                <span>{isHindi ? "दुकान से पिकअप उपलब्ध" : "Store Pickup Allowed"}</span>
              </div>
            )}
          </div>

          {/* 5. Embedded Search Bar */}
          {onSearchChange && (
            <div className="pt-1">
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => onSearchChange(e.target.value)}
                  placeholder={isHindi ? "आटा, दाल, चावल, बिस्कुट खोजें…" : "Search atta, dal, rice, biscuits…"}
                  className="w-full bg-[#FAF8F3] text-[#17251e] placeholder-slate-400 rounded-2xl py-3 pl-10 pr-4 text-xs sm:text-sm font-body outline-none border border-[#ddd6ca] shadow-2xs focus:border-[#1F5D42] focus:bg-white transition"
                />
                <span className="absolute left-3.5 top-3 text-slate-400 font-bold">⌕</span>
                {searchQuery && (
                  <button
                    onClick={() => onSearchChange("")}
                    className="absolute right-3.5 top-3 text-xs text-slate-400 hover:text-slate-600 font-bold"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
