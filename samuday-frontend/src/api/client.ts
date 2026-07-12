/**
 * Centralized API client with JWT auth headers.
 * Access tokens are short-lived (60 min); a 401 triggers a silent refresh-token
 * exchange and a single retry before falling back to forcing re-login.
 */

const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1';
const TOKEN_KEY = 'samuday_token';
const REFRESH_KEY = 'samuday_refresh_token';

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// Shared in-flight promise so concurrent 401s trigger one refresh call, not a
// stampede that would otherwise race to rotate/invalidate each other's refresh token.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/identity/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return null;
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return data.access_token as string;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

// Notifies AuthContext to clear React state; components can't be imported here.
function handleSessionExpired() {
  clearTokens();
  window.dispatchEvent(new Event('samuday:session-expired'));
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
  }
  return { 'Content-Type': 'application/json' };
}

async function handleUnauthorized(): Promise<boolean> {
  const newToken = await refreshAccessToken();
  if (newToken) return true;
  handleSessionExpired();
  return false;
}

export async function apiFetch(path: string, options: RequestInit = {}, _retried = false): Promise<any> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers as Record<string, string> || {}) },
  });

  if (res.status === 401 && !_retried && getToken()) {
    if (await handleUnauthorized()) return apiFetch(path, options, true);
    throw new Error('Your session has expired. Please log in again.');
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }

  return data;
}

