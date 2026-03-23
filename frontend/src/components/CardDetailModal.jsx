import { useState, useEffect } from 'react';
import { getPlayerStats, getPlayerPriceHistory, getPlayerTiming, createScheduledBid } from '../api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';

const calcRemaining = (endTime) => {
  if (!endTime) return 0;
  return Math.max(0, Math.floor((new Date(endTime).getTime() - Date.now()) / 1000));
};

const fmtCountdown = (secs) => {
  if (secs <= 0) return 'Ended';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  const pad = (n) => n.toString().padStart(2, '0');
  if (h >= 24) return `${Math.floor(h/24)}d ${h%24}h ${pad(m)}m ${pad(s)}s`;
  if (h >= 1) return `${h}h ${pad(m)}m ${pad(s)}s`;
  return `${m}:${pad(s)}`;
};

const TABS = ['Overview', 'Sell-Through', 'Price History', 'Timing'];

const CardDetailModal = ({ opportunity, type, onClose }) => {
  const [tab, setTab] = useState('Overview');
  const [stats, setStats] = useState(null);
  const [priceHistory, setPriceHistory] = useState(null);
  const [timing, setTiming] = useState(null);
  const [imgError, setImgError] = useState(false);
  const [showSnipe, setShowSnipe] = useState(false);
  const [showManualBid, setShowManualBid] = useState(false);
  const [snipeSeconds, setSnipeSeconds] = useState(10);
  const [snipeStatus, setSnipeStatus] = useState(null);
  const [snipeBid, setSnipeBid] = useState(null);
  const [manualBid, setManualBid] = useState('');
  const [manualSeconds, setManualSeconds] = useState(10);

  const isAuction = type === 'auction';
  const playerName = opportunity.player_name;
  const imageUrl = opportunity.image_url;
  const cardYear = opportunity.card_year;
  const cardSet = opportunity.card_set;
  const cardNumber = opportunity.card_number;
  const parallel = opportunity.parallel;
  const priceSource = opportunity.price_source || 'scp';

  const buyPrice = isAuction ? opportunity.current_bid : opportunity.arbitrage?.buy_price;
  const scpPrice = isAuction ? opportunity.scp_sell_price : opportunity.arbitrage?.sell_price;
  const netProfit = isAuction ? opportunity.net_profit : opportunity.arbitrage?.net_profit;
  const roi = isAuction ? opportunity.roi : opportunity.arbitrage?.roi;
  const shipping = isAuction ? opportunity.shipping : 0;
  const scpGrade9 = isAuction ? opportunity.scp_grade_9 : opportunity.arbitrage?.scp_grade_9;
  const scpPsa10 = isAuction ? opportunity.scp_psa_10 : opportunity.arbitrage?.scp_psa_10;
  const ebayUrl = isAuction ? opportunity.ebay_url : opportunity.buy_listings?.[0]?.url;
  const endTime = opportunity.end_time;

  // Recommended snipe: work backwards from SCP after fees minus $10 target profit
  const FEE_RATE = 0.13;
  const MIN_TARGET_PROFIT = 10;
  const recSnipe = scpPrice ? Math.floor((scpPrice * (1 - FEE_RATE) - MIN_TARGET_PROFIT - (shipping || 0)) * 100) / 100 : null;

  useEffect(() => {
    if (recSnipe && recSnipe > 0 && snipeBid === null) setSnipeBid(recSnipe.toFixed(2));
  }, [recSnipe]);

  const [remaining, setRemaining] = useState(() => calcRemaining(endTime));

  // Load data on mount
  useEffect(() => {
    if (!playerName) return;
    getPlayerStats(playerName).then(setStats).catch(() => {});
    getPlayerPriceHistory(playerName).then(setPriceHistory).catch(() => {});
    getPlayerTiming(playerName).then(setTiming).catch(() => {});
  }, [playerName]);

  // Live countdown
  useEffect(() => {
    if (!endTime) return;
    const id = setInterval(() => setRemaining(calcRemaining(endTime)), 1000);
    return () => clearInterval(id);
  }, [endTime]);

  // Escape to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const sourceBadge = {
    scp: { label: 'SCP Verified', cls: 'bg-gain/15 text-gain border-gain/20' },
    sold_comps: { label: 'Sold Comps', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/20' },
    ebay_comps: { label: 'Market Comps', cls: 'bg-amber-500/15 text-amber-400 border-amber-500/20' },
  }[priceSource] || { label: 'SCP Verified', cls: 'bg-gain/15 text-gain border-gain/20' };

  // Capital efficiency calc
  const totalCost = (buyPrice || 0) + (shipping || 0);
  const sellThrough = stats?.sell_through || [];
  const bestBucket = sellThrough.find(b => {
    if (!scpPrice || !totalCost) return false;
    const ratio = totalCost / scpPrice;
    if (ratio < 0.80) return b.bucket === '<80% of SCP';
    if (ratio < 0.90) return b.bucket === '80-90%';
    if (ratio < 1.00) return b.bucket === '90-100%';
    return b.bucket === '100-110%';
  });
  const daysToSell = bestBucket?.avg_days_to_sell;
  const dailyReturn = daysToSell && daysToSell > 0 && netProfit ? (netProfit / daysToSell) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

      <div className="relative bg-surface-card border border-surface-border rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}>

        {/* Close */}
        <button onClick={onClose}
          className="absolute top-3 right-3 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-surface-raised text-frost-dim hover:text-frost-light transition-colors text-sm">
          X
        </button>

        {/* ===== HERO ===== */}
        <div className="flex flex-col md:flex-row gap-5 p-5 pb-4 border-b border-surface-border shrink-0">
          {/* Image */}
          <div className="w-32 md:w-40 shrink-0 self-center md:self-start">
            <div className="aspect-[3/4] rounded-xl overflow-hidden bg-surface-raised">
              {imageUrl && !imgError ? (
                <img src={imageUrl} alt="" className="w-full h-full object-contain" onError={() => setImgError(true)} />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">No Image</div>
              )}
            </div>
          </div>

          {/* Hero right */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div>
                <h2 className="text-lg font-display font-semibold text-frost-light leading-tight">{playerName}</h2>
                <div className="text-xs text-frost-dim mt-0.5">
                  {cardYear} {cardSet}{cardNumber ? ` #${cardNumber}` : ''}
                  {parallel && parallel !== 'Base' ? ` - ${parallel}` : ''}
                </div>
              </div>
              <span className={`text-[9px] font-semibold px-2 py-0.5 rounded border shrink-0 ${sourceBadge.cls}`}>
                {sourceBadge.label}
              </span>
            </div>

            {/* Key numbers row */}
            <div className="flex flex-wrap items-end gap-4 mb-3">
              <div>
                <div className="text-[9px] uppercase text-frost-dim">{isAuction ? 'Current Bid' : 'Buy Price'}</div>
                <div className="text-xl font-mono font-bold text-frost-light">${buyPrice?.toFixed(2)}</div>
              </div>
              <div className="text-frost-dim text-lg font-light">/</div>
              <div>
                <div className="text-[9px] uppercase text-frost-dim">SCP Market</div>
                <div className="text-xl font-mono font-bold text-frost-light">${scpPrice?.toFixed(2)}</div>
              </div>
              <div className="ml-auto text-right">
                <div className="text-xl font-mono font-bold text-gain">+${netProfit?.toFixed(2)}</div>
                <div className="text-xs font-mono text-gain/70">{roi?.toFixed(0)}% ROI</div>
              </div>
            </div>

            {/* Timer row -- context, not action */}
            {isAuction && (
              <div className="flex items-center gap-3 mb-3">
                {endTime && (
                  <span className={`text-xs font-mono font-bold ${remaining <= 0 ? 'text-frost-dim' : remaining <= 3600 ? 'text-loss' : 'text-amber-400'}`}>
                    {fmtCountdown(remaining)}
                  </span>
                )}
                <span className="text-[10px] text-frost-dim">{opportunity.bid_count} bid{opportunity.bid_count !== 1 ? 's' : ''}</span>
                <div className="flex-1" />
                {ebayUrl && <a href={ebayUrl} target="_blank" rel="noopener noreferrer" className="text-[10px] text-frost-dim hover:text-frost-light transition-colors">eBay</a>}
                {opportunity.scp_url && <a href={opportunity.scp_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-frost-dim hover:text-frost-light transition-colors">SCP</a>}
              </div>
            )}

            {/* Primary action */}
            {snipeStatus === 'scheduled' ? (
              <div className="px-4 py-2.5 rounded-xl text-sm font-bold bg-gain/10 text-gain border border-gain/20 text-center">Bid Queued</div>
            ) : isAuction && remaining > 0 ? (
              <button onClick={() => { setShowSnipe(!showSnipe); setShowManualBid(false); }}
                className="w-full px-4 py-2.5 rounded-xl text-sm font-bold bg-ember/20 text-ember-light border border-ember/30 hover:bg-ember/30 transition-colors">
                {recSnipe > 0 ? `Snipe $${recSnipe.toFixed(2)}` : 'Place Bid'}
              </button>
            ) : !isAuction && ebayUrl ? (
              <a href={ebayUrl} target="_blank" rel="noopener noreferrer"
                className="block w-full px-4 py-2.5 rounded-xl text-sm font-bold bg-gain/15 text-gain border border-gain/20 hover:bg-gain/25 transition-colors text-center">
                Buy ${buyPrice?.toFixed(2)}
              </a>
            ) : null}

            {/* BIN secondary links */}
            {!isAuction && (
              <div className="flex items-center gap-3 mt-2">
                {ebayUrl && <a href={ebayUrl} target="_blank" rel="noopener noreferrer" className="text-[10px] text-frost-dim hover:text-frost-light transition-colors">eBay</a>}
                {opportunity.scp_url && <a href={opportunity.scp_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-frost-dim hover:text-frost-light transition-colors">SCP</a>}
              </div>
            )}

            {/* Snipe panel -- compact */}
            {showSnipe && (
              <div className="mt-3 bg-surface-raised rounded-xl p-4 border border-surface-border">
                {/* Profit headline */}
                {(() => {
                  const cb = parseFloat(snipeBid);
                  const cp = cb && scpPrice ? (scpPrice * (1 - FEE_RATE) - cb - (shipping || 0)) : null;
                  const cr = cp && cb > 0 ? (cp / (cb + (shipping || 0))) * 100 : null;
                  return cp !== null ? (
                    <div className={`text-center mb-3 py-2 rounded-lg ${cp > 0 ? 'bg-gain/8' : 'bg-loss/8'}`}>
                      <div className={`text-2xl font-mono font-bold ${cp > 0 ? 'text-gain' : 'text-loss'}`}>
                        {cp > 0 ? '+' : ''}${cp.toFixed(2)} profit
                      </div>
                      <div className="text-[10px] text-frost-dim">
                        {cr ? `${cr.toFixed(0)}% ROI` : ''}
                        {cp > 0 ? ` if you win at $${cb.toFixed(2)}` : ' -- you would lose money at this price'}
                      </div>
                    </div>
                  ) : null;
                })()}

                <div className="flex items-center gap-2 mb-3 text-[10px] text-frost-dim">
                  <span>SCP ${scpPrice?.toFixed(2)}</span>
                  <span className="text-frost-dim/30">-</span>
                  <span>13% fees</span>
                  <span className="text-frost-dim/30">-</span>
                  <span>$10 min profit</span>
                  <span className="text-frost-dim/30">=</span>
                  <span className="font-semibold text-ember-light">${recSnipe?.toFixed(2)} max</span>
                </div>

                <div className="flex items-end gap-3">
                  <div className="flex-1">
                    <input type="number" step="0.01" value={snipeBid || ''}
                      onChange={e => setSnipeBid(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg text-sm font-mono bg-surface-card border border-surface-border text-frost-light focus:outline-none focus:border-ember/40" />
                  </div>
                  <select value={snipeSeconds} onChange={e => setSnipeSeconds(Number(e.target.value))}
                    className="px-2.5 py-2 rounded-lg text-xs bg-surface-card border border-surface-border text-frost-light">
                    <option value={3}>3s</option>
                    <option value={5}>5s</option>
                    <option value={10}>10s</option>
                    <option value={15}>15s</option>
                    <option value={30}>30s</option>
                  </select>
                  <button onClick={async () => {
                    const maxBid = parseFloat(snipeBid);
                    if (!maxBid || maxBid <= 0) return;
                    try {
                      await createScheduledBid({
                        player_name: playerName, card_year: cardYear, card_set: cardSet,
                        card_number: cardNumber, parallel, max_bid: maxBid,
                        snipe_seconds: snipeSeconds, ebay_item_id: opportunity.ebay_item_id,
                        ebay_url: ebayUrl, image_url: imageUrl, scp_price: scpPrice, end_time: endTime,
                      });
                      setSnipeStatus('scheduled');
                      setShowSnipe(false);
                    } catch (err) { setSnipeStatus('error'); }
                  }}
                    className="px-5 py-2 rounded-lg text-xs font-bold bg-ember/20 text-ember-light border border-ember/30 hover:bg-ember/30 transition-colors shrink-0">
                    Queue
                  </button>
                </div>
                <div className="text-[9px] text-frost-dim mt-2">eBay OAuth required for auto-bid (coming soon)</div>
              </div>
            )}
          </div>
        </div>

        {/* ===== TABS ===== */}
        <div className="flex border-b border-surface-border shrink-0">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-xs font-medium transition-colors ${
                tab === t
                  ? 'text-ember-light border-b-2 border-ember'
                  : 'text-frost-dim hover:text-frost-light'
              }`}>
              {t}
            </button>
          ))}
        </div>

        {/* ===== TAB CONTENT ===== */}
        <div className="flex-1 overflow-y-auto p-5">

          {/* OVERVIEW TAB */}
          {tab === 'Overview' && (
            <div className="space-y-4">
              {/* Pricing grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <Stat label={isAuction ? 'Current Bid' : 'Buy Price'} value={`$${buyPrice?.toFixed(2)}`} />
                <Stat label="SCP Ungraded" value={`$${scpPrice?.toFixed(2)}`} />
                {scpGrade9 && <Stat label="SCP Grade 9" value={`$${scpGrade9.toFixed(2)}`} />}
                {scpPsa10 && <Stat label="SCP PSA 10" value={`$${scpPsa10.toFixed(2)}`} />}
                {shipping > 0 && <Stat label="Shipping" value={`$${shipping.toFixed(2)}`} />}
                <Stat label="eBay Fees (13%)" value={`$${(scpPrice * 0.13)?.toFixed(2)}`} />
                <Stat label="Net Profit" value={`+$${netProfit?.toFixed(2)}`} gain />
                <Stat label="ROI" value={`${roi?.toFixed(0)}%`} gain />
              </div>

              {/* Player analytics */}
              {stats && (
                <>
                  <SectionLabel text="Player Analytics" />
                  <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                    <MiniStat label="30d Sales" value={stats.recent_sales_30d} />
                    <MiniStat label="Avg Sale" value={stats.avg_sale_price_30d ? `$${stats.avg_sale_price_30d.toFixed(0)}` : '--'} />
                    <MiniStat label="Velocity" value={stats.velocity?.toFixed(2)} sub={velLabel(stats.velocity)} />
                    <MiniStat label="Active" value={stats.active_listings} />
                    <MiniStat label="Cards" value={stats.cards} />
                    <MiniStat label="SCP Rates" value={stats.market_rates} />
                  </div>
                </>
              )}

              {/* Capital efficiency callout */}
              {dailyReturn && (
                <div className="bg-gain/5 border border-gain/15 rounded-lg px-4 py-3">
                  <div className="text-xs text-gain font-semibold mb-1">Capital Efficiency</div>
                  <div className="text-sm text-frost-light">
                    At ${totalCost.toFixed(2)} buy-in, similar cards sell in ~<span className="font-mono font-bold text-gain">{daysToSell}d</span>.
                    That's <span className="font-mono font-bold text-gain">${dailyReturn.toFixed(2)}/day</span> return on capital.
                  </div>
                </div>
              )}

              {/* QA flags */}
              {opportunity.qa_flags?.length > 0 && (
                <div className="space-y-1">
                  {opportunity.qa_flags.map((f, i) => (
                    <div key={i} className={`text-xs px-2 py-1 rounded ${
                      f.severity === 'critical' ? 'bg-loss/10 text-loss border border-loss/20'
                      : f.severity === 'warning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      : 'bg-surface-raised text-frost-dim border border-surface-border'
                    }`}>
                      <span className="font-medium">{f.rule}</span>: {f.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* SELL-THROUGH TAB */}
          {tab === 'Sell-Through' && (
            <div className="space-y-5">
              {sellThrough.length > 0 ? (
                <>
                  <SectionLabel text="How fast do cards sell at each price point? (90 days)" />
                  <div className="space-y-2">
                    {sellThrough.map((b, i) => {
                      const isYou = bestBucket && b.bucket === bestBucket.bucket;
                      return (
                        <div key={i} className={`flex items-center gap-3 text-xs rounded-lg px-3 py-2 ${
                          isYou ? 'bg-ember/10 border border-ember/20' : 'bg-surface-raised'
                        }`}>
                          <span className="w-24 text-frost-dim shrink-0 font-medium">{b.bucket}</span>
                          <div className="flex-1 h-5 bg-surface-card rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                b.avg_days_to_sell && b.avg_days_to_sell <= 3 ? 'bg-gain/50'
                                : b.avg_days_to_sell && b.avg_days_to_sell <= 10 ? 'bg-amber-500/40'
                                : 'bg-frost-dim/20'
                              }`}
                              style={{ width: `${Math.max(4, Math.min(100, b.pct_of_total))}%` }}
                            />
                          </div>
                          <div className="w-14 text-right">
                            <span className="font-mono font-bold text-frost-light">
                              {b.avg_days_to_sell ? `${b.avg_days_to_sell}d` : '--'}
                            </span>
                          </div>
                          <div className="w-16 text-right text-frost-dim">{b.sales} sold</div>
                          {isYou && <span className="text-[9px] text-ember-light font-bold uppercase">Your Price</span>}
                        </div>
                      );
                    })}
                  </div>

                  {/* Turnover estimate */}
                  {dailyReturn && (
                    <div className="bg-surface-raised rounded-lg p-4">
                      <SectionLabel text="Inventory Turnover Estimate" />
                      <div className="grid grid-cols-3 gap-3 mt-2">
                        <div className="text-center">
                          <div className="text-2xl font-mono font-bold text-frost-light">{daysToSell}d</div>
                          <div className="text-[9px] text-frost-dim uppercase">Est. Time to Sell</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-mono font-bold text-gain">${dailyReturn.toFixed(2)}</div>
                          <div className="text-[9px] text-frost-dim uppercase">Profit / Day</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-mono font-bold text-frost-light">
                            ${(dailyReturn * 30).toFixed(0)}
                          </div>
                          <div className="text-[9px] text-frost-dim uppercase">Monthly (if repeated)</div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <Empty text="No sell-through data yet. Run the pipeline to collect sales data." />
              )}
            </div>
          )}

          {/* PRICE HISTORY TAB */}
          {tab === 'Price History' && (
            <div className="space-y-4">
              {priceHistory?.history?.length > 1 ? (
                <>
                  <SectionLabel text={`Sale prices over ${priceHistory.days} days`} />
                  <div className="bg-surface-raised rounded-lg p-4" style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={priceHistory.history}>
                        <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }}
                          tickFormatter={d => d.slice(5)} />
                        <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} width={50}
                          tickFormatter={v => `$${v}`} />
                        <Tooltip
                          contentStyle={{ background: '#1a1d24', border: '1px solid #2d3039', borderRadius: 8, fontSize: 12 }}
                          labelStyle={{ color: '#9ca3af' }}
                          formatter={(v, name) => [`$${v.toFixed(2)}`, name === 'avg_price' ? 'Avg Price' : name]}
                        />
                        {priceHistory.scp_avg && (
                          <ReferenceLine y={priceHistory.scp_avg} stroke="#e8590c" strokeDasharray="6 3"
                            label={{ value: `SCP $${priceHistory.scp_avg}`, position: 'right', fontSize: 9, fill: '#e8590c' }} />
                        )}
                        {buyPrice && (
                          <ReferenceLine y={buyPrice} stroke="#22c55e" strokeDasharray="3 3"
                            label={{ value: `Buy $${buyPrice.toFixed(0)}`, position: 'left', fontSize: 9, fill: '#22c55e' }} />
                        )}
                        <Line type="monotone" dataKey="avg_price" stroke="#60a5fa" strokeWidth={2}
                          dot={{ r: 3, fill: '#60a5fa' }} activeDot={{ r: 5 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  {/* Min/max range */}
                  <div className="flex gap-4 text-xs text-frost-dim">
                    <span>Low: <span className="font-mono text-frost-light">
                      ${Math.min(...priceHistory.history.map(h => h.min_price)).toFixed(2)}
                    </span></span>
                    <span>High: <span className="font-mono text-frost-light">
                      ${Math.max(...priceHistory.history.map(h => h.max_price)).toFixed(2)}
                    </span></span>
                    <span>Avg: <span className="font-mono text-frost-light">
                      ${(priceHistory.history.reduce((s, h) => s + h.avg_price, 0) / priceHistory.history.length).toFixed(2)}
                    </span></span>
                  </div>
                </>
              ) : (
                <Empty text="Not enough price history data yet. Need 2+ days of sales." />
              )}
            </div>
          )}

          {/* TIMING TAB */}
          {tab === 'Timing' && (
            <div className="space-y-5">
              {timing?.by_day?.length > 0 ? (
                <>
                  <SectionLabel text="When do cards sell cheapest?" />

                  {/* Day of week chart */}
                  <div className="bg-surface-raised rounded-lg p-4">
                    <div className="text-[10px] uppercase text-frost-dim mb-2 font-semibold">Average Sale Price by Day</div>
                    <div style={{ height: 180 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={timing.by_day}>
                          <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#9ca3af' }} />
                          <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} width={50} tickFormatter={v => `$${v}`} />
                          <Tooltip
                            contentStyle={{ background: '#1a1d24', border: '1px solid #2d3039', borderRadius: 8, fontSize: 12 }}
                            formatter={(v, name) => [name === 'avg_price' ? `$${v.toFixed(2)}` : v, name === 'avg_price' ? 'Avg Price' : 'Sales']}
                          />
                          <Bar dataKey="avg_price" radius={[4, 4, 0, 0]}>
                            {timing.by_day.map((entry, i) => {
                              const min = Math.min(...timing.by_day.map(d => d.avg_price));
                              const isLowest = entry.avg_price === min;
                              return <Cell key={i} fill={isLowest ? '#22c55e' : '#3b82f6'} fillOpacity={isLowest ? 0.8 : 0.4} />;
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    {(() => {
                      const cheapest = timing.by_day.reduce((a, b) => a.avg_price < b.avg_price ? a : b);
                      const priciest = timing.by_day.reduce((a, b) => a.avg_price > b.avg_price ? a : b);
                      return (
                        <div className="text-xs text-frost-dim mt-2">
                          Cheapest: <span className="text-gain font-semibold">{cheapest.day}</span> (avg ${cheapest.avg_price.toFixed(2)})
                          {' '} | Most expensive: <span className="text-loss font-semibold">{priciest.day}</span> (avg ${priciest.avg_price.toFixed(2)})
                        </div>
                      );
                    })()}
                  </div>

                  {/* Hour of day */}
                  {timing.by_hour?.length > 0 && (
                    <div className="bg-surface-raised rounded-lg p-4">
                      <div className="text-[10px] uppercase text-frost-dim mb-2 font-semibold">Sales Volume by Hour</div>
                      <div style={{ height: 140 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={timing.by_hour}>
                            <XAxis dataKey="hour" tick={{ fontSize: 9, fill: '#6b7280' }}
                              tickFormatter={h => h === 0 ? '12a' : h < 12 ? `${h}a` : h === 12 ? '12p' : `${h-12}p`} />
                            <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} width={30} />
                            <Tooltip
                              contentStyle={{ background: '#1a1d24', border: '1px solid #2d3039', borderRadius: 8, fontSize: 12 }}
                              labelFormatter={h => `${h === 0 ? '12' : h > 12 ? h-12 : h}${h < 12 ? 'am' : 'pm'}`}
                              formatter={(v, name) => [name === 'avg_price' ? `$${v.toFixed(2)}` : v, name === 'sales' ? 'Sales' : 'Avg Price']}
                            />
                            <Bar dataKey="sales" fill="#60a5fa" fillOpacity={0.5} radius={[2, 2, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <Empty text="Not enough timing data yet. Need more sales across different days." />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const SectionLabel = ({ text }) => (
  <div className="text-[10px] uppercase tracking-wider text-frost-dim font-semibold">{text}</div>
);

const Stat = ({ label, value, gain }) => (
  <div className="bg-surface-raised rounded-lg px-3 py-2">
    <div className="text-[9px] text-frost-dim mb-0.5 uppercase">{label}</div>
    <div className={`text-sm font-mono font-semibold ${gain ? 'text-gain' : 'text-frost-light'}`}>{value}</div>
  </div>
);

const MiniStat = ({ label, value, sub }) => (
  <div className="bg-surface-raised rounded-lg px-2 py-1.5 text-center">
    <div className="text-sm font-mono font-semibold text-frost-light">{value}</div>
    <div className="text-[9px] text-frost-dim">{label}</div>
    {sub && <div className="text-[9px] text-ember-light">{sub}</div>}
  </div>
);

const Empty = ({ text }) => (
  <div className="text-center py-12 text-frost-dim text-sm">{text}</div>
);

const velLabel = (v) => {
  if (!v || v === 0) return 'No data';
  if (v >= 1.0) return 'Hot';
  if (v >= 0.5) return 'Warm';
  if (v >= 0.2) return 'Stable';
  return 'Cold';
};

export default CardDetailModal;
