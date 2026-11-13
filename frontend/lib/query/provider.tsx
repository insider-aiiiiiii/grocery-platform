"use client";

import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "./client";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>;
}
