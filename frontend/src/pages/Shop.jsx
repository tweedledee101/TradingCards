import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const Shop = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchCards();
  }, [page]);

  const fetchCards = async (searchTerm = '') => {
    setLoading(true);
    try {
      const params = { page, limit: 50 };
      if (searchTerm) params.search = searchTerm;
      const resp = await axios.get(`${API_BASE}/api/shop/ebay`, { params });
      setCards(resp.data.cards || []);
      setTotal(resp.data.total || 0);
    } catch (err) {
      console.error('Shop fetch error:', err);
      setCards([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchCards(search);
  };

  return (
    <div className="min-h-screen bg-surface">
      {/* Public nav */}
      <nav className="border-b border-surface-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="Ragnarok Gaming" className="w-10 h-10 object-contain" />
            <span className="text-base font-display font-semibold text-frost-light tracking-wide uppercase">
              Ragnarok <span className="text-ember">Gaming</span>
            </span>
          </a>
          <div className="flex items-center gap-4">
            <a href="/shop" className="text-sm text-ember font-medium">Shop</a>
            <a href="/market" className="text-sm text-frost-dim hover:text-frost-light transition-colors">Sign In</a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div className="border-b border-surface-border bg-gradient-to-b from-surface-card to-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
          <h1 className="text-4xl sm:text-5xl font-display font-bold text-frost-light tracking-wide">
            The Shop That <span className="text-ember">Roks</span>
          </h1>
          <p className="text-frost-dim mt-3 text-sm sm:text-base max-w-lg">
            Cards, collectibles, and more. Every purchase ships fast and is backed by eBay buyer protection.
          </p>

          {/* Search */}
          <form onSubmit={handleSearch} className="mt-6 max-w-md">
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search the shop..."
                className="w-full px-4 py-2.5 rounded-lg text-sm bg-surface border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40 pr-20"
              />
              <button
                type="submit"
                className="absolute right-1.5 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-md text-xs font-medium bg-ember/90 hover:bg-ember text-white transition-colors"
              >
                Search
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* Results info */}
        <div className="flex items-center justify-between mb-6">
          <span className="text-xs text-frost-dim">
            {total} item{total !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Card Grid */}
        {loading ? (
          <div className="text-center py-16 text-frost-dim text-sm">Loading...</div>
        ) : cards.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-frost-dim text-sm">Nothing here yet. Check back soon.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {cards.map((card) => (
              <ShopCard key={card.id} card={card} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > 50 && (
          <div className="flex justify-center gap-4 mt-10">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light disabled:opacity-30 hover:border-ember/30 transition-colors"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-sm text-frost-dim">Page {page}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={cards.length < 50}
              className="px-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light disabled:opacity-30 hover:border-ember/30 transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

const ShopCard = ({ card }) => {
  return (
    <a
      href={card.ebay_url}
      target="_blank"
      rel="noopener noreferrer"
      className="card-surface overflow-hidden hover:border-ember/30 transition-all group cursor-pointer"
    >
      {/* Image */}
      <div className="aspect-[2.5/3.5] bg-surface-raised relative overflow-hidden">
        {card.image_url ? (
          <img
            src={card.image_url}
            alt={card.title}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">
            No Image
          </div>
        )}
        {/* Price badge */}
        {card.price && (
          <div className="absolute bottom-2 right-2 bg-surface-base/90 backdrop-blur-sm rounded-md px-2.5 py-1">
            <span className="text-sm font-mono font-bold text-gain">${card.price.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-2.5">
        <div className="text-xs font-medium text-frost-light line-clamp-2 leading-relaxed">{card.title}</div>
        <div className="mt-2">
          <span className="text-[10px] bg-ember/10 text-ember px-2 py-0.5 rounded-full">
            Buy Now
          </span>
        </div>
      </div>
    </a>
  );
};

export default Shop;
