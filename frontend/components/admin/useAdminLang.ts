"use client";

import { useSyncExternalStore } from "react";

export type AdminLang = "en" | "hi";

function subscribe(onChange: () => void) {
  window.addEventListener("admin-lang-changed", onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener("admin-lang-changed", onChange);
    window.removeEventListener("storage", onChange);
  };
}

function getSnapshot(): AdminLang {
  try {
    return localStorage.getItem("super_admin_language") === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
}

/** Reads the super admin language (localStorage `super_admin_language`) and follows `admin-lang-changed`. */
export function useAdminLang(): AdminLang {
  return useSyncExternalStore(subscribe, getSnapshot, () => "en" as AdminLang);
}
