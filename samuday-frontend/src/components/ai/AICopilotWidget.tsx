import React, { useState } from 'react';
import { aiAPI, cartAPI } from '../../api/client';
import { useCart } from '../../context/CartContext';
import { Bot, X, Send, Mic, Sparkles, ShoppingBag } from 'lucide-react';

const renderFormattedText = (text: string) => {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    let isBullet = false;
    let cleanLine = line;
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      isBullet = true;
      cleanLine = line.trim().replace(/^[-*]\s+/, '');
    }

    const parts: React.ReactNode[] = [];
    const boldRegex = /\*\*(.*?)\*\*/g;
    let match;
    let lastIndex = 0;

    while ((match = boldRegex.exec(cleanLine)) !== null) {
      const matchIndex = match.index;
      if (matchIndex > lastIndex) {
        parts.push(cleanLine.substring(lastIndex, matchIndex));
      }
      parts.push(<strong key={matchIndex}>{match[1]}</strong>);
      lastIndex = boldRegex.lastIndex;
    }

    if (lastIndex < cleanLine.length) {
      parts.push(cleanLine.substring(lastIndex));
    }

    const content = parts.length > 0 ? parts : cleanLine;

    if (isBullet) {
      return (
        <div key={idx} style={{ display: 'flex', gap: 6, margin: '4px 0 4px 8px', fontSize: '0.84rem', lineHeight: 1.45 }}>
          <span>•</span>
          <span>{content}</span>
        </div>
      );
    }

    return (
      <p key={idx} style={{ margin: '4px 0', fontSize: '0.86rem', lineHeight: 1.45 }}>
        {content}
      </p>
    );
  });
};

