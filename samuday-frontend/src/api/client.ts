/**
 * Centralized API client with JWT auth headers.
 */

const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1';

function getToken(): string | null {
  return localStorage.getItem('samuday_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
  }
  return { 'Content-Type': 'application/json' };
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
  });
  
  const data = await res.json().catch(() => null);
  
  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  
  return data;
}

export async function apiUpload(path: string, formData: FormData): Promise<any> {
  const url = `${API_BASE}${path}`;
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: formData
  });
  
  const data = await res.json().catch(() => null);
  
  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  
  return data;
}

// Auth
export const authAPI = {
  googleLogin: (credential: string) => apiFetch('/identity/auth/google', { method: 'POST', body: JSON.stringify({ credential }) }),
  requestOTP: (phone: string) => apiFetch('/identity/auth/request-otp', { method: 'POST', body: JSON.stringify({ phone_number: phone }) }),
  verifyOTP: (phone: string, otp: string) => apiFetch('/identity/auth/verify-otp', { method: 'POST', body: JSON.stringify({ phone_number: phone, otp_code: otp }) }),
  register: (phone: string, otp: string, name: string, lang: string) =>
    apiFetch(`/identity/auth/register?otp_code=${otp}`, { method: 'POST', body: JSON.stringify({ phone_number: phone, full_name: name, preferred_language: lang }) }),
  getMe: () => apiFetch('/identity/me'),
  updateProfile: (data: any) => apiFetch('/identity/me', { method: 'PUT', body: JSON.stringify(data) }),
};

// Marketplace
export const marketAPI = {
  getCategories: () => apiFetch('/marketplace/categories'),
  getListings: (params?: string) => apiFetch(`/marketplace/listings${params ? '?' + params : ''}`),
  getListing: (id: string) => apiFetch(`/marketplace/listings/${id}`),
  createListing: (data: any) => apiFetch('/marketplace/listings', { method: 'POST', body: JSON.stringify(data) }),
  uploadImage: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return apiUpload('/marketplace/upload', fd);
  }
};

// Cart
export const cartAPI = {
  getCart: () => apiFetch('/cart'),
  addToCart: (listingId: string, qty: number = 1) => apiFetch('/cart', { method: 'POST', body: JSON.stringify({ listing_id: listingId, quantity: qty }) }),
  updateItem: (itemId: string, qty: number) => apiFetch(`/cart/${itemId}`, { method: 'PUT', body: JSON.stringify({ quantity: qty }) }),
  removeItem: (itemId: string) => apiFetch(`/cart/${itemId}`, { method: 'DELETE' }),
  clearCart: () => apiFetch('/cart', { method: 'DELETE' }),
  getCount: () => apiFetch('/cart/count'),
};

// Wallet
export const walletAPI = {
  getBalance: () => apiFetch('/wallet/balance'),
};

// Promotions
export const promoAPI = {
  getSaleEvents: () => apiFetch('/promotions/sales'),
  getAds: (placement?: string) => apiFetch(`/promotions/ads${placement ? '?placement=' + placement : ''}`),
  createSaleEvent: (data: any) => apiFetch('/promotions/sales', { method: 'POST', body: JSON.stringify(data) }),
  createAd: (data: any) => apiFetch('/promotions/ads', { method: 'POST', body: JSON.stringify(data) }),
  clickAd: (id: string) => apiFetch(`/promotions/ads/${id}/click`, { method: 'POST' }),
};

// Orders
export const orderAPI = {
  createOrder: (data: any) => apiFetch('/marketplace/orders', { method: 'POST', body: JSON.stringify(data) }),
};

// AI Suite
export const aiAPI = {
  transcribeAudio: (audioBlob: Blob) => {
    const fd = new FormData();
    fd.append('file', audioBlob, 'voice.webm');
    return apiUpload('/ai/transcribe', fd);
  },

  generateImages: (primaryImageUrl: string, title: string, category?: string) =>
    apiFetch('/ai/generate-images', { method: 'POST', body: JSON.stringify({ primary_image_url: primaryImageUrl, title, category }) }),

  generateListing: (shortSummary: string, audioUrl?: string, language: string = 'en') =>
    apiFetch('/ai/generate-listing', { method: 'POST', body: JSON.stringify({ short_summary: shortSummary, audio_url: audioUrl, language }) }),

  runSellerAgent: (prompt: string) =>
    apiFetch('/ai/seller-agent', { method: 'POST', body: JSON.stringify({ prompt }) }),

  getSellerInsights: () => apiFetch('/ai/seller-insights'),

  autoReplyReview: (buyerName: string, rating: number, reviewText: string, productTitle: string) =>
    apiFetch('/ai/reviews/auto-reply', { method: 'POST', body: JSON.stringify({ buyer_name: buyerName, rating, review_text: reviewText, product_title: productTitle }) }),

  getReviewAnalytics: () => apiFetch('/ai/reviews/analytics'),

  copilotChat: (query: string, language: string = 'en') =>
    apiFetch('/ai/copilot/chat', { method: 'POST', body: JSON.stringify({ query, language }) }),
};