export async function apiUpload(path: string, formData: FormData, _retried = false): Promise<any> {
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

  if (res.status === 401 && !_retried && token) {
    if (await handleUnauthorized()) return apiUpload(path, formData, true);
    throw new Error('Your session has expired. Please log in again.');
  }

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
  refreshToken: (refreshToken: string) => apiFetch('/identity/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }) }),
};

// Marketplace
export const marketAPI = {
  getCategories: () => apiFetch('/marketplace/categories'),
  getListings: (params?: string) => apiFetch(`/marketplace/listings${params ? '?' + params : ''}`),
  getListing: (id: string) => apiFetch(`/marketplace/listings/${id}`),
  createListing: (data: any) => apiFetch('/marketplace/listings', { method: 'POST', body: JSON.stringify(data) }),
  updateListing: (id: string, data: any) => apiFetch(`/marketplace/listings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getMyListings: () => apiFetch('/marketplace/listings/mine'),
  pauseListing: (id: string) => apiFetch(`/marketplace/listings/${id}/pause`, { method: 'POST' }),
  reactivateListing: (id: string) => apiFetch(`/marketplace/listings/${id}/reactivate`, { method: 'POST' }),
  removeListing: (id: string) => apiFetch(`/marketplace/listings/${id}`, { method: 'DELETE' }),
  getSellerReviews: () => apiFetch('/marketplace/reviews/mine-as-seller'),
  submitReview: (data: { order_id?: string; booking_id?: string; rating: number; comment?: string }) =>
    apiFetch('/marketplace/reviews', { method: 'POST', body: JSON.stringify(data) }),
  updateReview: (reviewId: string, data: { rating?: number; comment?: string }) =>
    apiFetch(`/marketplace/reviews/${reviewId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteReview: (reviewId: string) => apiFetch(`/marketplace/reviews/${reviewId}`, { method: 'DELETE' }),
  replyToReview: (reviewId: string, reply: string) =>
    apiFetch(`/marketplace/reviews/${reviewId}/reply`, { method: 'POST', body: JSON.stringify({ reply }) }),
  getListingReviews: (listingId: string) => apiFetch(`/marketplace/listings/${listingId}/reviews`),
  getSellerProfile: (sellerId: string) => apiFetch(`/marketplace/sellers/${sellerId}`),
  getSellerListings: (sellerId: string) => apiFetch(`/marketplace/sellers/${sellerId}/listings`),
  uploadImage: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return apiUpload('/marketplace/upload', fd);
  },
  // Address book
  getAddresses: () => apiFetch('/marketplace/addresses'),
  createAddress: (data: any) => apiFetch('/marketplace/addresses', { method: 'POST', body: JSON.stringify(data) }),
  deleteAddress: (id: string) => apiFetch(`/marketplace/addresses/${id}`, { method: 'DELETE' }),
  // Geocoding (GPS auto-detect / manual search) — free OpenStreetMap, no API key
  reverseGeocode: (lat: number, lng: number) => apiFetch(`/marketplace/geocode/reverse?lat=${lat}&lng=${lng}`),
  searchAddress: (q: string) => apiFetch(`/marketplace/geocode/search?q=${encodeURIComponent(q)}`),
};

// Shipping / Delhivery
export const shippingAPI = {
  getStatus: () => apiFetch('/shipping/status'),
  getMyDispatchProfile: () => apiFetch('/shipping/dispatch-profile'),
  upsertDispatchProfile: (data: any) => apiFetch('/shipping/dispatch-profile', { method: 'PUT', body: JSON.stringify(data) }),
  getRate: (listingId: string, quantity: number, destinationPincode: string) =>
    apiFetch('/shipping/rate', { method: 'POST', body: JSON.stringify({ listing_id: listingId, quantity, destination_pincode: destinationPincode }) }),
  trackOrder: (orderId: string) => apiFetch(`/shipping/track/${orderId}`),
};

// Seller verification (Official business tier + Local KYC tier)
export const verificationAPI = {
  submitOfficialProfile: (data: any) => apiFetch('/enterprise/supplier/profile', { method: 'POST', body: JSON.stringify(data) }),
  submitLocalKyc: (data: any) => apiFetch('/identity/kyc', { method: 'POST', body: JSON.stringify(data) }),
  // Admin review
  listPendingOfficial: () => apiFetch('/enterprise/admin/verifications/pending'),
  approveOfficial: (id: string) => apiFetch(`/enterprise/admin/verifications/${id}/approve`, { method: 'POST' }),
  rejectOfficial: (id: string, reason?: string) => apiFetch(`/enterprise/admin/verifications/${id}/reject`, { method: 'POST', body: JSON.stringify({ rejection_reason: reason }) }),
  listPendingLocal: () => apiFetch('/identity/admin/kyc/pending'),
  approveLocal: (id: string) => apiFetch(`/identity/admin/kyc/${id}/approve`, { method: 'POST' }),
  rejectLocal: (id: string, reason?: string) => apiFetch(`/identity/admin/kyc/${id}/reject`, { method: 'POST', body: JSON.stringify({ rejection_reason: reason }) }),
};

// Platform Admin
export const adminAPI = {
  getOverview: () => apiFetch('/admin/overview'),
  listSellers: (tier?: string, status?: string) => {
    const params = new URLSearchParams();
    if (tier) params.set('tier', tier);
    if (status) params.set('verification_status', status);
    return apiFetch(`/admin/sellers${params.toString() ? '?' + params.toString() : ''}`);
  },
  listListings: (limit = 100) => apiFetch(`/admin/listings?limit=${limit}`),
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
  getLedger: () => apiFetch('/wallet/ledger'),
  checkout: (amountPaise: number) => apiFetch(`/wallet/payment/checkout?amount=${amountPaise}`, { method: 'POST' }),
  verifyCallback: (gatewayOrderId: string, paymentId: string, signature: string) =>
    apiFetch(`/wallet/payment/callback?gateway_order_id=${encodeURIComponent(gatewayOrderId)}&payment_id=${encodeURIComponent(paymentId)}&signature=${encodeURIComponent(signature)}`, { method: 'POST' }),
};

// Promotions
export const promoAPI = {
  getSaleEvents: () => apiFetch('/promotions/sales'),
  getMySales: () => apiFetch('/promotions/sales/mine'),
  deleteSaleEvent: (id: string) => apiFetch(`/promotions/sales/${id}`, { method: 'DELETE' }),
  getAds: (placement?: string) => apiFetch(`/promotions/ads${placement ? '?placement=' + placement : ''}`),
  getMyAds: () => apiFetch('/promotions/ads/mine'),
  deleteAd: (id: string) => apiFetch(`/promotions/ads/${id}`, { method: 'DELETE' }),
  createSaleEvent: (data: any) => apiFetch('/promotions/sales', { method: 'POST', body: JSON.stringify(data) }),
  createAd: (data: any) => apiFetch('/promotions/ads', { method: 'POST', body: JSON.stringify(data) }),
  clickAd: (id: string) => apiFetch(`/promotions/ads/${id}/click`, { method: 'POST' }),
  getSaleEventDetail: (id: string) => apiFetch(`/promotions/sales/${id}`),
  getAdDetail: (id: string) => apiFetch(`/promotions/ads/${id}`),
};

// Orders
export const orderAPI = {
  createOrder: (data: any) => apiFetch('/marketplace/orders', { method: 'POST', body: JSON.stringify(data) }),
  getMyOrders: (role: 'buyer' | 'seller' = 'buyer') => apiFetch(`/marketplace/orders/mine?role=${role}`),
  completeOrder: (id: string) => apiFetch(`/marketplace/orders/${id}/complete`, { method: 'POST' }),
  cancelOrder: (id: string) => apiFetch(`/marketplace/orders/${id}/cancel`, { method: 'POST' }),
};

// Kutumb Network (family registration, community groups, matrimonial layer)
function toQuery(params: Record<string, string | boolean | number | undefined>): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)); });
  return q.toString() ? '?' + q.toString() : '';
}

