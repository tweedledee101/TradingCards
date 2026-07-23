import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import axios from 'axios';
import { useAuth } from '../auth/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');
const SITE_ORIGIN = typeof window !== 'undefined' ? window.location.origin : 'https://ragnarokgamez.com';

const SellerDashboard = () => {
  const [listings, setListings] = useState([]);
  const [orders, setOrders] = useState([]);
  const [tab, setTab] = useState('listings');
  const [showForm, setShowForm] = useState(false);
  const [payoutsReady, setPayoutsReady] = useState(null); // null = still loading
  const [connecting, setConnecting] = useState(false);
  const { getToken } = useAuth();

  const authHeaders = () => {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  useEffect(() => { fetchData(); fetchMe(); }, []);

  const fetchMe = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/api/auth/me`, { headers: authHeaders() });
      setPayoutsReady(!!resp.data.user?.payouts_ready);
    } catch (err) { console.error(err); setPayoutsReady(false); }
  };

  const fetchData = async () => {
    try {
      const headers = authHeaders();
      const [listResp, orderResp] = await Promise.all([
        axios.get(`${API_BASE}/api/marketplace/listings`, { headers }),
        axios.get(`${API_BASE}/api/marketplace/orders`, { headers }),
      ]);
      setListings(listResp.data.listings || []);
      setOrders(orderResp.data.orders || []);
    } catch (err) { console.error(err); }
  };

  const connectStripe = async () => {
    setConnecting(true);
    try {
      const resp = await axios.post(`${API_BASE}/api/marketplace/seller/onboard`, {}, { headers: authHeaders() });
      window.location.href = resp.data.url;
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not start Stripe onboarding');
      setConnecting(false);
    }
  };

  const openOrders = orders.filter(o => o.status === 'paid').length;
  const overdueOrders = orders.filter(o => o.is_overdue).length;

  return (
    <div className="min-h-screen bg-surface">
      <nav className="border-b border-surface-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="Ragnarok" className="w-10 h-10" />
            <span className="text-base font-display font-semibold text-frost-light">Seller Dashboard</span>
          </a>
          <a href="/market" className="text-sm text-frost-dim hover:text-ember">← Back to Market</a>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Stripe Connect gate */}
        {payoutsReady === false && (
          <div className="card-surface p-5 mb-6 border-ember/40 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="text-sm font-medium text-frost-light">Connect Stripe to start selling</div>
              <div className="text-xs text-frost-dim mt-1">
                Payouts run through Stripe Connect. You'll need this before you can create listings or get paid.
                In test mode you can use Stripe's test values (e.g. phone 000-000-0000, DOB 01/01/1901, routing
                110000000 / account 000123456789) — no real bank/identity info needed to finish onboarding.
              </div>
            </div>
            <button onClick={connectStripe} disabled={connecting} className="shrink-0 px-4 py-2 rounded-lg text-sm font-medium bg-ember text-white disabled:opacity-50">
              {connecting ? 'Redirecting...' : 'Connect Stripe'}
            </button>
          </div>
        )}

        {overdueOrders > 0 && (
          <div className="card-surface p-4 mb-6 border-loss/40 bg-loss/5">
            <div className="text-sm font-medium text-loss">
              {overdueOrders} order{overdueOrders !== 1 ? 's are' : ' is'} past the 3-day ship-by date
            </div>
            <div className="text-xs text-frost-dim mt-1">Buyers expect delivery within a week of paying - ship these first.</div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button onClick={() => setTab('listings')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'listings' ? 'bg-ember text-white' : 'bg-surface-card text-frost-dim border border-surface-border'}`}>
            My Listings ({listings.length})
          </button>
          <button onClick={() => setTab('orders')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'orders' ? 'bg-ember text-white' : 'bg-surface-card text-frost-dim border border-surface-border'}`}>
            Orders ({orders.length}){openOrders > 0 ? ` · ${openOrders} to ship` : ''}
          </button>
          <button
            onClick={() => setShowForm(true)}
            disabled={!payoutsReady}
            title={!payoutsReady ? 'Connect Stripe first' : ''}
            className="ml-auto px-4 py-2 rounded-lg text-sm font-medium bg-gain text-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            + New Listing
          </button>
        </div>

        {/* Listings Tab */}
        {tab === 'listings' && (
          <div className="grid gap-3">
            {listings.length === 0 ? (
              <p className="text-frost-dim text-sm py-8 text-center">No listings yet. Create your first one!</p>
            ) : listings.map(l => (
              <div key={l.id} className="card-surface p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {l.image_urls?.[0] && <img src={l.image_urls[0]} className="w-12 h-16 object-cover rounded" />}
                  <div>
                    <div className="text-sm font-medium text-frost-light">{l.title}</div>
                    <div className="text-xs text-frost-dim">{l.category} • {l.condition}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono font-bold text-gain">${(l.price_cents / 100).toFixed(2)}</div>
                  <div className={`text-xs ${l.status === 'active' ? 'text-gain' : 'text-frost-dim'}`}>{l.status}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Orders Tab */}
        {tab === 'orders' && (
          <div className="grid gap-3">
            {orders.length === 0 ? (
              <p className="text-frost-dim text-sm py-8 text-center">No orders yet.</p>
            ) : orders.map(o => (
              <OrderCard key={o.id} order={o} authHeaders={authHeaders} />
            ))}
          </div>
        )}

        {/* Listing Form Modal */}
        {showForm && <ListingForm authHeaders={authHeaders} onClose={() => { setShowForm(false); fetchData(); }} />}
      </div>
    </div>
  );
};

const OrderCard = ({ order }) => {
  const shipUrl = `${SITE_ORIGIN}/ship/${order.id}`;
  const needsShipping = order.status === 'paid';

  return (
    <div className="card-surface p-4">
      <div className="flex justify-between items-start gap-4">
        <div className="min-w-0">
          <div className="text-sm font-medium text-frost-light truncate">{order.listing_title || `Order #${order.id}`}</div>
          <div className="text-xs text-frost-dim mt-1">
            ${(order.price_cents / 100).toFixed(2)} + ${(order.shipping_cents / 100).toFixed(2)} shipping
          </div>
          {order.shipping_address && (
            <div className="text-xs text-frost-dim mt-2">
              Ship to: {order.shipping_address.line1}, {order.shipping_address.city} {order.shipping_address.state} {order.shipping_address.postal_code}
            </div>
          )}
          {order.ship_by_date && (
            <div className={`text-xs mt-1 font-medium ${order.is_overdue ? 'text-loss' : 'text-frost-dim'}`}>
              {order.is_overdue ? 'Overdue - ' : 'Ship by '}{order.ship_by_date}
            </div>
          )}
        </div>
        <span className={`shrink-0 text-xs px-2 py-1 rounded-full ${
          order.status === 'paid' ? 'bg-ember/20 text-ember'
          : order.status === 'shipped' ? 'bg-gain/20 text-gain'
          : 'bg-frost-dim/20 text-frost-dim'
        }`}>
          {order.delivered_at ? 'delivered' : order.status}
        </span>
      </div>

      {needsShipping && (
        <div className="mt-4 pt-4 border-t border-surface-border flex items-center gap-4">
          <div className="bg-white p-1.5 rounded-lg shrink-0">
            <QRCodeSVG value={shipUrl} size={64} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs text-frost-dim mb-1.5">Scan while packing, or confirm from here:</div>
            <Link to={`/ship/${order.id}`} className="inline-block px-3 py-1.5 rounded-lg text-xs font-medium bg-ember text-white hover:bg-ember-glow transition-colors">
              Confirm Shipment
            </Link>
          </div>
        </div>
      )}

      {order.shipment_photo_url && (
        <div className="mt-3 flex items-center gap-3">
          <img src={order.shipment_photo_url} alt="Shipment proof" className="w-14 h-14 object-cover rounded-lg border border-surface-border" />
          <div className="text-xs text-frost-dim">
            {order.tracking_number ? (
              <>
                {order.carrier || 'Tracking'}: {order.tracking_url ? (
                  <a href={order.tracking_url} target="_blank" rel="noopener noreferrer" className="text-ember hover:underline">{order.tracking_number}</a>
                ) : order.tracking_number}
              </>
            ) : 'Shipped - no tracking number on file'}
          </div>
        </div>
      )}
    </div>
  );
};

