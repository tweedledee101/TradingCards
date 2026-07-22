import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../auth/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.ragnarokgamez.com');

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const { getToken } = useAuth();

  const authHeaders = () => {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/api/marketplace/my-orders`, { headers: authHeaders() });
      setOrders(resp.data.orders || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const markReceived = async (id) => {
    try {
      await axios.post(`${API_BASE}/api/marketplace/orders/${id}/delivered`, {}, { headers: authHeaders() });
      load();
    } catch (err) { alert('Could not update order'); }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-[60vh]"><div className="text-frost-dim text-sm">Loading your orders...</div></div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Your Orders</h1>
      <p className="text-sm text-frost-dim mb-6">
        Sellers ship Ragnarok Exclusive orders within 3 business days. You'll see a photo confirmation
        and tracking number here the moment it ships - no need to email to ask.
      </p>

      {orders.length === 0 ? (
        <div className="card-surface p-12 text-center">
          <div className="text-frost-light font-medium mb-1">No orders yet</div>
          <div className="text-xs text-frost-dim">Purchases from the Shop will show up here.</div>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map(o => <OrderRow key={o.id} order={o} onMarkReceived={() => markReceived(o.id)} />)}
        </div>
      )}
    </div>
  );
};

const STATUS_STEPS = ['paid', 'shipped', 'delivered'];

const OrderRow = ({ order, onMarkReceived }) => {
  const effectiveStatus = order.delivered_at ? 'delivered' : order.status;
  const stepIndex = STATUS_STEPS.indexOf(effectiveStatus);

  return (
    <div className="card-surface p-4">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="text-sm font-medium text-frost-light">{order.listing_title || `Order #${order.id}`}</div>
          <div className="text-xs text-frost-dim mt-0.5">
            ${(order.price_cents / 100).toFixed(2)} + ${(order.shipping_cents / 100).toFixed(2)} shipping · {order.created_at?.slice(0, 10)}
          </div>
        </div>
      </div>

      {/* Status stepper */}
      <div className="flex items-center gap-2 mb-3">
        {['Paid', 'Shipped', 'Delivered'].map((label, i) => (
          <div key={label} className="flex items-center gap-2 flex-1">
            <div className={`flex-1 h-1.5 rounded-full ${i <= stepIndex ? 'bg-gain' : 'bg-surface-raised'}`} />
            <span className={`text-[10px] whitespace-nowrap ${i <= stepIndex ? 'text-gain font-medium' : 'text-frost-dim'}`}>{label}</span>
          </div>
        ))}
      </div>

      {effectiveStatus === 'paid' && (
        <div className="text-xs text-frost-dim">
          {order.is_overdue ? (
            <span className="text-loss font-medium">This is running past the 3-day ship window - it's on us, not you.</span>
          ) : (
            <>Expected to ship by <span className="text-frost-light font-medium">{order.ship_by_date}</span></>
          )}
        </div>
      )}

      {(effectiveStatus === 'shipped' || effectiveStatus === 'delivered') && (
        <div className="flex items-center gap-3 mt-2">
          {order.shipment_photo_url && (
            <img src={order.shipment_photo_url} alt="Shipment proof" className="w-16 h-16 object-cover rounded-lg border border-surface-border" />
          )}
          <div className="text-xs text-frost-dim">
            {order.tracking_number ? (
              <div>
                {order.carrier || 'Tracking'}:{' '}
                {order.tracking_url ? (
                  <a href={order.tracking_url} target="_blank" rel="noopener noreferrer" className="text-ember hover:underline">{order.tracking_number}</a>
                ) : order.tracking_number}
              </div>
            ) : (
              <div>Shipped - no tracking number given</div>
            )}
            {effectiveStatus === 'shipped' && (
              <button onClick={onMarkReceived} className="mt-2 px-3 py-1 rounded-lg text-[11px] font-medium bg-gain/10 text-gain border border-gain/20 hover:bg-gain/20 transition-colors">
                Mark as Received
              </button>
            )}
            {effectiveStatus === 'delivered' && (
              <div className="mt-1 text-gain font-medium">Delivered {order.delivered_at?.slice(0, 10)}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Orders;