export const kutumbAPI = {
  // Family registry
  createFamily: (name: string) => apiFetch('/kutumb/families', { method: 'POST', body: JSON.stringify({ name }) }),
  addFamilyMember: (familyId: string, data: any) =>
    apiFetch(`/kutumb/families/${familyId}/members`, { method: 'POST', body: JSON.stringify(data) }),
  getMyFamily: () => apiFetch('/kutumb/families/me'),
  getFamilyInvites: () => apiFetch('/kutumb/families/invites'),
  respondFamilyInvite: (memberId: string, accept: boolean) =>
    apiFetch(`/kutumb/families/members/${memberId}/respond`, { method: 'POST', body: JSON.stringify({ accept }) }),
  updateMemberVisibility: (memberId: string, data: { visible_phone?: boolean; visible_kyc?: boolean }) =>
    apiFetch(`/kutumb/families/members/${memberId}/visibility`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Community groups
  createGroup: (data: any) => apiFetch('/kutumb/groups', { method: 'POST', body: JSON.stringify(data) }),
  getGroups: (geohashPrefix?: string) => apiFetch(`/kutumb/groups${toQuery({ geohash_prefix: geohashPrefix })}`),
  getMyGroups: () => apiFetch('/kutumb/groups/mine'),
  joinGroup: (groupId: string) => apiFetch(`/kutumb/groups/${groupId}/join`, { method: 'POST' }),
  leaveGroup: (groupId: string) => apiFetch(`/kutumb/groups/${groupId}/leave`, { method: 'POST' }),

  // Matrimonial layer
  optInMatrimonial: (data: any) => apiFetch('/kutumb/matrimonial/opt-in', { method: 'POST', body: JSON.stringify(data) }),
  getMyMatrimonialProfile: () => apiFetch('/kutumb/matrimonial/me'),
  updateMatrimonialProfile: (data: any) => apiFetch('/kutumb/matrimonial/me', { method: 'PATCH', body: JSON.stringify(data) }),
  optOutMatrimonial: () => apiFetch('/kutumb/matrimonial/opt-out', { method: 'POST' }),
  searchMatrimonial: (params: Record<string, string | boolean | number | undefined>) =>
    apiFetch(`/kutumb/matrimonial/search${toQuery(params)}`),
  sendInterest: (toUserId: string) =>
    apiFetch('/kutumb/matrimonial/interests', { method: 'POST', body: JSON.stringify({ to_user_id: toUserId }) }),
  getMyInterests: (direction: 'sent' | 'received') => apiFetch(`/kutumb/matrimonial/interests${toQuery({ direction })}`),
  respondInterest: (interestId: string, action: 'accept' | 'decline' | 'withdraw') =>
    apiFetch(`/kutumb/matrimonial/interests/${interestId}`, { method: 'PATCH', body: JSON.stringify({ action }) }),

  // Safety: blocking & reporting
  blockUser: (blockedUserId: string) => apiFetch('/kutumb/blocks', { method: 'POST', body: JSON.stringify({ blocked_user_id: blockedUserId }) }),
  getMyBlocks: () => apiFetch('/kutumb/blocks'),
  unblockUser: (blockedUserId: string) => apiFetch(`/kutumb/blocks/${blockedUserId}`, { method: 'DELETE' }),
  submitReport: (reportedUserId: string, reasonCode: string, details?: string) =>
    apiFetch('/kutumb/reports', { method: 'POST', body: JSON.stringify({ reported_user_id: reportedUserId, reason_code: reasonCode, details }) }),

  // Admin moderation
  adminListReports: (statusFilter?: string, reasonCode?: string) =>
    apiFetch(`/kutumb/admin/reports${toQuery({ status: statusFilter, reason_code: reasonCode })}`),
  adminResolveReport: (reportId: string, action: string, note?: string) =>
    apiFetch(`/kutumb/admin/reports/${reportId}/resolve`, { method: 'POST', body: JSON.stringify({ action, note }) }),
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

  generateAd: (listingId: string) =>
    apiFetch('/ai/generate-ad', { method: 'POST', body: JSON.stringify({ listing_id: listingId }) }),
};
