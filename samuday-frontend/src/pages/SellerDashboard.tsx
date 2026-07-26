import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { promoAPI, marketAPI, aiAPI, shippingAPI, orderAPI } from '../api/client';
import { PublishProductModal } from '../components/seller/PublishProductModal';
import { PublishJobModal } from '../components/seller/PublishJobModal';
import { PublishAgriModal } from '../components/seller/PublishAgriModal';
import { JobApplicantsModal } from '../components/seller/JobApplicantsModal';
import { SellerOnboarding } from '../components/seller/SellerOnboarding';
import { EditListingModal } from '../components/seller/EditListingModal';
import { renderFormattedText } from '../utils/textFormat';
import {
  Package, Megaphone, TrendingUp, Plus, LayoutDashboard, Sparkles,
  Bot, Star, Send, BellRing, CheckCircle2, AlertTriangle, Info, Trash2, Upload,
  Truck, Warehouse, MapPin
} from 'lucide-react';
import { FALLBACK_IMAGE } from '../utils/placeholder';

export const SellerDashboard: React.FC = () => {
  const { user } = useAuth();
  const [tab, setTab] = useState<'overview' | 'listings' | 'orders' | 'dispatch' | 'ai_agent' | 'reviews' | 'sales' | 'ads'>('overview');
  const [listings, setListings] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [mySales, setMySales] = useState<any[]>([]);
  const [myAds, setMyAds] = useState<any[]>([]);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [isPublishJobModalOpen, setIsPublishJobModalOpen] = useState(false);
  const [isPublishAgriModalOpen, setIsPublishAgriModalOpen] = useState(false);
  const [applicantsFor, setApplicantsFor] = useState<{ id: string; title: string } | null>(null);
  const [editingListingId, setEditingListingId] = useState<string | null>(null);
  const [listingActionId, setListingActionId] = useState<string | null>(null);

  // Orders (as seller) & dispatch profile
  const [myOrders, setMyOrders] = useState<any[]>([]);
  const [dispatchProfile, setDispatchProfile] = useState<any>(null);
  const [dispatchForm, setDispatchForm] = useState({
    contact_name: '', contact_phone: '', pickup_address_line1: '', pickup_address_line2: '',
    pickup_city: '', pickup_state: '', pickup_pincode: '',
  });
  const [dispatchSaving, setDispatchSaving] = useState(false);
  const [dispatchSuccess, setDispatchSuccess] = useState('');
  const [delhiveryConnected, setDelhiveryConnected] = useState(false);

  // AI Seller Agent States
  const [agentPrompt, setAgentPrompt] = useState('');
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentMessages, setAgentMessages] = useState<Array<{ sender: 'user' | 'agent'; text: string; tools?: any[] }>>([
    {
      sender: 'agent',
      text: '🤖 **Hello Seller!** I am your AI Business Advisor. I constantly monitor your catalog, prices, and inventory levels. Ask me to run diagnostic tools or optimize your listings!',
      tools: []
    }
  ]);

  // AI Insights & Notifications
  const [aiInsights, setAiInsights] = useState<any>(null);

  // Review Analytics & Auto-Reply
  const [reviewAnalytics, setReviewAnalytics] = useState<any>(null);
  const [reviewsList, setReviewsList] = useState<any[]>([]);
  const [replyPostingId, setReplyPostingId] = useState<string | null>(null);
  const [aiDraftingId, setAiDraftingId] = useState<string | null>(null);
  const [editingReplyId, setEditingReplyId] = useState<string | null>(null);

  // Forms
  const [saleTitle, setSaleTitle] = useState('');
  const [saleDesc, setSaleDesc] = useState('');
  const [saleDiscount, setSaleDiscount] = useState(20);
  const [saleBanner, setSaleBanner] = useState('');
  const [saleBannerUploading, setSaleBannerUploading] = useState(false);
  const [saleSubmitting, setSaleSubmitting] = useState(false);
  const [saleSuccess, setSaleSuccess] = useState('');
  const [saleDeletingId, setSaleDeletingId] = useState<string | null>(null);
  const [saleApplyAll, setSaleApplyAll] = useState(true);
  const [saleSelectedIds, setSaleSelectedIds] = useState<Set<string>>(new Set());
  const [saleOverrides, setSaleOverrides] = useState<Record<string, string>>({});

  const [adTitle, setAdTitle] = useState('');
  const [adImage, setAdImage] = useState('');
  const [adImageUploading, setAdImageUploading] = useState(false);
  const [adPlacement, setAdPlacement] = useState('hero_banner');
  const [adSubmitting, setAdSubmitting] = useState(false);
  const [adSuccess, setAdSuccess] = useState('');
  const [adDeletingId, setAdDeletingId] = useState<string | null>(null);
  const [adListingId, setAdListingId] = useState('');
  const [adGenerating, setAdGenerating] = useState(false);
  const [aiNoticeAd, setAiNoticeAd] = useState('');

  const loadData = async () => {
    if (user?.is_seller) {
      marketAPI.getCategories().then(setCategories).catch(() => {});
      marketAPI.getMyListings().then(setListings).catch(() => {});
      promoAPI.getMySales().then(setMySales).catch(() => setMySales([]));
      promoAPI.getMyAds().then(setMyAds).catch(() => setMyAds([]));
      aiAPI.getSellerInsights().then(setAiInsights).catch(() => {});
      aiAPI.getReviewAnalytics().then(setReviewAnalytics).catch(() => {});
      marketAPI.getSellerReviews().then(rows => setReviewsList(
        rows.map((r: any) => ({
          id: r.id, buyer_name: r.buyer_name, rating: r.rating, review_text: r.review_text,
          product_title: r.product_title, date: new Date(r.created_at).toLocaleDateString('en-IN'),
          reply: r.seller_reply || null, draftReply: r.seller_reply || '',
        }))
      )).catch(() => setReviewsList([]));
      orderAPI.getMyOrders('seller').then(setMyOrders).catch(() => setMyOrders([]));
      shippingAPI.getStatus().then(s => setDelhiveryConnected(s.delhivery_connected)).catch(() => {});
      shippingAPI.getMyDispatchProfile().then(p => {
        setDispatchProfile(p);
        setDispatchForm({
          contact_name: p.contact_name, contact_phone: p.contact_phone,
          pickup_address_line1: p.pickup_address_line1, pickup_address_line2: p.pickup_address_line2 || '',
          pickup_city: p.pickup_city, pickup_state: p.pickup_state, pickup_pincode: p.pickup_pincode,
        });
      }).catch(() => setDispatchProfile(null));
    }
  };

  const handleSaveDispatchProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setDispatchSaving(true);
    setDispatchSuccess('');
    try {
      const saved = await shippingAPI.upsertDispatchProfile(dispatchForm);
      setDispatchProfile(saved);
      setDispatchSuccess('Dispatch info saved! Courier delivery is now available for your listings.');
    } catch (e: any) {
      setDispatchSuccess('Error: ' + (e.message || 'Failed to save'));
    }
    setDispatchSaving(false);
  };

  useEffect(() => {
    loadData();
  }, [user]);

  const handleRunAgent = async (customPrompt?: string) => {
    const p = customPrompt || agentPrompt;
    if (!p.trim()) return;

    const updated = [...agentMessages, { sender: 'user' as const, text: p }];
    setAgentMessages(updated);
    setAgentPrompt('');
    setAgentLoading(true);

    try {
      const res = await aiAPI.runSellerAgent(p);
      setAgentMessages([...updated, { sender: 'agent', text: res.reply, tools: res.tools_executed }]);
    } catch {
      setAgentMessages([...updated, { sender: 'agent', text: 'Sorry, AI agent diagnostic service is currently busy.' }]);
    }
    setAgentLoading(false);
  };

  const handleAutoReplyReview = async (reviewId: string, buyerName: string, rating: number, text: string, title: string) => {
    setAiDraftingId(reviewId);
    try {
      const res = await aiAPI.autoReplyReview(buyerName, rating, text, title);
      setReviewsList(prev => prev.map(r => r.id === reviewId ? { ...r, draftReply: res.ai_reply } : r));
    } catch {
      alert('Failed to generate AI auto-reply');
    }
    setAiDraftingId(null);
  };

  const handleDraftReplyChange = (reviewId: string, value: string) => {
    setReviewsList(prev => prev.map(r => r.id === reviewId ? { ...r, draftReply: value } : r));
  };

  const handlePostReply = async (reviewId: string) => {
    const review = reviewsList.find(r => r.id === reviewId);
    if (!review || !review.draftReply?.trim()) return;
    setReplyPostingId(reviewId);
    try {
      await marketAPI.replyToReview(reviewId, review.draftReply.trim());
      setReviewsList(prev => prev.map(r => r.id === reviewId ? { ...r, reply: review.draftReply.trim() } : r));
      setEditingReplyId(null);
    } catch (e: any) {
      alert('Failed to post reply: ' + (e.message || 'Unknown error'));
    }
    setReplyPostingId(null);
  };

  const toggleSaleListing = (id: string) => {
    setSaleSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleCreateSale = async () => {
    setSaleSubmitting(true);
    setSaleSuccess('');
    try {
      const now = new Date();
      const overrides: Record<string, number> = {};
      Object.entries(saleOverrides).forEach(([id, val]) => {
        const n = parseInt(val);
        if (val.trim() !== '' && !isNaN(n)) overrides[id] = n;
      });
      await promoAPI.createSaleEvent({
        title: saleTitle,
        description: saleDesc,
        banner_image_url: saleBanner || 'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&h=400&fit=crop',
        discount_percent: saleDiscount,
        start_date: now.toISOString(),
        end_date: new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        listing_ids: saleApplyAll ? [] : Array.from(saleSelectedIds),
        overrides,
      });
      setSaleSuccess('Sale event created! It will appear on the homepage.');
      setSaleTitle(''); setSaleDesc(''); setSaleBanner(''); setSaleSelectedIds(new Set()); setSaleOverrides({}); setSaleApplyAll(true);
      loadData();
    } catch (e: any) {
      setSaleSuccess('Error: ' + (e.message || 'Failed'));
    }
    setSaleSubmitting(false);
  };

  const handleGenerateAd = async () => {
    if (!adListingId) return;
    setAdGenerating(true);
    setAdSuccess('');
    try {
      const listing = listings.find((l: any) => l.id === adListingId);
      const res = await aiAPI.generateAd(adListingId);
      setAdTitle(res.headline || listing?.title || '');
      if (res.image_url) setAdImage(res.image_url);
      setAiNoticeAd('✨ AI generated an ad headline' + (res.image_url ? ' and banner image' : '') + ' from this listing!');
    } catch (e: any) {
      setAdSuccess('Error: ' + (e.message || 'AI ad generation failed'));
    }
    setAdGenerating(false);
  };

  const handleCreateAd = async () => {
    setAdSubmitting(true);
    setAdSuccess('');
    try {
      const now = new Date();
      await promoAPI.createAd({
        title: adTitle,
        image_url: adImage || 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&h=400&fit=crop',
        listing_id: adListingId || undefined,
        ai_generated: !!aiNoticeAd,
        placement: adPlacement,
        start_date: now.toISOString(),
        end_date: new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000).toISOString(),
      });
      setAdSuccess('Ad placement purchased! Your ad is live.');
      setAdTitle(''); setAdImage(''); setAdListingId(''); setAiNoticeAd('');
      loadData();
    } catch (e: any) {
      setAdSuccess('Error: ' + (e.message || 'Failed'));
    }
    setAdSubmitting(false);
  };

  const handleUploadSaleBanner = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSaleBannerUploading(true);
    try {
      const res = await marketAPI.uploadImage(file);
      if (res.url) setSaleBanner(res.url);
    } catch (err: any) {
      setSaleSuccess('Error: ' + (err.message || 'Image upload failed'));
    }
    setSaleBannerUploading(false);
  };

  const handleUploadAdImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAdImageUploading(true);
    try {
      const res = await marketAPI.uploadImage(file);
      if (res.url) setAdImage(res.url);
    } catch (err: any) {
      setAdSuccess('Error: ' + (err.message || 'Image upload failed'));
    }
    setAdImageUploading(false);
  };

  const handleDeleteSaleEvent = async (id: string) => {
    if (!confirm('Take down this sale event? This cannot be undone.')) return;
    setSaleDeletingId(id);
    try {
      await promoAPI.deleteSaleEvent(id);
      setMySales(prev => prev.filter(s => s.id !== id));
    } catch (err: any) {
      alert('Failed to take down sale event: ' + (err.message || 'Unknown error'));
    }
    setSaleDeletingId(null);
  };

  const handlePauseListing = async (id: string) => {
    if (!confirm('Temporarily take this listing down? Buyers won\'t be able to see or order it until you reactivate it.')) return;
    setListingActionId(id);
    try {
      const updated = await marketAPI.pauseListing(id);
      setListings(prev => prev.map(l => l.id === id ? updated : l));
    } catch (err: any) {
      alert('Failed to pause listing: ' + (err.message || 'Unknown error'));
    }
    setListingActionId(null);
  };

  const handleReactivateListing = async (id: string) => {
    setListingActionId(id);
    try {
      const updated = await marketAPI.reactivateListing(id);
      setListings(prev => prev.map(l => l.id === id ? updated : l));
    } catch (err: any) {
      alert('Failed to reactivate listing: ' + (err.message || 'Unknown error'));
    }
    setListingActionId(null);
  };

  const handleRemoveListing = async (id: string) => {
    if (!confirm('Permanently take this listing down? This cannot be undone — buyers will never see it again.')) return;
    setListingActionId(id);
    try {
      const updated = await marketAPI.removeListing(id);
      setListings(prev => prev.map(l => l.id === id ? updated : l));
    } catch (err: any) {
      alert('Failed to remove listing: ' + (err.message || 'Unknown error'));
    }
    setListingActionId(null);
  };

  const handleDeleteAd = async (id: string) => {
    if (!confirm('Take down this advertisement? This cannot be undone.')) return;
    setAdDeletingId(id);
    try {
      await promoAPI.deleteAd(id);
      setMyAds(prev => prev.filter(a => a.id !== id));
    } catch (err: any) {
      alert('Failed to take down advertisement: ' + (err.message || 'Unknown error'));
    }
    setAdDeletingId(null);
  };

  if (!user) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Please login to access the seller dashboard</h3></div>
      </div>
    );
  }

  if (!user.is_seller || user.seller_verification_status !== 'approved') {
    return <SellerOnboarding />;
  }

  const activeListings = listings.filter((l: any) => l.status === 'active');

  const AD_PRICING: Record<string, string> = {
    hero_banner: '5,000', sidebar: '2,000', category_strip: '1,000'
  };

  return (
    <div className="page-content" style={{ paddingTop: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 4 }}>Seller Dashboard & AI Intelligence Suite</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Manage your products, AI agents, review auto-replies, and promotions</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setIsPublishModalOpen(true)}
          style={{ background: 'linear-gradient(135deg, #FF9900 0%, #E67A00 100%)', border: 'none', display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <Sparkles size={18} /> Publish Product with AI Magic
        </button>
      </div>

      {/* Live AI Alert Ticker Banner */}
      {aiInsights && (
        <div style={{ background: '#FFF8E7', border: '1px solid #FFE099', padding: '10px 16px', borderRadius: 'var(--radius-md)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <BellRing size={20} color="#E67A00" className="animate-bounce" />
          <div style={{ flex: 1, fontSize: '0.86rem', color: '#663C00' }}>
            <strong>Live AI Insight:</strong> {aiInsights.summary.ai_recommendation}
          </div>
          {aiInsights.summary.health_score !== null && (
            <span style={{ fontSize: '0.75rem', background: '#FFE099', color: '#663C00', padding: '2px 8px', borderRadius: 10, fontWeight: 600 }}>Health: {aiInsights.summary.health_score}%</span>
          )}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="dashboard-tabs">
        <button className={`dashboard-tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          <LayoutDashboard size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Overview
        </button>
        <button className={`dashboard-tab ${tab === 'listings' ? 'active' : ''}`} onClick={() => setTab('listings')}>
          <Package size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> My Listings ({listings.filter((l: any) => l.status === 'active').length})
        </button>
        <button className={`dashboard-tab ${tab === 'orders' ? 'active' : ''}`} onClick={() => setTab('orders')}>
          <Truck size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Orders ({myOrders.length})
        </button>
        <button className={`dashboard-tab ${tab === 'dispatch' ? 'active' : ''}`} onClick={() => setTab('dispatch')}>
          <Warehouse size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Dispatch Info
        </button>
        <button className={`dashboard-tab ${tab === 'ai_agent' ? 'active' : ''}`} onClick={() => setTab('ai_agent')}>
          <Bot size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> AI Seller Agent
        </button>
        <button className={`dashboard-tab ${tab === 'reviews' ? 'active' : ''}`} onClick={() => setTab('reviews')}>
          <Star size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> AI Reviews & Auto-Reply
        </button>
        <button className={`dashboard-tab ${tab === 'sales' ? 'active' : ''}`} onClick={() => setTab('sales')}>
          <TrendingUp size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Sale Events
        </button>
        <button className={`dashboard-tab ${tab === 'ads' ? 'active' : ''}`} onClick={() => setTab('ads')}>
          <Megaphone size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Advertise
        </button>
      </div>

      {/* Tab 1: Overview */}
      {tab === 'overview' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
            <div style={{ background: 'var(--bg-white)', padding: 20, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--primary)' }}>{listings.filter((l: any) => l.status === 'active').length}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Active Listings</div>
            </div>
            <div style={{ background: 'var(--bg-white)', padding: 20, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--success)' }}>{mySales.length}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Sale Events</div>
            </div>
            <div style={{ background: 'var(--bg-white)', padding: 20, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent)' }}>94%</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>AI Catalog Health</div>
            </div>
            <div style={{ background: 'var(--bg-white)', padding: 20, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#00A8E8' }}>₹48,500</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Monthly Revenue</div>
            </div>
          </div>

          {/* Live AI Notifications feed */}
          {aiInsights?.notifications && (
            <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <BellRing size={18} color="var(--primary)" /> Real-Time AI Alert Notifications
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {aiInsights.notifications.map((n: any) => (
                  <div key={n.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-body)' }}>
                    {n.type === 'success' && <CheckCircle2 size={18} color="var(--success)" style={{ marginTop: 2 }} />}
                    {n.type === 'warning' && <AlertTriangle size={18} color="#E67A00" style={{ marginTop: 2 }} />}
                    {n.type === 'info' && <Info size={18} color="var(--primary)" style={{ marginTop: 2 }} />}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{n.title}</div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{n.message}</div>
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{n.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: My Listings */}
      {tab === 'listings' && (
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Your Active Listings</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={() => setIsPublishModalOpen(true)}>
                + Add Product
              </button>
              <button className="btn btn-outline btn-sm" onClick={() => setIsPublishJobModalOpen(true)}>
                + Post a Job
              </button>
              <button className="btn btn-outline btn-sm" onClick={() => setIsPublishAgriModalOpen(true)}>
                + List Farm Produce
              </button>
            </div>
          </div>

          {listings.length === 0 ? (
            <div className="empty-state">
              <h3>No listings yet</h3>
              <p>Click "Publish Product with AI Magic" to create your first listing using voice dictation or single photo!</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {listings.map((l: any) => {
                const statusMeta: Record<string, { label: string; color: string }> = {
                  active: { label: 'Active', color: 'var(--success)' },
                  paused: { label: 'Paused (temporarily down)', color: '#E67A00' },
                  removed: { label: 'Removed (permanent)', color: 'var(--danger)' },
                  sold: { label: 'Sold', color: 'var(--text-muted)' },
                  suspended: { label: 'Suspended', color: 'var(--danger)' },
                };
                const meta = statusMeta[l.status] || { label: l.status, color: 'var(--text-muted)' };
                const busy = listingActionId === l.id;
                return (
                  <div
                    key={l.id}
                    style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', opacity: l.status === 'removed' ? 0.6 : 1 }}
                  >
                    <img
                      src={l.media?.[0]?.media_url || FALLBACK_IMAGE}
                      alt=""
                      onClick={() => setEditingListingId(l.id)}
                      style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                    />
                    <div style={{ flex: 1, cursor: 'pointer' }} onClick={() => setEditingListingId(l.id)} title="Click to view or edit this listing">
                      <div style={{ fontWeight: 600 }}>{l.title}</div>
                      {l.job_details ? (
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          {l.job_details.salary_min || l.job_details.salary_max
                            ? `₹${((l.job_details.salary_min || l.job_details.salary_max) / 100).toLocaleString('en-IN')}${l.job_details.salary_min && l.job_details.salary_max && l.job_details.salary_min !== l.job_details.salary_max ? `–₹${(l.job_details.salary_max / 100).toLocaleString('en-IN')}` : ''} / ${l.job_details.salary_period || 'month'}`
                            : 'Salary not disclosed'}
                          {' · '}{l.job_details.job_type} · {l.job_details.openings} opening{l.job_details.openings === 1 ? '' : 's'} · <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
                        </div>
                      ) : l.agri_details ? (
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          &#8377;{(l.price / 100).toLocaleString('en-IN')}/{l.unit || 'unit'} · Stock: {l.quantity || 0} {l.unit || 'units'}
                          {l.agri_details.is_organic ? ' · 🌱 Organic' : ''} · <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
                        </div>
                      ) : (
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          &#8377;{(l.price / 100).toLocaleString('en-IN')} · Stock: {l.quantity || 100} units · <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {l.job_details && (
                        <button className="btn btn-outline btn-sm" onClick={() => setApplicantsFor({ id: l.id, title: l.title })} title="View who applied">
                          Applicants
                        </button>
                      )}
                      {l.status === 'active' && (
                        <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => handlePauseListing(l.id)} title="Temporarily take this listing down (reversible)">
                          {busy ? '...' : 'Pause'}
                        </button>
                      )}
                      {l.status === 'paused' && (
                        <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => handleReactivateListing(l.id)} title="Bring this listing back live">
                          {busy ? '...' : 'Reactivate'}
                        </button>
                      )}
                      {(l.status === 'active' || l.status === 'paused') && (
                        <button
                          className="btn btn-outline btn-sm"
                          disabled={busy}
                          onClick={() => handleRemoveListing(l.id)}
                          title="Permanently take this listing down (cannot be undone)"
                          style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--danger)', borderColor: 'var(--danger)' }}
                        >
                          <Trash2 size={14} /> {busy ? '...' : 'Remove'}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Orders (as seller) */}
      {tab === 'orders' && (
        <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Orders Received</h3>
          {myOrders.length === 0 ? (
            <div className="empty-state">
              <Truck size={48} />
              <h3>No orders yet</h3>
              <p>Orders placed by buyers will show up here, along with courier tracking status.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {myOrders.map((o: any) => (
                <div key={o.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 14, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                  <img src={o.listing_image || FALLBACK_IMAGE} alt="" style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 6 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{o.listing_title || 'Product'}</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      Qty: {o.quantity} · You receive &#8377;{(o.product_amount / 100).toLocaleString('en-IN')} · {new Date(o.created_at).toLocaleDateString('en-IN')}
                    </div>
                    {o.fulfillment_type === 'courier' && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--primary)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Truck size={12} /> {o.courier_status || 'pending'} {o.is_simulated_shipment && <span style={{ color: 'var(--text-muted)' }}>(simulated — no courier account connected)</span>}
                      </div>
                    )}
                  </div>
                  <span style={{ fontSize: '0.78rem', fontWeight: 600, padding: '4px 10px', borderRadius: 12, background: 'var(--primary-soft)', color: 'var(--primary-dark)', textTransform: 'capitalize' }}>
                    {o.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Dispatch Info (pickup location required for courier fulfillment) */}
      {tab === 'dispatch' && (
        <div style={{ maxWidth: 560 }}>
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Warehouse size={18} /> Pickup / Dispatch Information
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: 8 }}>
              Required before buyers can choose courier delivery for your listings. This is where Delhivery (or our simulated estimator, until a real account is connected) will pick up packages from.
            </p>
            <div style={{ fontSize: '0.8rem', marginBottom: 16, padding: '8px 12px', borderRadius: 6, background: delhiveryConnected ? 'var(--success-light)' : 'var(--warning-light)', color: delhiveryConnected ? '#15803d' : '#92400e' }}>
              {delhiveryConnected ? '✓ Real Delhivery account connected' : '⚠ Running in simulated mode — rates/tracking are estimates until a real Delhivery account is connected'}
            </div>
            {dispatchSuccess && <div className={`alert ${dispatchSuccess.startsWith('Error') ? 'alert-error' : 'alert-success'}`}>{dispatchSuccess}</div>}
            <form onSubmit={handleSaveDispatchProfile} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-group"><label>Contact Name *</label><input value={dispatchForm.contact_name} onChange={e => setDispatchForm({ ...dispatchForm, contact_name: e.target.value })} required /></div>
              <div className="form-group"><label>Contact Phone *</label><input value={dispatchForm.contact_phone} onChange={e => setDispatchForm({ ...dispatchForm, contact_phone: e.target.value })} required /></div>
              <div className="form-group"><label>Pickup Address Line 1 *</label><input value={dispatchForm.pickup_address_line1} onChange={e => setDispatchForm({ ...dispatchForm, pickup_address_line1: e.target.value })} required /></div>
              <div className="form-group"><label>Pickup Address Line 2</label><input value={dispatchForm.pickup_address_line2} onChange={e => setDispatchForm({ ...dispatchForm, pickup_address_line2: e.target.value })} /></div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                <div className="form-group"><label>City *</label><input value={dispatchForm.pickup_city} onChange={e => setDispatchForm({ ...dispatchForm, pickup_city: e.target.value })} required /></div>
                <div className="form-group"><label>State *</label><input value={dispatchForm.pickup_state} onChange={e => setDispatchForm({ ...dispatchForm, pickup_state: e.target.value })} required /></div>
                <div className="form-group"><label>Pincode *</label><input value={dispatchForm.pickup_pincode} onChange={e => setDispatchForm({ ...dispatchForm, pickup_pincode: e.target.value })} maxLength={6} required /></div>
              </div>
              <button type="submit" className="btn btn-primary btn-block" disabled={dispatchSaving}>
                <MapPin size={16} style={{ marginRight: 6, verticalAlign: -3 }} />
                {dispatchSaving ? 'Saving...' : dispatchProfile ? 'Update Dispatch Info' : 'Save Dispatch Info'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab 3: AI Seller Agent */}
      {tab === 'ai_agent' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          {/* Chat with Agent */}
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20, display: 'flex', flexDirection: 'column', height: 500 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Bot size={20} color="var(--primary)" /> AI Seller Advisor Chat & Tool Diagnostics
            </h3>
            
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingRight: 8 }}>
              {agentMessages.map((m, idx) => (
                <div key={idx} style={{ alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                  <div style={{
                    padding: '10px 14px', borderRadius: 10, fontSize: '0.88rem', lineHeight: 1.45,
                    background: m.sender === 'user' ? 'var(--primary)' : 'var(--bg-body)',
                    color: m.sender === 'user' ? '#fff' : 'var(--text-primary)',
                    border: m.sender === 'agent' ? '1px solid var(--border-light)' : 'none'
                  }}>
                    {m.sender === 'agent' ? renderFormattedText(m.text) : m.text}
                  </div>

                  {m.tools && m.tools.length > 0 && (
                    <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {m.tools.map((t: any, i: number) => (
                        <div key={i} style={{ fontSize: '0.78rem', background: '#EBF4FF', color: '#0052CC', padding: '4px 8px', borderRadius: 6, border: '1px solid #B3D4FF' }}>
                          🔧 <strong>Tool Executed ({t.tool}):</strong> {t.output}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {agentLoading && <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>🤖 AI Agent running diagnostic tools...</div>}
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <input
                value={agentPrompt}
                onChange={e => setAgentPrompt(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleRunAgent()}
                placeholder="Ask AI agent (e.g. 'Optimize my prices' or 'Check inventory stock')..."
                style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid var(--border-light)', fontSize: '0.88rem' }}
              />
              <button className="btn btn-primary" onClick={() => handleRunAgent()}>
                <Send size={16} />
              </button>
            </div>
          </div>

          {/* Quick AI Diagnostic Tools Sidebar */}
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
            <h4 style={{ fontSize: '0.92rem', fontWeight: 600, marginBottom: 12 }}>Quick AI Diagnostic Tools</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Analyze my buyer reviews and ratings')}>
                📝 Analyze My Reviews
              </button>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Analyze my order engagement and sales performance')}>
                📊 Analyze Engagement & Sales
              </button>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Run price optimization analysis')}>
                🏷️ Run Price Optimizer
              </button>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Check inventory low stock alerts')}>
                ⚠️ Run Stock Alert Check
              </button>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Suggest best homepage ad campaign')}>
                Megaphone Recommend Ad Spot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: AI Reviews & Auto-Reply */}
      {tab === 'reviews' && (
        <div>
          {/* Sentiment Summary Card */}
          {reviewAnalytics && (
            <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20, marginBottom: 16 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12 }}>Customer Review Sentiment Analysis</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 20, alignItems: 'center' }}>
                <div style={{ textAlign: 'center', borderRight: '1px solid var(--border-light)', paddingRight: 20 }}>
                  <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--primary)' }}>{reviewAnalytics.average_rating}</div>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 2, color: '#FFA41C', marginBottom: 4 }}>
                    {[1,2,3,4,5].map(i => <Star key={i} size={16} fill="currentColor" />)}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Based on {reviewAnalytics.total_reviews} verified customer reviews</div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
                    <span>Positive ({reviewAnalytics.sentiment_breakdown.positive_percent}%)</span>
                    <span style={{ color: 'var(--success)', fontWeight: 600 }}>Great</span>
                  </div>
                  <div style={{ width: '100%', height: 8, background: 'var(--bg-body)', borderRadius: 4, overflow: 'hidden', marginBottom: 10 }}>
                    <div style={{ width: `${reviewAnalytics.sentiment_breakdown.positive_percent}%`, height: '100%', background: 'var(--success)' }}></div>
                  </div>

                  <div style={{ fontWeight: 600, fontSize: '0.82rem', marginBottom: 4 }}>AI Product Flaw Reports:</div>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {reviewAnalytics.flaw_reports.map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Reviews List & 1-Click Auto-Reply */}
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 20 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Buyer Reviews & 1-Click AI Auto-Reply</h3>
            
            {reviewsList.length === 0 && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No buyer reviews yet. Reviews appear here once buyers rate a completed order.</p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {reviewsList.map(r => (
                <div key={r.id} style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', padding: 16, background: 'var(--bg-body)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ fontWeight: 600 }}>{r.buyer_name} <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--text-muted)' }}>on {r.product_title}</span></div>
                    <div style={{ display: 'flex', gap: 2, color: '#FFA41C' }}>
                      {[...Array(r.rating)].map((_, i) => <Star key={i} size={14} fill="currentColor" />)}
                    </div>
                  </div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginBottom: 10 }}>"{r.review_text}"</p>

                  {r.reply && editingReplyId !== r.id ? (
                    <div>
                      <div style={{ background: '#E6F4EA', border: '1px solid #CEEAD6', padding: 10, borderRadius: 6, fontSize: '0.82rem', color: '#137333', marginBottom: 8 }}>
                        <strong>AI-posted response (visible to buyers on the product page):</strong> {r.reply}
                      </div>
                      <button className="btn btn-outline btn-sm" onClick={() => setEditingReplyId(r.id)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Sparkles size={14} /> Edit Response
                      </button>
                    </div>
                  ) : (
                    <div>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <button
                          className="btn btn-outline btn-sm"
                          onClick={() => handleAutoReplyReview(r.id, r.buyer_name, r.rating, r.review_text, r.product_title)}
                          disabled={aiDraftingId === r.id}
                          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                        >
                          <Sparkles size={14} /> {aiDraftingId === r.id ? 'Drafting...' : '1-Click AI Auto-Reply'}
                        </button>
                      </div>
                      <textarea
                        value={r.draftReply || ''}
                        onChange={e => handleDraftReplyChange(r.id, e.target.value)}
                        rows={2}
                        placeholder="Generate an AI draft above, or type your own reply..."
                        style={{ width: '100%', marginBottom: 8, fontSize: '0.85rem' }}
                      />
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => handlePostReply(r.id)}
                          disabled={!r.draftReply?.trim() || replyPostingId === r.id}
                        >
                          {replyPostingId === r.id ? 'Posting...' : 'Post Reply'}
                        </button>
                        {editingReplyId === r.id && (
                          <button className="btn btn-outline btn-sm" onClick={() => setEditingReplyId(null)} disabled={replyPostingId === r.id}>
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Sale Events */}
      {tab === 'sales' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Plus size={18} /> Create Sale Event
            </h3>
            {saleSuccess && <div className={`alert ${saleSuccess.startsWith('Error') ? 'alert-error' : 'alert-success'}`}>{saleSuccess}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-group"><label>Sale Title</label><input value={saleTitle} onChange={e => setSaleTitle(e.target.value)} placeholder="e.g. Monsoon Mega Sale" /></div>
              <div className="form-group"><label>Description</label><textarea value={saleDesc} onChange={e => setSaleDesc(e.target.value)} rows={3} placeholder="Describe your sale..." /></div>
              <div className="form-group"><label>Default Discount (%)</label><input type="number" value={saleDiscount} onChange={e => setSaleDiscount(+e.target.value)} min={1} max={90} /></div>

              <div className="form-group">
                <label>Applies To</label>
                <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 400, fontSize: '0.85rem' }}>
                    <input type="radio" checked={saleApplyAll} onChange={() => setSaleApplyAll(true)} /> All my listings
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 400, fontSize: '0.85rem' }}>
                    <input type="radio" checked={!saleApplyAll} onChange={() => setSaleApplyAll(false)} /> Select specific listings
                  </label>
                </div>
                <div style={{ maxHeight: 220, overflowY: 'auto', border: '1px solid var(--border-light)', borderRadius: 6, padding: 8 }}>
                  {activeListings.length === 0 && <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: 0 }}>No active listings.</p>}
                  {activeListings.map((l: any) => (
                    <div key={l.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
                      {!saleApplyAll && (
                        <input type="checkbox" checked={saleSelectedIds.has(l.id)} onChange={() => toggleSaleListing(l.id)} />
                      )}
                      <span style={{ flex: 1, fontSize: '0.82rem', opacity: saleApplyAll || saleSelectedIds.has(l.id) ? 1 : 0.5 }}>{l.title}</span>
                      <input
                        type="number"
                        placeholder={`${saleDiscount}%`}
                        value={saleOverrides[l.id] || ''}
                        onChange={e => setSaleOverrides(prev => ({ ...prev, [l.id]: e.target.value }))}
                        title="Override discount % for this item only"
                        style={{ width: 70, padding: '3px 6px', fontSize: '0.78rem', border: '1px solid var(--border-light)', borderRadius: 4 }}
                      />
                    </div>
                  ))}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Leave the % box blank to use the default discount; set a value to override it for that item only.</span>
              </div>

              <div className="form-group">
                <label>Banner Image</label>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input value={saleBanner} onChange={e => setSaleBanner(e.target.value)} placeholder="https://... (or upload below)" style={{ flex: 1 }} />
                </div>
                <label className="btn btn-outline btn-sm" style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                  <Upload size={14} /> {saleBannerUploading ? 'Uploading...' : 'Upload from device'}
                  <input type="file" accept="image/*" onChange={handleUploadSaleBanner} disabled={saleBannerUploading} style={{ display: 'none' }} />
                </label>
                {saleBanner && (
                  <img src={saleBanner} alt="Banner preview" style={{ display: 'block', marginTop: 10, width: '100%', maxHeight: 120, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-light)' }} />
                )}
              </div>
              <button className="btn btn-primary btn-block" onClick={handleCreateSale} disabled={saleSubmitting || !saleTitle}>
                {saleSubmitting ? 'Creating...' : 'Create Sale Event'}
              </button>
            </div>
          </div>

          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Your Sale Events</h3>
            {mySales.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No sale events yet. Create one to boost your sales!</p>
            ) : (
              mySales.map((s: any) => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{s.title}</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-discount)' }}>{s.discount_percent}% OFF</div>
                  </div>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => handleDeleteSaleEvent(s.id)}
                    disabled={saleDeletingId === s.id}
                    title="Take down this sale event"
                    style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--danger)', borderColor: 'var(--danger)' }}
                  >
                    <Trash2 size={14} /> {saleDeletingId === s.id ? 'Removing...' : 'Take Down'}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 6: Advertise */}
      {tab === 'ads' && (
        <div style={{ maxWidth: 600 }}>
          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Megaphone size={18} /> Purchase Ad Placement
            </h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: '0.9rem' }}>
              Pick which of your listings to advertise, then let AI write the headline and design the banner image for you — or fill it in yourself.
            </p>
            {adSuccess && <div className={`alert ${adSuccess.startsWith('Error') ? 'alert-error' : 'alert-success'}`}>{adSuccess}</div>}
            {aiNoticeAd && <div className="alert alert-success">{aiNoticeAd}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-group">
                <label>Listing to Advertise *</label>
                <select value={adListingId} onChange={e => { setAdListingId(e.target.value); setAiNoticeAd(''); }}>
                  <option value="">Select a listing...</option>
                  {activeListings.map((l: any) => (
                    <option key={l.id} value={l.id}>{l.title}</option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                className="btn btn-primary btn-block"
                onClick={handleGenerateAd}
                disabled={!adListingId || adGenerating}
                style={{ background: 'linear-gradient(135deg, #FF9900 0%, #E67A00 100%)', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
              >
                <Sparkles size={16} /> {adGenerating ? 'AI is designing your ad...' : 'AI Create My Ad'}
              </button>

              <div className="form-group"><label>Ad Title</label><input value={adTitle} onChange={e => setAdTitle(e.target.value)} placeholder="Your ad headline (AI-generated or your own)" /></div>
              <div className="form-group">
                <label>Ad Image</label>
                <input value={adImage} onChange={e => setAdImage(e.target.value)} placeholder="https://... (AI-generated, or upload/paste your own)" />
                <label className="btn btn-outline btn-sm" style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                  <Upload size={14} /> {adImageUploading ? 'Uploading...' : 'Upload from device instead'}
                  <input type="file" accept="image/*" onChange={handleUploadAdImage} disabled={adImageUploading} style={{ display: 'none' }} />
                </label>
                {adImage && (
                  <img src={adImage} alt="Ad preview" style={{ display: 'block', marginTop: 10, width: '100%', maxHeight: 120, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-light)' }} />
                )}
              </div>
              <div className="form-group">
                <label>Placement</label>
                <select value={adPlacement} onChange={e => setAdPlacement(e.target.value)}>
                  <option value="hero_banner">Hero Banner (Homepage Carousel) — ₹{AD_PRICING.hero_banner}</option>
                  <option value="sidebar">Sidebar — ₹{AD_PRICING.sidebar}</option>
                  <option value="category_strip">Category Strip — ₹{AD_PRICING.category_strip}</option>
                </select>
              </div>
              <button className="btn btn-accent btn-block" onClick={handleCreateAd} disabled={adSubmitting || !adTitle}>
                {adSubmitting ? 'Purchasing...' : 'Purchase Ad Placement'}
              </button>
            </div>
          </div>

          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24, marginTop: 16 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Your Advertisements</h3>
            {myAds.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No advertisements purchased yet.</p>
            ) : (
              myAds.map((a: any) => (
                <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', marginBottom: 8 }}>
                  <img src={a.image_url || FALLBACK_IMAGE} alt="" style={{ width: 60, height: 40, objectFit: 'cover', borderRadius: 4 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{a.title}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{a.placement} · {a.impressions} impressions · {a.clicks} clicks</div>
                  </div>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => handleDeleteAd(a.id)}
                    disabled={adDeletingId === a.id}
                    title="Take down this advertisement"
                    style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--danger)', borderColor: 'var(--danger)' }}
                  >
                    <Trash2 size={14} /> {adDeletingId === a.id ? 'Removing...' : 'Take Down'}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Publish Modal */}
      <PublishProductModal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        onSuccess={loadData}
        categories={categories}
      />

      <PublishJobModal
        isOpen={isPublishJobModalOpen}
        onClose={() => setIsPublishJobModalOpen(false)}
        onSuccess={loadData}
        jobsCategoryId={categories.find((c: any) => c.name === 'Jobs')?.id || null}
      />

      <PublishAgriModal
        isOpen={isPublishAgriModalOpen}
        onClose={() => setIsPublishAgriModalOpen(false)}
        onSuccess={loadData}
        agriCategoryId={categories.find((c: any) => c.name === 'Agriculture')?.id || null}
      />

      <JobApplicantsModal
        listingId={applicantsFor?.id || null}
        listingTitle={applicantsFor?.title || ''}
        onClose={() => setApplicantsFor(null)}
      />

      <EditListingModal
        listingId={editingListingId}
        onClose={() => setEditingListingId(null)}
        onSaved={loadData}
      />
    </div>
  );
};
