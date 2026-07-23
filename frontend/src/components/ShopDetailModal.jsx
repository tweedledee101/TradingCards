import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const ShopDetailModal = ({ item, onClose, authenticated, login, getToken }) => {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [buying, setBuying] = useState(false);
  const [feeCents, setFeeCents] = useState(100);

  useEffect(() => {
    axios.get(`${API_BASE}/api/marketplace/fees`)
      .then(r => setFeeCents(r.data.platform_fee_cents ?? 100))
      .catch(() => {});
  }, []);

  const handleBuy = async () => {
    if (!authenticated) { login(); return; }
    setBuying(true);
    try {
      const token = getToken();
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await axios.post(`${API_BASE}/api/marketplace/checkout`, { listing_id: item.id }, { headers });
      window.location.href = resp.data.checkout_url;
    } catch (err) {
      alert(err.response?.data?.detail || 'Checkout error');
      setBuying(false);
    }
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    setDetail(null);
    setStats(null);

    const url = item.source === 'ragnarok'
      ? `${API_BASE}/api/marketplace/listings/${item.id}`
      : `${API_BASE}/api/shop/ebay/${item.id}`;

    axios.get(url).then(resp => {
      if (!active) return;
      setDetail(resp.data);
      const playerName = resp.data.guessed_player_name;
      if (playerName) {
        setStatsLoading(true);
        axios.get(`${API_BASE}/api/market/card-stats`, { params: { player: playerName } })
          .then(r => { if (active) setStats({ ...r.data, matched_name: playerName }); })
          .catch(() => {})
          .finally(() => { if (active) setStatsLoading(false); });
      }
    }).catch(err => console.error(err))
      .finally(() => { if (active) setLoading(false); });

    return () => { active = false; };
  }, [item.source, item.id]);

  const images = item.source === 'ragnarok'
    ? (detail?.image_urls?.length ? detail.image_urls : (item.image_urls || []))
    : (detail?.images?.length ? detail.images : (item.image_url ? [item.image_url] : []));

  const hasRealStats = stats && (stats.total_sales > 0 || stats.active_listings > 0);

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-surface-card rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-surface-border"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-surface-card/95 backdrop-blur-sm border-b border-surface-border px-5 py-3 flex items-center justify-between">
          <span className="text-xs font-medium text-frost-dim uppercase tracking-wide">
            {item.source === 'ragnarok' ? 'Ragnarok Exclusive' : 'eBay Listing'}
          </span>
          <button onClick={onClose} className="text-frost-dim hover:text-frost-light text-sm px-2">✕ Close</button>
        </div>

        {loading ? (
          <div className="py-20 text-center text-frost-dim text-sm">Loading...</div>
        ) : (
          <div className="p-5">
            <div className="flex gap-5 flex-wrap sm:flex-nowrap">
              <div className="w-full sm:w-48 aspect-[2.5/3.5] bg-surface-raised rounded-lg overflow-hidden shrink-0">
                {images[0] ? (
                  <img src={images[0]} alt={item.title} className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">No Image</div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-display font-semibold text-frost-light leading-snug">
                  {detail?.title || item.title}
                </h2>
                <div className="text-2xl font-mono font-bold text-gain mt-2">
                  ${(item.price || 0).toFixed(2)}
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  {detail?.condition && <InfoRow label="Condition" value={detail.condition} />}
                  {item.source === 'ragnarok' && detail?.category && <InfoRow label="Category" value={detail.category} />}
                  {item.source === 'ragnarok' && detail?.seller_name && <InfoRow label="Seller" value={detail.seller_name} />}
                  {item.source === 'ebay' && detail?.watch_count != null && <InfoRow label="Watchers" value={detail.watch_count} />}
                  {item.source === 'ragnarok' && item.shipping_cents > 0 && (
                    <InfoRow label="Shipping" value={`$${(item.shipping_cents / 100).toFixed(2)}`} />
                  )}
                </div>

                {item.source === 'ragnarok' && (
                  <div className="mt-3 rounded-lg bg-surface-raised/50 border border-surface-border p-2.5 text-xs space-y-1">
                    <div className="flex justify-between"><span className="text-frost-dim">Item</span><span className="font-mono text-frost-light">${(item.price || 0).toFixed(2)}</span></div>
                    {item.shipping_cents > 0 && (
                      <div className="flex justify-between"><span className="text-frost-dim">Shipping</span><span className="font-mono text-frost-light">${(item.shipping_cents / 100).toFixed(2)}</span></div>
                    )}
                    <div className="flex justify-between"><span className="text-frost-dim">Marketplace fee</span><span className="font-mono text-frost-light">${(feeCents / 100).toFixed(2)}</span></div>
                    <div className="flex justify-between border-t border-surface-border pt-1 mt-1">
                      <span className="text-frost-light font-medium">Total</span>
                      <span className="font-mono font-bold text-gain">${((item.price || 0) + (item.shipping_cents || 0) / 100 + feeCents / 100).toFixed(2)}</span>
                    </div>
                    <div className="text-[10px] text-frost-dim pt-0.5">🛡️ Protected by escrow — funds release to the seller only after delivery.</div>
                  </div>
                )}

                <div className="mt-4">
                  {item.source === 'ragnarok' ? (
                    <button
                      onClick={handleBuy}
                      disabled={buying}
                      className="px-5 py-2 rounded-lg text-sm font-medium bg-ember hover:bg-ember-glow text-white disabled:opacity-50"
                    >
                      {buying ? 'Redirecting...' : authenticated ? 'Buy Now' : 'Sign In to Buy'}
                    </button>
                  ) : (
                    <a
                      href={detail?.ebay_url || item.ebay_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-5 py-2 rounded-lg text-sm font-medium bg-ember/10 text-ember hover:bg-ember/20"
                    >
                      View & Buy on eBay →
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Item specifics (eBay) */}
            {item.source === 'ebay' && detail?.specifics && Object.keys(detail.specifics).length > 0 && (
              <div className="mt-5 border-t border-surface-border pt-4">
                <div className="text-label mb-2">Item Specifics</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(detail.specifics).map(([k, v]) => (
                    <InfoRow key={k} label={k} value={v} />
                  ))}
                </div>
              </div>
            )}

            {/* Description */}
            {detail?.description && (
              <div className="mt-5 border-t border-surface-border pt-4">
                <div className="text-label mb-2">Description</div>
                <div
                  className="text-xs text-frost-dim leading-relaxed max-h-40 overflow-y-auto"
                  dangerouslySetInnerHTML={{ __html: detail.description }}
                />
              </div>
            )}

            {/* Market stats */}
            <div className="mt-5 border-t border-surface-border pt-4">
              <div className="text-label mb-2">Market Stats</div>
              {statsLoading ? (
                <div className="text-xs text-frost-dim">Checking market data...</div>
              ) : hasRealStats ? (
                <>
                  <div className="text-[10px] text-frost-dim mb-2">
                    Matched to tracked player: <span className="text-frost-light">{stats.matched_name}</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <StatBox label="Avg Sale (30d)" value={stats.avg_sale_price_30d ? `$${stats.avg_sale_price_30d}` : '—'} />
                    <StatBox label="Sales (30d)" value={stats.recent_sales_30d} />
                    <StatBox label="Active Listings" value={stats.active_listings} />
                    <StatBox label="Velocity" value={stats.velocity} />
                  </div>
                  {stats.sell_through?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-[10px] text-frost-dim mb-1.5">Sell-through by price vs. market rate (90d)</div>
                      <div className="space-y-1">
                        {stats.sell_through.map((b, i) => (
                          <div key={i} className="flex items-center justify-between text-xs bg-surface-raised rounded px-2.5 py-1.5">
                            <span className="text-frost-dim">{b.bucket}</span>
                            <span className="text-frost-light font-mono">{b.sales} sales ({b.pct_of_total}%)</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-xs text-frost-dim">
                  No market stats available for this specific card yet — only ~40-60 players are tracked by the pipeline right now.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const InfoRow = ({ label, value }) => (
  <div className="flex items-baseline gap-1.5 min-w-0">
    <span className="text-frost-dim shrink-0">{label}:</span>
    <span className="text-frost-light truncate">{value}</span>
  </div>
);

const StatBox = ({ label, value }) => (
  <div className="bg-surface-raised rounded-lg p-2.5 text-center">
    <div className="text-[10px] text-frost-dim mb-1">{label}</div>
    <div className="text-sm font-mono font-bold text-frost-light">{value ?? '—'}</div>
  </div>
);

export default ShopDetailModal;
