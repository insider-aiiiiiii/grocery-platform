import { QueryClient } from "@tanstack/react-query";

/**
 * One QueryClient for the whole browser tab, importable from non-React code (API clients).
 * Everything cached here belongs to whoever is signed in, so it must be cleared on sign-out,
 * session expiry and sign-in: otherwise the next person on a shared tab briefly sees the
 * previous person's orders and customers.
 */
let browserClient: QueryClient | undefined;

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  });
}

export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") return makeQueryClient();
  browserClient ??= makeQueryClient();
  return browserClient;
}

export function clearQueryCache() {
  browserClient?.clear();
}
