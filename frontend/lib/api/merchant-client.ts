import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!baseURL) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
}

export const merchantClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

merchantClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = sessionStorage.getItem("merchant_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string> | null = null;

function expireMerchantSession() {
  sessionStorage.removeItem("merchant_access_token");
  sessionStorage.removeItem("merchant_refresh_token");
  sessionStorage.removeItem("merchant_must_change_password");
  window.dispatchEvent(new Event("merchant-session-expired"));
}

merchantClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    if (error.response?.status !== 401 || request?._merchantRetry || request?.url?.includes("/auth/")) {
      return Promise.reject(error);
    }
    if (typeof window === "undefined") return Promise.reject(error);

    const refresh = sessionStorage.getItem("merchant_refresh_token");
    if (!refresh) {
      expireMerchantSession();
      return Promise.reject(error);
    }

    request._merchantRetry = true;
    try {
      refreshing ??= axios
        .post(`${baseURL}/auth/refresh/`, { refresh })
        .then(({ data }) => {
          sessionStorage.setItem("merchant_access_token", data.access);
          sessionStorage.setItem("merchant_refresh_token", data.refresh);
          return data.access as string;
        })
        .finally(() => {
          refreshing = null;
        });
      const access = await refreshing;
      request.headers.Authorization = `Bearer ${access}`;
      return merchantClient(request);
    } catch (refreshError) {
      expireMerchantSession();
      return Promise.reject(refreshError);
    }
  },
);
