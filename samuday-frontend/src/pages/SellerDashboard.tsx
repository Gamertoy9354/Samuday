import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { authAPI, promoAPI, marketAPI, aiAPI } from '../api/client';
import { PublishProductModal } from '../components/seller/PublishProductModal';
import {
  Package, Megaphone, TrendingUp, Plus, LayoutDashboard, Sparkles,
  Bot, Star, Send, BellRing, CheckCircle2, AlertTriangle, Info
} from 'lucide-react';

export const SellerDashboard: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [tab, setTab] = useState<'overview' | 'listings' | 'ai_agent' | 'reviews' | 'sales' | 'ads'>('overview');
  const [listings, setListings] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [mySales, setMySales] = useState<any[]>([]);
  const [becomingASeller, setBecomingASeller] = useState(false);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);

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
  const [reviewsList, setReviewsList] = useState<any[]>([
    { id: 1, buyer_name: 'Rahul Sharma', rating: 5, review_text: 'Super fast delivery and fresh organic wheat. Packaging was top notch!', product_title: 'Organic Sharbati Wheat - 50kg', date: 'Yesterday', reply: null },
    { id: 2, buyer_name: 'Priya Patel', rating: 4, review_text: 'Good phone, battery backup is 2 days. Camera quality is clear.', product_title: 'Samsung Galaxy S24 Ultra', date: '3 days ago', reply: null },
    { id: 3, buyer_name: 'Amit Kumar', rating: 3, review_text: 'Product quality is okay, but delivery took 4 days.', product_title: 'JBL Charge 5 Bluetooth Speaker', date: '5 days ago', reply: null }
  ]);

  // Forms
  const [saleTitle, setSaleTitle] = useState('');
  const [saleDesc, setSaleDesc] = useState('');
  const [saleDiscount, setSaleDiscount] = useState(20);
  const [saleBanner, setSaleBanner] = useState('');
  const [saleSubmitting, setSaleSubmitting] = useState(false);
  const [saleSuccess, setSaleSuccess] = useState('');

  const [adTitle, setAdTitle] = useState('');
  const [adImage, setAdImage] = useState('');
  const [adPlacement, setAdPlacement] = useState('hero_banner');
  const [adSubmitting, setAdSubmitting] = useState(false);
  const [adSuccess, setAdSuccess] = useState('');

  const loadData = async () => {
    if (user?.is_seller) {
      marketAPI.getCategories().then(setCategories).catch(() => {});
      marketAPI.getListings().then(all => {
        setListings(all.filter((l: any) => l.seller_id === user.id));
      }).catch(() => {});
      promoAPI.getSaleEvents().then(setMySales).catch(() => setMySales([]));
      aiAPI.getSellerInsights().then(setAiInsights).catch(() => {});
      aiAPI.getReviewAnalytics().then(setReviewAnalytics).catch(() => {});
    }
  };

  useEffect(() => {
    loadData();
  }, [user]);

  const handleBecomeSeller = async () => {
    setBecomingASeller(true);
    try {
      await authAPI.updateProfile({ is_seller: true });
      await refreshUser();
    } catch { /* ignore */ }
    setBecomingASeller(false);
  };

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

  const handleAutoReplyReview = async (reviewId: number, buyerName: string, rating: number, text: string, title: string) => {
    try {
      const res = await aiAPI.autoReplyReview(buyerName, rating, text, title);
      setReviewsList(prev => prev.map(r => r.id === reviewId ? { ...r, reply: res.ai_reply } : r));
    } catch {
      alert('Failed to generate AI auto-reply');
    }
  };

  const handleCreateSale = async () => {
    setSaleSubmitting(true);
    setSaleSuccess('');
    try {
      const now = new Date();
      await promoAPI.createSaleEvent({
        title: saleTitle,
        description: saleDesc,
        banner_image_url: saleBanner || 'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&h=400&fit=crop',
        discount_percent: saleDiscount,
        start_date: now.toISOString(),
        end_date: new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        listing_ids: [],
      });
      setSaleSuccess('Sale event created! It will appear on the homepage.');
      setSaleTitle(''); setSaleDesc('');
    } catch (e: any) {
      setSaleSuccess('Error: ' + (e.message || 'Failed'));
    }
    setSaleSubmitting(false);
  };

  const handleCreateAd = async () => {
    setAdSubmitting(true);
    setAdSuccess('');
    try {
      const now = new Date();
      await promoAPI.createAd({
        title: adTitle,
        image_url: adImage || 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&h=400&fit=crop',
        placement: adPlacement,
        start_date: now.toISOString(),
        end_date: new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000).toISOString(),
      });
      setAdSuccess('Ad placement purchased! Your ad is live.');
      setAdTitle(''); setAdImage('');
    } catch (e: any) {
      setAdSuccess('Error: ' + (e.message || 'Failed'));
    }
    setAdSubmitting(false);
  };

  if (!user) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div className="empty-state"><h3>Please login to access the seller dashboard</h3></div>
      </div>
    );
  }

  if (!user.is_seller) {
    return (
      <div className="page-content" style={{ paddingTop: 32 }}>
        <div style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center', background: 'var(--bg-white)', padding: 40, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <LayoutDashboard size={48} color="var(--primary)" style={{ marginBottom: 16 }} />
          <h2 style={{ marginBottom: 8, fontSize: '1.3rem' }}>Become a Seller</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 24, fontSize: '0.92rem' }}>
            Start selling on Samuday Marketplace. Publish listings with AI image generation, automated voice listing generator, and AI diagnostic agent!
          </p>
          <button className="btn btn-primary btn-lg" onClick={handleBecomeSeller} disabled={becomingASeller}>
            {becomingASeller ? 'Setting up...' : 'Start Selling'}
          </button>
        </div>
      </div>
    );
  }

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
          <span style={{ fontSize: '0.75rem', background: '#FFE099', color: '#663C00', padding: '2px 8px', borderRadius: 10, fontWeight: 600 }}>Health: {aiInsights.summary.health_score}%</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="dashboard-tabs">
        <button className={`dashboard-tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          <LayoutDashboard size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Overview
        </button>
        <button className={`dashboard-tab ${tab === 'listings' ? 'active' : ''}`} onClick={() => setTab('listings')}>
          <Package size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> My Listings ({listings.length})
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
              <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--primary)' }}>{listings.length}</div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Your Active Product Listings</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setIsPublishModalOpen(true)}>
              + Add Product
            </button>
          </div>

          {listings.length === 0 ? (
            <div className="empty-state">
              <h3>No listings yet</h3>
              <p>Click "Publish Product with AI Magic" to create your first listing using voice dictation or single photo!</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {listings.map((l: any) => (
                <div key={l.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                  <img src={l.media?.[0]?.media_url || 'https://via.placeholder.com/60'} alt="" style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 'var(--radius-sm)' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{l.title}</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      &#8377;{(l.price / 100).toLocaleString('en-IN')} · Stock: {l.quantity || 100} units · <span style={{ color: 'var(--success)' }}>Active</span>
                    </div>
                  </div>
                  <span style={{ fontSize: '0.75rem', background: '#E6F4EA', color: '#137333', padding: '4px 8px', borderRadius: 4, fontWeight: 600 }}>
                    ✨ AI SEO Optimized
                  </span>
                </div>
              ))}
            </div>
          )}
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
                    {m.text}
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
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Run price optimization analysis')}>
                🏷️ Run Price Optimizer
              </button>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Check inventory low stock alerts')}>
                ⚠️ Run Stock Alert Check
              </button>
              <button className="btn btn-outline btn-block" onClick={() => handleRunAgent('Enhance search keywords for listings')}>
                🔍 Run SEO Keyword Tool
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

                  {r.reply ? (
                    <div style={{ background: '#E6F4EA', border: '1px solid #CEEAD6', padding: 10, borderRadius: 6, fontSize: '0.82rem', color: '#137333' }}>
                      <strong>🤖 AI Response Posted:</strong> {r.reply}
                    </div>
                  ) : (
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => handleAutoReplyReview(r.id, r.buyer_name, r.rating, r.review_text, r.product_title)}
                      style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                      <Sparkles size={14} /> 1-Click AI Auto-Reply
                    </button>
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
              <div className="form-group"><label>Discount (%)</label><input type="number" value={saleDiscount} onChange={e => setSaleDiscount(+e.target.value)} min={1} max={90} /></div>
              <div className="form-group"><label>Banner Image URL (optional)</label><input value={saleBanner} onChange={e => setSaleBanner(e.target.value)} placeholder="https://..." /></div>
              <button className="btn btn-primary btn-block" onClick={handleCreateSale} disabled={saleSubmitting || !saleTitle}>
                {saleSubmitting ? 'Creating...' : 'Create Sale Event'}
              </button>
            </div>
          </div>

          <div style={{ background: 'var(--bg-white)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', padding: 24 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Active Sales</h3>
            {mySales.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No sale events yet. Create one to boost your sales!</p>
            ) : (
              mySales.map((s: any) => (
                <div key={s.id} style={{ padding: 12, border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', marginBottom: 8 }}>
                  <div style={{ fontWeight: 600 }}>{s.title}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-discount)' }}>{s.discount_percent}% OFF</div>
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
              Advertise your products on the homepage carousel or sidebar. Choose a placement and your ad goes live immediately!
            </p>
            {adSuccess && <div className={`alert ${adSuccess.startsWith('Error') ? 'alert-error' : 'alert-success'}`}>{adSuccess}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-group"><label>Ad Title</label><input value={adTitle} onChange={e => setAdTitle(e.target.value)} placeholder="Your ad headline" /></div>
              <div className="form-group"><label>Ad Image URL</label><input value={adImage} onChange={e => setAdImage(e.target.value)} placeholder="https://..." /></div>
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
        </div>
      )}

      {/* Publish Modal */}
      <PublishProductModal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        onSuccess={loadData}
        categories={categories}
      />
    </div>
  );
};