const ListingForm = ({ authHeaders, onClose }) => {
  const [methods, setMethods] = useState([]);
  const [form, setForm] = useState({
    title: '', description: '', price: '', category: 'Baseball', condition: 'Near Mint',
    shipping_method: 'single_card', shipping: '', image_url: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [feeCents, setFeeCents] = useState(100);
  const [guidance, setGuidance] = useState(null);
  const [checkingPrice, setCheckingPrice] = useState(false);

  useEffect(() => {
    axios.get(`${API_BASE}/api/marketplace/shipping-methods`).then(resp => {
      const list = resp.data.methods || [];
      setMethods(list);
      const first = list.find(m => m.code === 'single_card') || list[0];
      if (first) setForm(f => ({ ...f, shipping_method: first.code, shipping: (first.default_cents / 100).toFixed(2) }));
    }).catch(() => {});
    axios.get(`${API_BASE}/api/marketplace/fees`)
      .then(r => setFeeCents(r.data.platform_fee_cents ?? 100))
      .catch(() => {});
  }, []);

  const runPriceCheck = async () => {
    if (form.title.trim().length < 3) return;
    setCheckingPrice(true);
    try {
      const resp = await axios.get(`${API_BASE}/api/marketplace/pricing-guidance`, {
        params: { query: form.title }, headers: authHeaders(),
      });
      setGuidance(resp.data);
    } catch {
      setGuidance({ sample_size: 0, message: 'Could not fetch pricing right now.' });
    } finally {
      setCheckingPrice(false);
    }
  };

  const handleMethodChange = (code) => {
    const method = methods.find(m => m.code === code);
    setForm(f => ({ ...f, shipping_method: code, shipping: method ? (method.default_cents / 100).toFixed(2) : f.shipping }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API_BASE}/api/marketplace/listings`, {
        title: form.title,
        description: form.description,
        price_cents: Math.round(parseFloat(form.price) * 100),
        category: form.category,
        condition: form.condition,
        shipping_method: form.shipping_method,
        shipping_cents: Math.round(parseFloat(form.shipping || 0) * 100),
        image_urls: form.image_url ? [form.image_url] : [],
      }, { headers: authHeaders() });
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error creating listing');
    } finally { setSubmitting(false); }
  };

  const selectedMethod = methods.find(m => m.code === form.shipping_method);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <form onSubmit={handleSubmit} className="bg-surface-card rounded-xl p-6 w-full max-w-md border border-surface-border max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-display font-bold text-frost-light mb-4">New Listing</h2>
        <div className="grid gap-3">
          <input required placeholder="Title" value={form.title} onChange={e => setForm({...form, title: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
          <textarea placeholder="Description" value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light h-20" />
          <div>
            <div className="flex gap-2">
              <input required type="number" step="0.01" min="2" placeholder="Price ($)" value={form.price} onChange={e => setForm({...form, price: e.target.value})} className="flex-1 px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
              <button type="button" onClick={runPriceCheck} disabled={checkingPrice || form.title.trim().length < 3} title="See recent sold-comp pricing for a card like this" className="shrink-0 px-3 py-2 rounded-lg text-xs font-medium bg-ember/15 text-ember-light border border-ember/25 hover:bg-ember/25 disabled:opacity-40">
                {checkingPrice ? '…' : '💡 Price check'}
              </button>
            </div>
            {guidance && (
              <div className="mt-2 rounded-lg border border-surface-border bg-surface-raised/60 p-3 text-xs">
                {guidance.sample_size > 0 ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-frost-dim">Recent sold comps</span>
                      <span className="text-frost-dim">{guidance.sample_size} sales / 90d</span>
                    </div>
                    <div className="mt-1.5 grid grid-cols-3 gap-2 text-center">
                      <div><div className="text-[10px] text-frost-dim">Avg 30d</div><div className="font-mono font-semibold text-frost-light">{guidance.avg_sale_price_30d ? `$${guidance.avg_sale_price_30d}` : '—'}</div></div>
                      <div><div className="text-[10px] text-frost-dim">Range 90d</div><div className="font-mono font-semibold text-frost-light">${guidance.low_90d}–${guidance.high_90d}</div></div>
                      <div><div className="text-[10px] text-frost-dim">~Days/sale</div><div className="font-mono font-semibold text-frost-light">{guidance.typical_days_between_sales ?? '—'}</div></div>
                    </div>
                    {guidance.recommended_price && (
                      <button type="button" onClick={() => setForm(f => ({ ...f, price: String(guidance.recommended_price) }))} className="mt-2 w-full px-2 py-1.5 rounded-md text-[11px] font-medium bg-ember/90 hover:bg-ember text-white">
                        Use suggested ${guidance.recommended_price}
                      </button>
                    )}
                    <div className="mt-1.5 text-[9px] text-frost-dim leading-snug">{guidance.disclaimer}</div>
                  </>
                ) : (
                  <span className="text-frost-dim">{guidance.message || 'No comps found for that card yet.'}</span>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">Shipping Method</label>
            <select value={form.shipping_method} onChange={e => handleMethodChange(e.target.value)} className="w-full px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              {methods.map(m => <option key={m.code} value={m.code}>{m.label}</option>)}
            </select>
            {selectedMethod && <div className="text-[10px] text-frost-dim mt-1">{selectedMethod.estimate}</div>}
          </div>
          <input type="number" step="0.01" min="0" placeholder="Shipping charge ($)" value={form.shipping} onChange={e => setForm({...form, shipping: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />

          <div className="grid grid-cols-2 gap-3">
            <select value={form.category} onChange={e => setForm({...form, category: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              <option>Baseball</option><option>Football</option><option>Basketball</option><option>Soccer</option><option>Hockey</option><option>Pokémon</option><option>Yu-Gi-Oh!</option><option>Magic: The Gathering</option><option>Other</option>
            </select>
            <select value={form.condition} onChange={e => setForm({...form, condition: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light">
              <option>Mint</option><option>Near Mint</option><option>Excellent</option><option>Good</option><option>Fair</option><option>PSA 10</option><option>PSA 9</option><option>BGS 9.5</option>
            </select>
          </div>
          <input placeholder="Image URL" value={form.image_url} onChange={e => setForm({...form, image_url: e.target.value})} className="px-3 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-light" />
        </div>

        {form.price && (
          <div className="mt-4 rounded-lg bg-gain/10 border border-gain/20 p-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-frost-dim">You receive</span>
              <span className="font-mono font-bold text-gain">
                ${(parseFloat(form.price || 0) + parseFloat(form.shipping || 0)).toFixed(2)}
              </span>
            </div>
            <div className="mt-1 text-[10px] text-frost-dim leading-snug">
              Buyers pay a flat ${(feeCents / 100).toFixed(2)} marketplace fee — you keep 100% of your sale price. No percentage cut.
            </div>
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button type="button" onClick={onClose} className="flex-1 px-4 py-2 rounded-lg text-sm bg-surface border border-surface-border text-frost-dim">Cancel</button>
          <button type="submit" disabled={submitting} className="flex-1 px-4 py-2 rounded-lg text-sm bg-ember text-white font-medium disabled:opacity-50">
            {submitting ? 'Posting...' : 'List Card'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SellerDashboard;