export const AICopilotWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState<'en' | 'hi' | 'gu'>('en');
  const [isRecording, setIsRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'ai'; text: string; products?: any[] }>>([
    {
      sender: 'ai',
      text: 'Namaste! 🙏 I am your Samuday AI Shopping Copilot. Ask me anything in English, Hindi (हिंदी), or Gujarati (ગુજરાતી)!',
      products: []
    }
  ]);

  const { refreshCart } = useCart();

  const handleVoiceInput = async () => {
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

        setLoading(true);
        try {
          const res = await aiAPI.transcribeAudio(audioBlob);
          if (res.text) {
            setQuery(res.text);
          }
        } catch {
          alert('Voice transcription failed via Groq.');
        } finally {
          setLoading(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err: any) {
      alert('Microphone access denied: ' + err.message);
    }
  };

  const handleSend = async (customQuery?: string) => {
    const textToSend = customQuery || query;
    if (!textToSend.trim()) return;

    const newMsgs = [...messages, { sender: 'user' as const, text: textToSend }];
    setMessages(newMsgs);
    setQuery('');
    setLoading(true);

    try {
      const res = await aiAPI.copilotChat(textToSend, language);
      setMessages([...newMsgs, { sender: 'ai', text: res.reply, products: res.recommended_products || [] }]);
    } catch {
      setMessages([...newMsgs, { sender: 'ai', text: 'Sorry, I could not process that request right now. Try browsing our categories!' }]);
    }
    setLoading(false);
  };

  const handleAddToCart = async (listingId: string) => {
    try {
      await cartAPI.addToCart(listingId, 1);
      await refreshCart();
      alert('Item added to cart!');
    } catch {
      alert('Please login to add items to cart.');
    }
  };

  return (
    <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1200 }}>
      {/* Floating Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            width: 56, height: 56, borderRadius: '50%',
            background: 'linear-gradient(135deg, #FF9900 0%, #E67A00 100%)',
            color: '#fff', border: 'none', cursor: 'pointer',
            boxShadow: '0 8px 24px rgba(255, 153, 0, 0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'transform 0.2s ease-in-out'
          }}
          className="hover:scale-105"
          title="Open AI Shopping Copilot"
        >
          <Bot size={28} />
        </button>
      )}

      {/* Chat Drawer Window */}
      {isOpen && (
        <div style={{
          width: 380, maxHeight: 580, background: 'var(--bg-white)',
          borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-card)',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.15)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            background: 'linear-gradient(135deg, #131921 0%, #232F3E 100%)',
            color: '#fff', padding: '14px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Sparkles size={18} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>AI Shopping Copilot</div>
                <div style={{ display: 'flex', gap: 4, marginTop: 2 }}>
                  {(['en', 'hi', 'gu'] as const).map(l => (
                    <button
                      key={l}
                      onClick={() => setLanguage(l)}
                      style={{
                        background: language === l ? '#febd69' : 'transparent',
                        color: language === l ? '#131921' : '#fff',
                        border: 'none', borderRadius: 4, padding: '1px 5px', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer'
                      }}
                    >
                      {l === 'en' ? 'EN' : l === 'hi' ? 'हिंदी' : 'ગુજરાતી'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>
              <X size={20} />
            </button>
          </div>

          {/* Messages Container */}
          <div style={{ flex: 1, padding: 14, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 420 }}>
            {messages.map((m, idx) => (
              <div key={idx} style={{ alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%' }}>
                <div style={{
                  padding: '10px 14px', borderRadius: 12, fontSize: '0.86rem', lineHeight: 1.45,
                  background: m.sender === 'user' ? 'var(--primary)' : 'var(--bg-body)',
                  color: m.sender === 'user' ? '#fff' : 'var(--text-primary)',
                  border: m.sender === 'ai' ? '1px solid var(--border-light)' : 'none'
                }}>
                  {renderFormattedText(m.text)}
                </div>

                {/* Recommended Products Carousel Cards */}
                {m.products && m.products.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                    {m.products.map((p: any) => (
                      <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 8, background: '#fff', borderRadius: 8, border: '1px solid var(--border-light)' }}>
                        <img src={p.image} alt="" style={{ width: 44, height: 44, objectFit: 'cover', borderRadius: 6 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.title}</div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--primary)', fontWeight: 700 }}>₹{(p.price / 100).toLocaleString('en-IN')}</div>
                        </div>
                        <button
                          onClick={() => handleAddToCart(p.id)}
                          style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: '6px 10px', borderRadius: 6, fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          <ShoppingBag size={12} /> Add
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div style={{ alignSelf: 'flex-start', background: 'var(--bg-body)', padding: '8px 14px', borderRadius: 12, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                🤖 Copilot thinking...
              </div>
            )}
          </div>

          {/* Quick Suggestions Chips */}
          <div style={{ padding: '4px 12px', display: 'flex', gap: 6, overflowX: 'auto', background: 'var(--bg-body)', borderTop: '1px solid var(--border-light)' }}>
            <button onClick={() => handleSend('Best smartphones under 20,000')} style={{ padding: '3px 8px', borderRadius: 12, border: '1px solid var(--border-card)', background: '#fff', fontSize: '0.72rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              📱 Mobiles under 20k
            </button>
            <button onClick={() => handleSend('Organic wheat from MP farm')} style={{ padding: '3px 8px', borderRadius: 12, border: '1px solid var(--border-card)', background: '#fff', fontSize: '0.72rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              🌾 Organic Wheat
            </button>
            <button onClick={() => handleSend('Monsoon fashion deals')} style={{ padding: '3px 8px', borderRadius: 12, border: '1px solid var(--border-card)', background: '#fff', fontSize: '0.72rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              👗 Fashion Deals
            </button>
          </div>

          {/* Input Footer */}
          <div style={{ padding: 10, background: '#fff', borderTop: '1px solid var(--border-light)', display: 'flex', gap: 6, alignItems: 'center' }}>
            <button
              onClick={handleVoiceInput}
              style={{ background: isRecording ? 'var(--danger)' : 'var(--bg-body)', border: 'none', width: 36, height: 36, borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              title="Voice Input (EN/HI/GU)"
            >
              <Mic size={16} color={isRecording ? '#fff' : 'var(--text-primary)'} />
            </button>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Ask AI Copilot..."
              style={{ flex: 1, padding: '8px 12px', borderRadius: 20, border: '1px solid var(--border-light)', fontSize: '0.85rem' }}
            />
            <button
              onClick={() => handleSend()}
              style={{ background: 'var(--primary)', color: '#fff', border: 'none', width: 36, height: 36, borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
