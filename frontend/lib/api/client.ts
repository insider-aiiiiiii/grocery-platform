import axios from "axios";
import { clearQueryCache } from "@/lib/query/client";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!baseURL) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
}

export const apiClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// Request Interceptor: attach Authorization: Bearer <token>
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = sessionStorage.getItem("admin_access_token");
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response Interceptor: on 401 response, attempt refresh via POST /auth/refresh/ using admin_refresh_token
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/")
    ) {
      if (typeof window === "undefined") {
        return Promise.reject(error);
      }

      const refreshToken = sessionStorage.getItem("admin_refresh_token");
      if (!refreshToken) {
        sessionStorage.removeItem("admin_access_token");
        sessionStorage.removeItem("admin_refresh_token");
        if (window.location.pathname.startsWith("/admin") && window.location.pathname !== "/admin/login") {
          window.location.href = "/admin/login";
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await axios.post(`${baseURL}/auth/refresh/`, {
          refresh: refreshToken,
        });
        const newAccessToken = refreshResponse.data.access;
        sessionStorage.setItem("admin_access_token", newAccessToken);
        if (refreshResponse.data.refresh) {
          sessionStorage.setItem("admin_refresh_token", refreshResponse.data.refresh);
        }

        apiClient.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        processQueue(null, newAccessToken);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        sessionStorage.removeItem("admin_access_token");
        sessionStorage.removeItem("admin_refresh_token");
        if (window.location.pathname.startsWith("/admin") && window.location.pathname !== "/admin/login") {
          window.location.href = "/admin/login";
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Ends the admin session on the SERVER (revokes the refresh token) and then clears the browser.
 * Clearing only the browser would leave a copied refresh token valid for 30 days.
 */
export async function signOutAdmin(): Promise<void> {
  const refresh = typeof window !== "undefined" ? sessionStorage.getItem("admin_refresh_token") : null;
  try {
    if (refresh) await apiClient.post("/auth/logout/", { refresh });
  } catch {
    // Already expired or offline: still sign out locally below.
  } finally {
    ["admin_access_token", "admin_refresh_token"].forEach((k) => sessionStorage.removeItem(k));
    ["admin_user", "admin_remember", "admin_username"].forEach((k) => localStorage.removeItem(k));
    clearQueryCache();
  }
}
