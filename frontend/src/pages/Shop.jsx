import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const Shop = () => {
  const [ebayCards, setEbayCards] = useState([]);
  const [marketplaceListings, setMarketplaceListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => { fetchAll(); }, [page, category]);

  const fetchAll = async (searchTerm = '') => {
    setLoading(true);
    try {
      const [ebayResp, mpResp] = await Promise.all([
        axios.get(`${API_BASE}/api/shop/ebay`, { params: { page, limit: 25, search: searchTerm || undefined } }),
        axios.get(`${API_BASE}/api/marketplace/listings`, { params: { limit: 50, category: category || undefined } }),
      ]);
      setEbayCards(ebayResp.data.cards || []);
      setMarketplaceListings(mpResp.data.listings || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSearch = (e) => { e.preventDefault(); setPage(1); fetchAll(search); };

  const allCards = [
    ...marketplaceListings.map(l => ({ ...l, source: 'ragnarok', price: l.price_cents / 100 })),
    ...ebayCards.map(c => ({ ...c, source: 'ebay' })),
  ];

  const purchased = new URLSearchParams(window.location.search).get('purchased');

  return (
    <div className="min-h-screen bg-surface">
      <nav className="border-b border-surface-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="Ragnarok Gaming" className="w-10 h-10 object-contain" />
            <span className="text-base font-display font-semibold text-frost-light tracking-wide uppercase">
              Ragnarok <span className="text-ember">Gamez</span>
            </span>
          </a>
          <div className="flex items-center gap-4">
            <a href="/shop" className="text-sm text-ember font-medium">Shop</a>
            <a href="/sell" className="text-sm text-frost-dim hover:text-frost-light transition-colors">Sell</a>
            <a href="/market" className="text-sm text-frost-dim hover:text-frost-light transition-colors">Sign In</a>
          </div>
        </div>
      </nav>

      {/* Success Banner */}
      {purchased && (
        <div className="bg-gain/20 border-b border-gain/30 py-3 text-center">
          <span className="text-sm text-gain font-medium">🎉 Purchase complete! The seller will ship your card soon.</span>
        </div>
      )}

      {/* Hero */}
      <div className="border-b border-surface-border bg-gradient-to-b from-surface-card to-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <h1 className="text-4xl sm:text-5xl font-display font-bold text-frost-light tracking-wide">
            The Shop That <span className="text-ember">Roks</span>
          </h1>
          <p className="text-frost-dim mt-3 text-sm max-w-lg">
            Cards and collectibles from verified sellers. Buy direct — fast shipping, no auction fees.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <form onSubmit={handleSearch} className="flex-1 min-w-[200px] max-w-md relative">
              <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search cards..." className="w-full px-4 py-2.5 rounded-lg text-sm bg-surface border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40 pr-20" />
              <button type="submit" className="absolute right-1.5 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-md text-xs font-medium bg-ember/90 hover:bg-ember text-white">Search</button>
            </form>
            <select value={category} onChange={e => { setCategory(e.target.value); setPage(1); }} className="px-3 py-2.5 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              <option value="">All Categories</option>
              <option>Baseball</option><option>Football</option><option>Basketball</option><option>Pokémon</option><option>Hockey</option><option>Soccer</option><option>Other</option>
            </select>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <span className="text-xs text-frost-dim">{allCards.length} items</span>
        </div>

        {loading ? (
          <div className="text-center py-16 text-frost-dim text-sm">Loading...</div>
        ) : allCards.length === 0 ? (
          <div className="text-center py-16"><p className="text-frost-dim text-sm">Nothing here yet.</p></div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {allCards.map((card, i) => <ShopCard key={`${card.source}-${card.id}-${i}`} card={card} />)}
          </div>
        )}
      </div>
    </div>
  );
};

const ShopCard = ({ card }) => {
  const [buying, setBuying] = useState(false);

  const handleBuy = async (e) => {
    e.preventDefault();
    if (card.source !== 'ragnarok') {
      window.open(card.ebay_url, '_blank');
      return;
    }
    setBuying(true);
    try {
      const resp = await axios.post(`${import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com')}/api/marketplace/checkout`, {
        listing_id: card.id,
        buyer_id: 1, // TODO: get from auth
      });
      window.location.href = resp.data.checkout_url;
    } catch (err) {
      alert(err.response?.data?.detail || 'Checkout error');
      setBuying(false);
    }
  };

  const price = card.price || 0;
  const imageUrl = card.source === 'ragnarok' ? card.image_urls?.[0] : card.image_url;

  return (
    <div className="card-surface overflow-hidden hover:border-ember/30 transition-all group">
      <div className="aspect-[2.5/3.5] bg-surface-raised relative overflow-hidden">
        {imageUrl ? (
          <img src={imageUrl} alt={card.title} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" onError={e => { e.target.style.display = 'none'; }} />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">No Image</div>
        )}
        {price > 0 && (
          <div className="absolute bottom-2 right-2 bg-surface-base/90 backdrop-blur-sm rounded-md px-2.5 py-1">
            <span className="text-sm font-mono font-bold text-gain">${price.toFixed(2)}</span>
          </div>
        )}
        {card.source === 'ragnarok' && (
          <div className="absolute top-2 left-2 bg-ember/90 rounded-md px-2 py-0.5">
            <span className="text-[10px] font-bold text-white">BUY DIRECT</span>
          </div>
        )}
      </div>
      <div className="p-2.5">
        <div className="text-xs font-medium text-frost-light line-clamp-2 leading-relaxed">{card.title}</div>
        <div className="mt-2 flex items-center justify-between">
          {card.source === 'ragnarok' ? (
            <button onClick={handleBuy} disabled={buying} className="text-[10px] bg-ember/90 hover:bg-ember text-white px-3 py-1 rounded-full font-medium disabled:opacity-50">
              {buying ? '...' : 'Buy Now'}
            </button>
          ) : (
            <a href={card.ebay_url} target="_blank" rel="noopener noreferrer" className="text-[10px] bg-ember/10 text-ember px-2 py-0.5 rounded-full">
              eBay
            </a>
          )}
          {card.shipping_cents > 0 && (
            <span className="text-[10px] text-frost-dim">+${(card.shipping_cents / 100).toFixed(2)} ship</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default Shop;
