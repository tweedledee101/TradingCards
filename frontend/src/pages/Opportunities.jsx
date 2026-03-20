import { useState, useEffect } from 'react';
import { getOpportunities, getAuctions } from '../api/client';

const Opportunities = () => {
  const [auctions, setAuctions] = useState([]);
  const [binDeals, setBinDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scannedAt, setScannedAt] = useState(null);
  const [expandedAuction, setExpandedAuction] = useState(null);
  const [expandedBin, setExpandedBin] = useState(null);
  const [expandedReview, setExpandedReview] = useState(null);
  const [filters, setFilters] = useState({ maxBid: '', minProfit: '', minRoi: '' });

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [auctionData, binData] = await Promise.all([
        getAuctions().catch(() => ({ auctions: [] })),
        getOpportunities().catch(() => ({ opportunities: [] })),
      ]);
      setAuctions(auctionData.auctions || []);
      setBinDeals(binData.opportunities || []);
      setScannedAt(binData.scanned_at || null);
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const clean = auctions.filter(a => !a.flagged);
  const flaggedAuctions = auctions.filter(a => a.flagged);

  const filteredAuctions = clean.filter(a => {
    if (filters.maxBid && a.current_bid > Number(filters.maxBid)) return false;
    if (filters.minProfit && a.net_profit < Number(filters.minProfit)) return false;
    if (filters.minRoi && a.roi < Number(filters.minRoi)) return false;
    return true;
  });

  const cleanBin = binDeals.filter(opp => !opp.flagged);
  const flaggedBin = binDeals.filter(opp => opp.flagged);

  const filteredBin = cleanBin.filter(opp => {
    if (filters.minRoi && (opp.arbitrage?.roi || 0) < Number(filters.minRoi)) return false;
    if (filters.minProfit && (opp.arbitrage?.net_profit || 0) < Number(filters.minProfit)) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Scanning for opportunities...</div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Opportunities</h1>
        <p className="text-sm text-frost-dim">
          BIN deals below SCP market rates{scannedAt && ` -- scanned ${new Date(scannedAt).toLocaleString()}`}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <input type="number" placeholder="Max Bid $" value={filters.maxBid}
          onChange={e => setFilters({ ...filters, maxBid: e.target.value })}
          className="w-24 px-2 py-1.5 rounded-lg text-xs bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40" />
        <input type="number" placeholder="Min Profit $" value={filters.minProfit}
          onChange={e => setFilters({ ...filters, minProfit: e.target.value })}
          className="w-28 px-2 py-1.5 rounded-lg text-xs bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40" />
        <input type="number" placeholder="Min ROI%" value={filters.minRoi}
          onChange={e => setFilters({ ...filters, minRoi: e.target.value })}
          className="w-24 px-2 py-1.5 rounded-lg text-xs bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40" />
        <button onClick={fetchAll}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-ember/20 text-ember-light border border-ember/20 hover:bg-ember/30 transition-colors">
          Refresh
        </button>
        <div className="flex-1" />
        <span className="text-xs text-frost-dim">
          {filteredBin.length} BIN{filteredAuctions.length > 0 ? ` | ${filteredAuctions.length} auction${filteredAuctions.length !== 1 ? 's' : ''}` : ''}{flaggedBin.length > 0 ? ` | ${flaggedBin.length} flagged` : ''}
        </span>
      </div>

      {error && <div className="card-surface p-4 mb-6 text-loss text-sm">{error}</div>}

      {/* LIVE AUCTIONS */}
      <SectionHeader title="Live Auctions" subtitle="Ending soon - bid below SCP market rate" count={filteredAuctions.length} />

      {filteredAuctions.length === 0 ? (
        <EmptyState message="No profitable auctions found. Run the auction scanner to refresh." />
      ) : (
        <div className="space-y-2 mb-10">
          {filteredAuctions.map((a, i) => (
            <AuctionCard key={a.ebay_item_id || i} auction={a} rank={i + 1}
              isExpanded={expandedAuction === (a.ebay_item_id || i)}
              onToggle={() => setExpandedAuction(expandedAuction === (a.ebay_item_id || i) ? null : (a.ebay_item_id || i))} />
          ))}
        </div>
      )}

      {/* BIN DEALS */}
      {filteredBin.length > 0 && (
        <>
          <SectionHeader title="Buy It Now" subtitle="BIN listings below SCP market rate" count={filteredBin.length} />
          <div className="space-y-2 mb-10">
            {filteredBin.map((opp, i) => (
              <BinCard key={opp.card_id || i} opp={opp} rank={i + 1}
                isExpanded={expandedBin === (opp.card_id || i)}
                onToggle={() => setExpandedBin(expandedBin === (opp.card_id || i) ? null : (opp.card_id || i))} />
            ))}
          </div>
        </>
      )}

      {/* NEEDS REVIEW */}
      {(flaggedAuctions.length > 0 || flaggedBin.length > 0) && (
        <>
          <div className="border-t border-surface-border mt-10 pt-6 mb-4">
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-lg font-display font-semibold text-amber-400">Needs Review</h2>
              <span className="text-xs text-frost-dim bg-surface-card px-2 py-0.5 rounded-md">{flaggedAuctions.length + flaggedBin.length}</span>
            </div>
            <p className="text-xs text-frost-dim">
              Price gap seems too large. May be a mismatch -- review before buying.
            </p>
          </div>
          <div className="space-y-2 opacity-75">
            {flaggedAuctions.map((a, i) => (
              <AuctionCard key={`review-${a.ebay_item_id || i}`} auction={a} rank={i + 1} isFlagged
                isExpanded={expandedReview === (a.ebay_item_id || i)}
                onToggle={() => setExpandedReview(expandedReview === (a.ebay_item_id || i) ? null : (a.ebay_item_id || i))} />
            ))}
            {flaggedBin.map((opp, i) => (
              <BinCard key={`review-bin-${i}`} opp={opp} rank={i + 1}
                isExpanded={expandedReview === `flagged-bin-${i}`}
                onToggle={() => setExpandedReview(expandedReview === `flagged-bin-${i}` ? null : `flagged-bin-${i}`)} />
            ))}
          </div>
        </>
      )}
    </div>
  );
};


const SectionHeader = ({ title, subtitle, count }) => (
  <div className="flex items-center gap-3 mb-3">
    <h2 className="text-lg font-display font-semibold text-frost-light">{title}</h2>
    <span className="text-xs text-frost-dim bg-surface-card px-2 py-0.5 rounded-md">{count}</span>
    <span className="text-xs text-frost-dim">{subtitle}</span>
  </div>
);

const EmptyState = ({ message }) => (
  <div className="card-surface p-8 text-center mb-10">
    <div className="text-xs text-frost-dim">{message}</div>
  </div>
);


const AuctionCard = ({ auction: a, rank, isExpanded, onToggle, isFlagged }) => {
  const hoursLeft = a.hours_left || 0;
  const urgency = hoursLeft <= 1 ? 'text-loss' : hoursLeft <= 6 ? 'text-amber-400' : 'text-frost-dim';
  const timeLabel = hoursLeft < 1 ? `${Math.round(hoursLeft * 60)}m` : `${hoursLeft.toFixed(1)}h`;

  return (
    <div className={`card-surface overflow-hidden ${isFlagged ? 'border-amber-500/30' : ''}`}>
      <div role="button" tabIndex={0} aria-expanded={isExpanded}
        className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-surface-hover transition-colors"
        onClick={onToggle}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}>

        {/* Time left */}
        <div className={`w-12 text-center shrink-0 ${urgency}`}>
          <div className="text-sm font-bold font-mono">{timeLabel}</div>
          <div className="text-[9px] uppercase tracking-wider">left</div>
        </div>

        {/* Image */}
        <div className="w-10 h-14 rounded-md overflow-hidden bg-surface-raised shrink-0">
          {a.image_url ? (
            <img src={a.image_url} alt="" loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">--</div>
          )}
        </div>

        {/* Card info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-frost-light truncate">{a.player_name}</span>
            {a.parallel && a.parallel !== 'Base' && <span className="badge-neutral text-[10px]">{a.parallel}</span>}
            {a.is_rookie && <span className="badge-ember text-[10px]">RC</span>}
            {a.grade_company && <span className="badge-neutral text-[10px]">{a.grade_company} {a.grade_value}</span>}
          </div>
          <div className="text-xs text-frost-dim truncate">
            {a.card_year} {a.card_set}{a.card_number ? ` #${a.card_number}` : ''}
          </div>
        </div>

        {/* Bids */}
        <div className="text-center shrink-0 w-16">
          <div className="text-sm font-mono font-semibold text-amber-400">${a.current_bid?.toFixed(2)}</div>
          <div className="text-[9px] text-frost-dim">{a.bid_count} bid{a.bid_count !== 1 ? 's' : ''}</div>
        </div>

        {/* SCP */}
        <div className="text-center shrink-0 w-16">
          <div className="text-sm font-mono font-semibold text-frost-light">${a.scp_sell_price?.toFixed(2)}</div>
          <div className="text-[9px] text-frost-dim">SCP {a.scp_price_tier}</div>
        </div>

        {/* Profit */}
        <div className="text-right shrink-0 w-20">
          <div className="text-sm font-bold font-mono text-gain">+${a.net_profit?.toFixed(2)}</div>
          <div className="text-[10px] font-mono text-gain/70">{a.roi?.toFixed(0)}% ROI</div>
        </div>

        <div className={`text-frost-dim text-xs transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`}>▼</div>
      </div>

      {/* Expanded */}
      {isExpanded && (
        <div className="border-t border-surface-border px-4 py-4">
          {isFlagged && a.flag_reason && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 mb-3 text-xs text-amber-400">
              {a.flag_reason}
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-xs">
            <Stat label="Current Bid" value={`$${a.current_bid?.toFixed(2)}`} />
            <Stat label="Shipping" value={a.shipping > 0 ? `$${a.shipping.toFixed(2)}` : 'Free'} />
            <Stat label="Total Cost" value={`$${a.total_cost?.toFixed(2)}`} />
            <Stat label="Fees (13%)" value={`$${a.fees?.toFixed(2)}`} />
            <Stat label="SCP Ungraded" value={a.scp_ungraded ? `$${a.scp_ungraded.toFixed(2)}` : '--'} />
            <Stat label="SCP Grade 9" value={a.scp_grade_9 ? `$${a.scp_grade_9.toFixed(2)}` : '--'} />
            <Stat label="SCP PSA 10" value={a.scp_psa_10 ? `$${a.scp_psa_10.toFixed(2)}` : '--'} />
            <Stat label="Condition" value={a.condition || 'Unknown'} />
          </div>
          <div className="text-xs text-frost-dim mb-3 truncate">{a.title}</div>
          <div className="flex gap-2">
            <a href={a.ebay_url} target="_blank" rel="noopener noreferrer"
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/20 hover:bg-amber-500/30 transition-colors">
              View Auction
            </a>
            {a.scp_url && (
              <a href={a.scp_url} target="_blank" rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
                Verify SCP
              </a>
            )}
            <button onClick={() => {
              const term = `${a.card_year} ${a.card_set} ${a.player_name}${a.parallel && a.parallel !== 'Base' ? ` ${a.parallel}` : ''}${a.card_number ? ` #${a.card_number}` : ''}`;
              navigator.clipboard.writeText(term);
            }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
              Copy Search
            </button>
          </div>
        </div>
      )}
    </div>
  );
};


const BinCard = ({ opp, rank, isExpanded, onToggle }) => {
  const arb = opp.arbitrage || {};
  const buyListings = opp.buy_listings || [];

  return (
    <div className="card-surface overflow-hidden">
      <div role="button" tabIndex={0} aria-expanded={isExpanded}
        className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-surface-hover transition-colors"
        onClick={onToggle}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}>

        <div className="w-12 text-center shrink-0">
          <div className="text-xs font-medium text-gain bg-gain/10 rounded-md px-1.5 py-0.5">BIN</div>
        </div>

        <div className="w-10 h-14 rounded-md overflow-hidden bg-surface-raised shrink-0">
          {opp.image_url ? (
            <img src={opp.image_url} alt="" loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">--</div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-frost-light truncate">{opp.player_name}</span>
            {opp.parallel && opp.parallel !== 'Base' && <span className="badge-neutral text-[10px]">{opp.parallel}</span>}
            {opp.is_rookie && <span className="badge-ember text-[10px]">RC</span>}
          </div>
          <div className="text-xs text-frost-dim truncate">
            {opp.card_year} {opp.card_set}{opp.card_number ? ` #${opp.card_number}` : ''}
          </div>
        </div>

        <div className="text-center shrink-0 w-16">
          <div className="text-sm font-mono font-semibold text-frost-light">${arb.buy_price?.toFixed(2)}</div>
          <div className="text-[9px] text-frost-dim">{buyListings.length} listing{buyListings.length !== 1 ? 's' : ''}</div>
        </div>

        <div className="text-center shrink-0 w-16">
          <div className="text-sm font-mono font-semibold text-frost-light">${arb.sell_price?.toFixed(2)}</div>
          <div className="text-[9px] text-frost-dim">SCP</div>
        </div>

        <div className="text-right shrink-0 w-20">
          <div className="text-sm font-bold font-mono text-gain">+${arb.net_profit?.toFixed(2)}</div>
          <div className="text-[10px] font-mono text-gain/70">{arb.roi?.toFixed(0)}% ROI</div>
        </div>

        <div className={`text-frost-dim text-xs transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`}>▼</div>
      </div>

      {isExpanded && (
        <div className="border-t border-surface-border px-4 py-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-xs">
            <Stat label="Buy Price" value={`$${arb.buy_price?.toFixed(2)}`} />
            <Stat label="SCP Rate" value={`$${arb.sell_price?.toFixed(2)}`} />
            <Stat label="Fees (13%)" value={`$${arb.fees?.toFixed(2)}`} />
            <Stat label="Net Profit" value={`+$${arb.net_profit?.toFixed(2)}`} gain />
            <Stat label="SCP Ungraded" value={arb.scp_ungraded ? `$${arb.scp_ungraded.toFixed(2)}` : '--'} />
            <Stat label="SCP Grade 9" value={arb.scp_grade_9 ? `$${arb.scp_grade_9.toFixed(2)}` : '--'} />
            <Stat label="SCP PSA 10" value={arb.scp_psa_10 ? `$${arb.scp_psa_10.toFixed(2)}` : '--'} />
            <Stat label="ROI" value={`${arb.roi?.toFixed(0)}%`} gain />
          </div>
          {buyListings.length > 0 && (
            <div className="space-y-1.5">
              {buyListings.slice(0, 5).map((l, i) => (
                <div key={i} className="flex items-center gap-3 text-xs bg-surface-raised rounded-lg px-3 py-2">
                  <a href={l.url} target="_blank" rel="noopener noreferrer"
                    className="flex-1 min-w-0 text-frost-light hover:text-ember-light transition-colors truncate">
                    {l.title || `Listing ${i + 1}`}
                  </a>
                  <span className="font-mono font-semibold text-frost-light shrink-0">${l.price.toFixed(2)}</span>
                  <span className="font-mono font-semibold text-gain shrink-0">+${l.net_profit.toFixed(2)}</span>
                  <a href={l.url} target="_blank" rel="noopener noreferrer"
                    className="px-3 py-1 rounded-md text-[10px] font-semibold bg-gain/20 text-gain border border-gain/20 hover:bg-gain/30 transition-colors shrink-0">
                    Buy
                  </a>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2 mt-3">
            {opp.scp_url && (
              <a href={opp.scp_url} target="_blank" rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
                Verify on SCP
              </a>
            )}
            <button onClick={() => {
              const term = `${opp.card_year} ${opp.card_set} ${opp.player_name}${opp.parallel && opp.parallel !== 'Base' ? ` ${opp.parallel}` : ''}${opp.card_number ? ` #${opp.card_number}` : ''}`;
              navigator.clipboard.writeText(term);
            }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
              Copy Search
            </button>
          </div>
        </div>
      )}
    </div>
  );
};


const Stat = ({ label, value, gain }) => (
  <div className="bg-surface-card rounded-lg px-3 py-2">
    <div className="text-[10px] text-frost-dim mb-0.5">{label}</div>
    <div className={`text-sm font-mono font-semibold ${gain ? 'text-gain' : 'text-frost-light'}`}>{value}</div>
  </div>
);


export default Opportunities;
