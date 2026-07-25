import React, { useState } from 'react';
import { marketAPI, aiAPI } from '../../api/client';
import { Sparkles, Mic, Image as ImageIcon, CheckCircle, AlertCircle, X, Wand2, Package, Plus, Trash2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  categories: any[];
}

export const PublishProductModal: React.FC<Props> = ({ isOpen, onClose, onSuccess, categories }) => {
  const [shortSummary, setShortSummary] = useState('');
  const [language, setLanguage] = useState<'en' | 'hi' | 'gu'>('en');
  const [isRecording, setIsRecording] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);

  // Form states
  const [title, setTitle] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [priceInr, setPriceInr] = useState('');
  const [quantity, setQuantity] = useState('100');
  const [description, setDescription] = useState('');
  const [primaryImage, setPrimaryImage] = useState('');
  const [imageVariants, setImageVariants] = useState<string[]>([]);
  const [imageGenerating, setImageGenerating] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [weightGrams, setWeightGrams] = useState('500');
  const [offers, setOffers] = useState<string[]>([]);
  const [newOffer, setNewOffer] = useState('');
  const [returnPolicy, setReturnPolicy] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [aiNotice, setAiNotice] = useState('');

  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  if (!isOpen) return null;

  // Handle Voice Dictation using MediaRecorder & Groq Whisper API
  const handleVoiceRecord = async () => {
    if (isRecording) {
      if (mediaRecorder) {
        mediaRecorder.stop();
        setIsRecording(false);
      }
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        if (audioBlob.size < 100) return;

        setAiGenerating(true);
        setError('');
        try {
          const res = await aiAPI.transcribeAudio(audioBlob);
          if (res.text) {
            setShortSummary(prev => prev ? `${prev} ${res.text}` : res.text);
            setAiNotice('🎙️ Audio transcribed successfully via Groq Whisper!');
          }
        } catch (err: any) {
          setError(err.message || 'Groq voice transcription failed.');
        } finally {
          setAiGenerating(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err: any) {
      alert('Microphone access denied: ' + err.message);
    }
  };

  // Handle Manual Image Upload
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingImage(true);
    setError('');
    setAiNotice('');
    try {
      const res = await marketAPI.uploadImage(file);
      if (res.url) {
        setPrimaryImage(res.url);
        setAiNotice('📤 Image uploaded successfully to local storage/Supabase!');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload image.');
    } finally {
      setUploadingImage(false);
    }
  };

  // AI 1-Click Full Listing Generation
  const handleAiGenerateListing = async () => {
    if (!shortSummary.trim()) {
      setError('Please type or speak a short summary of your product first.');
      return;
    }

    setAiGenerating(true);
    setError('');
    setAiNotice('');

    try {
      const result = await aiAPI.generateListing(shortSummary, undefined, language);
      
      // Set title (truncated to fit backend validation)
      const aiTitle = (result.title || '').trim().slice(0, 140);
      setTitle(aiTitle || shortSummary.slice(0, 100));
      
      // Set description
      setDescription(result.description || '');
      
      // Set price (convert paise to INR, ensure valid number)
      if (result.price_paise && result.price_paise > 0) {
        setPriceInr((result.price_paise / 100).toString());
      } else {
        setPriceInr('1499');
      }
      
      // Auto match category ID (case-insensitive, supports partial matching)
      const aiCategory = (result.category || '').toLowerCase().trim();
      const matchedCat = categories.find(c => {
        const catName = c.name.toLowerCase().trim();
        return catName === aiCategory || 
               catName.includes(aiCategory) || 
               aiCategory.includes(catName);
      });
      if (matchedCat) {
        setCategoryId(matchedCat.id);
      } else if (categories.length > 0) {
        setCategoryId(categories[0].id);
      }

      if (result.weight_grams && result.weight_grams > 0) {
        setWeightGrams(result.weight_grams.toString());
      }

      setAiNotice('✨ AI generated full SEO title, category, price, shipping weight & deep description!');
    } catch (e: any) {
      setError(e.message || 'AI generation failed');
    }
    setAiGenerating(false);
  };

  // AI Multi-Image Generation from single image
  const handleAiGenerateImages = async () => {
    if (!primaryImage) {
      setError('Please upload a primary image first.');
      return;
    }

    setImageGenerating(true);
    setError('');
    try {
      const res = await aiAPI.generateImages(primaryImage, title || 'Product', 'general');
      setImageVariants(res.generated_variants || []);
      setAiNotice('📸 AI generated 2 high-quality variant showcase photos!');
    } catch (e: any) {
      setError(e.message || 'Image generation failed');
    }
    setImageGenerating(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !priceInr || !categoryId) {
      setError('Please fill in required fields (Title, Price, Category)');
      return;
    }

    const priceValue = Math.round(parseFloat(priceInr) * 100);
    if (isNaN(priceValue) || priceValue <= 0) {
      setError('Please enter a valid price');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const mediaUrls: string[] = [];
      if (primaryImage) {
        mediaUrls.push(primaryImage);
      }
      imageVariants.forEach((v) => {
        if (v) mediaUrls.push(v);
      });

      await marketAPI.createListing({
        pillar: 'marketplace',
        title: title.slice(0, 150),
        description: (description || shortSummary || 'Quality product listed on Samuday marketplace.').slice(0, 10000),
        price: priceValue,
        category_id: categoryId || null,
        listing_type: 'sale',
        quantity: parseInt(quantity) || 50,
        unit: 'piece',
        media_urls: mediaUrls,
        weight_grams: parseInt(weightGrams) || 500,
        available_offers: offers,
        return_policy: returnPolicy || undefined,
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to publish product';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    setSubmitting(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '90vh', overflowY: 'auto', padding: 24 }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={22} color="var(--primary)" /> Publish Product with AI Magic
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}><AlertCircle size={16} /> {error}</div>}
        {aiNotice && <div className="alert alert-success" style={{ marginBottom: 16 }}><CheckCircle size={16} /> {aiNotice}</div>}

        {/* Section 1: Multilingual Voice / Text Summary AI Generator */}
        <div style={{ background: 'var(--bg-body)', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label style={{ fontWeight: 600, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Mic size={16} color="var(--primary)" /> Speak or Type Short Summary (EN / हिंदी / ગુજરાતી)
            </label>
            <div style={{ display: 'flex', gap: 6 }}>
              {(['en', 'hi', 'gu'] as const).map(l => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLanguage(l)}
                  style={{
                    padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-light)',
                    background: language === l ? 'var(--primary)' : 'var(--bg-white)',
                    color: language === l ? '#fff' : 'var(--text-primary)',
                    fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer'
                  }}
                >
                  {l === 'en' ? 'EN' : l === 'hi' ? 'हिंदी' : 'ગુજરાતી'}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <textarea
              value={shortSummary}
              onChange={e => setShortSummary(e.target.value)}
              rows={2}
              placeholder="e.g., Organic Sharbati wheat 50kg bag fresh from MP farm direct delivery"
              style={{ flex: 1, padding: 10, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', fontSize: '0.88rem' }}
            />
            <button
              type="button"
              onClick={handleVoiceRecord}
              className={`btn ${isRecording ? 'btn-danger' : 'btn-outline'}`}
              title="Click to speak your product summary"
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 16px' }}
            >
              <Mic size={18} className={isRecording ? 'animate-pulse' : ''} />
              <span style={{ fontSize: '0.7rem', marginTop: 2 }}>{isRecording ? 'Listening...' : 'Speak'}</span>
            </button>
          </div>

          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={handleAiGenerateListing}
            disabled={aiGenerating || !shortSummary.trim()}
            style={{ background: 'linear-gradient(135deg, #FF9900 0%, #E67A00 100%)', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
          >
            <Wand2 size={18} /> {aiGenerating ? 'AI Magic in progress...' : 'AI Auto-Fill SEO Listing & Pricing'}
          </button>
        </div>

        {/* Form Fields */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Product Title *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g., Organic Sharbati Wheat - 50kg Bag" required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Category *</label>
              <select value={categoryId} onChange={e => setCategoryId(e.target.value)} required>
                <option value="">Select category</option>
                {categories.map((c: any) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Price (₹) *</label>
              <input type="number" value={priceInr} onChange={e => setPriceInr(e.target.value)} placeholder="1499" required min="1" />
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Stock Quantity</label>
              <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} min="1" />
            </div>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Package size={14} /> Shipping Weight (grams, per unit)
            </label>
            <input type="number" value={weightGrams} onChange={e => setWeightGrams(e.target.value)} min="10" placeholder="500" />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Used to calculate courier delivery charges. AI Auto-Fill estimates this for you.</span>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Detailed Description & Features</label>
            <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
              <button type="button" className="btn btn-outline btn-sm" onClick={() => setDescription(prev => (prev ? prev + '\n' : '') + '### Heading\n')}>Heading</button>
              <button type="button" className="btn btn-outline btn-sm" onClick={() => setDescription(prev => prev + '**bold text**')}>Bold</button>
              <button type="button" className="btn btn-outline btn-sm" onClick={() => setDescription(prev => (prev ? prev + '\n' : '') + '- ')}>Bullet</button>
            </div>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={4} placeholder="Full product details... supports ### headings, **bold**, and - bullets" />
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Available Offers</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 8 }}>
              {offers.map((o, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg-body)', padding: '6px 10px', borderRadius: 6 }}>
                  <span style={{ flex: 1, fontSize: '0.85rem' }}>{o}</span>
                  <button type="button" onClick={() => setOffers(prev => prev.filter((_, idx) => idx !== i))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                value={newOffer}
                onChange={e => setNewOffer(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (newOffer.trim()) { setOffers(prev => [...prev, newOffer.trim()]); setNewOffer(''); } } }}
                placeholder="e.g. Bank Offer: 10% off on SBI Credit Cards"
                style={{ flex: 1 }}
              />
              <button type="button" className="btn btn-outline btn-sm" onClick={() => { if (newOffer.trim()) { setOffers(prev => [...prev, newOffer.trim()]); setNewOffer(''); } }} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Plus size={14} /> Add
              </button>
            </div>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Return Policy</label>
            <textarea value={returnPolicy} onChange={e => setReturnPolicy(e.target.value)} rows={2} placeholder="e.g. 7-day easy returns if item is unused and in original packaging." />
          </div>

          {/* Section 2: Manual Upload + AI Multi-Image Generator */}
          <div style={{ background: 'var(--bg-body)', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
            <label style={{ fontWeight: 600, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <ImageIcon size={16} color="var(--primary)" /> Product Primary Image (Manual Upload)
            </label>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                disabled={uploadingImage}
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn btn-accent"
                onClick={handleAiGenerateImages}
                disabled={imageGenerating || !primaryImage || uploadingImage}
                style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Sparkles size={16} /> {imageGenerating ? 'Generating...' : 'AI Generate 3 Variant Photos'}
              </button>
            </div>

            {/* Gallery Preview */}
            <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingTop: 4 }}>
              {primaryImage && (
                <div style={{ position: 'relative' }}>
                  <img src={primaryImage} alt="Primary" style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 6, border: '2px solid var(--primary)' }} />
                  <span style={{ position: 'absolute', bottom: 4, left: 4, background: 'var(--primary)', color: '#fff', fontSize: '0.65rem', padding: '1px 4px', borderRadius: 3 }}>Main</span>
                </div>
              )}
              {imageVariants.map((url, i) => (
                <div key={i} style={{ position: 'relative' }}>
                  <img src={url} alt={`AI Variant ${i+1}`} style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border-card)' }} />
                  <span style={{ position: 'absolute', bottom: 4, left: 4, background: 'var(--accent)', color: '#fff', fontSize: '0.65rem', padding: '1px 4px', borderRadius: 3 }}>AI #{i+1}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Publishing...' : 'Publish Product Listing'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
