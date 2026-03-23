import { useState, useEffect } from 'react';
import { getOpportunities, getAuctions, getScheduledBids, cancelScheduledBid } from '../api/client';
import CardDetailModal from '../components/CardDetailModal';

const Opportunities = () => {
  const [auctions, setAuctions] = useState([]);
  const [binDeals, setBinDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scannedAt, setScannedAt] = useState(null);
  const [expandedAuction, setExpandedAuction] = useState(null);
  const [expandedBin, setExpandedBin] = useState(null);
  const [expandedReview, setExpandedReview] = useState(null);
  const [selectedCard, setSelectedCard] = useState(null);
  const [filters, setFilters] = useState({ maxBid: '', minProfit: '', minRoi: '' });
  const [myBids, setMyBids] = useState([]);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [auctionData, binData, bidsData] = await Promise.all([
        getAuctions().catch(() => ({ auctions: [] })),
        getOpportunities().catch(() => ({ opportunities: [] })),
        getScheduledBids().catch(() => ({ bids: [] })),
      ]);
      setAuctions(auctionData.auctions || []);
      setBinDeals(binData.opportunities || []);
      setScannedAt(binData.scanned_at || null);
      setMyBids(bidsData.bids || []);
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelBid = async (id) => {
    try {
      await cancelScheduledBid(id);
      setMyBids(prev => prev.filter(b => b.id !== id));
    } catch (err) { /* ignore */ }
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

      {/* MY BIDS STRIP */}
      {myBids.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-lg font-display font-semibold text-blue-400">My Bids</h2>
            <span className="text-xs text-frost-dim bg-surface-card px-2 py-0.5 rounded-md">{myBids.length}</span>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {myBids.map(bid => (
              <MyBidCard key={bid.id} bid={bid} onCancel={() => handleCancelBid(bid.id)} />
            ))}
          </div>
        </div>
      )}

      {/* LIVE AUCTIONS */}
      <SectionHeader title="Live Auctions" subtitle="Ending soon - bid below SCP market rate" count={filteredAuctions.length} />

      {filteredAuctions.length === 0 ? (
        <EmptyState message="No profitable auctions found. Run the auction scanner to refresh." />
      ) : (
        <div className="space-y-2 mb-10">
          {filteredAuctions.map((a, i) => (
            <AuctionCard key={a.ebay_item_id || i} auction={a} rank={i + 1}
              isExpanded={expandedAuction === (a.ebay_item_id || i)}
              onToggle={() => setExpandedAuction(expandedAuction === (a.ebay_item_id || i) ? null : (a.ebay_item_id || i))}
              onDrillIn={() => setSelectedCard({ data: a, type: 'auction' })} />
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
                onToggle={() => setExpandedBin(expandedBin === (opp.card_id || i) ? null : (opp.card_id || i))}
                onDrillIn={() => setSelectedCard({ data: opp, type: 'bin' })} />
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
                onToggle={() => setExpandedReview(expandedReview === (a.ebay_item_id || i) ? null : (a.ebay_item_id || i))}
                onDrillIn={() => setSelectedCard({ data: a, type: 'auction' })} />
            ))}
            {flaggedBin.map((opp, i) => (
              <BinCard key={`review-bin-${i}`} opp={opp} rank={i + 1}
                isExpanded={expandedReview === `flagged-bin-${i}`}
                onToggle={() => setExpandedReview(expandedReview === `flagged-bin-${i}` ? null : `flagged-bin-${i}`)}
                onDrillIn={() => setSelectedCard({ data: opp, type: 'bin' })} />
            ))}
          </div>
        </>
      )}

      {/* Drill-in Modal */}
      {selectedCard && (
        <CardDetailModal
          opportunity={selectedCard.data}
          type={selectedCard.type}
          onClose={() => setSelectedCard(null)}
        />
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


const AuctionCard = ({ auction: a, rank, isExpanded, onToggle, onDrillIn, isFlagged }) => {
  return (
    <div className={`card-surface overflow-hidden ${isFlagged ? 'border-amber-500/30' : ''}`}>
      <div role="button" tabIndex={0} aria-expanded={isExpanded}
        className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-surface-hover transition-colors"
        onClick={onToggle}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}>

        {/* Time left */}
        <CountdownTimer endTime={a.end_time} />

        {/* Image */}
        <div className="w-10 h-14 rounded-md overflow-hidden bg-surface-raised shrink-0 cursor-pointer" onClick={e => { e.stopPropagation(); onDrillIn(); }}>
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
            <ConfidenceBadge source={a.price_source} />
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
          {a.qa_flags && a.qa_flags.length > 0 && (
            <div className="space-y-1 mb-3">
              {a.qa_flags.map((f, i) => (
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
            <button onClick={onDrillIn}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
              Full Details
            </button>
          </div>
        </div>
      )}
    </div>
  );
};


const BinCard = ({ opp, rank, isExpanded, onToggle, onDrillIn }) => {
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

        <div className="w-10 h-14 rounded-md overflow-hidden bg-surface-raised shrink-0 cursor-pointer" onClick={e => { e.stopPropagation(); onDrillIn(); }}>
          {opp.image_url ? (
            <img src={opp.image_url} alt="" loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">--</div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-frost-light truncate">{opp.player_name}</span>
            <ConfidenceBadge source={opp.price_source} />
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
            <button onClick={onDrillIn}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
              Full Details
            </button>
          </div>
          {opp.qa_flags && opp.qa_flags.length > 0 && (
            <div className="space-y-1 mt-3">
              {opp.qa_flags.map((f, i) => (
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
    </div>
  );
};


const CountdownTimer = ({ endTime }) => {
  const [remaining, setRemaining] = useState(() => calcRemaining(endTime));

  useEffect(() => {
    if (!endTime) return;
    const id = setInterval(() => setRemaining(calcRemaining(endTime)), 1000);
    return () => clearInterval(id);
  }, [endTime]);

  if (!endTime || remaining <= 0) {
    return (
      <div className="w-32 text-center shrink-0">
        <div className="text-[10px] font-bold uppercase tracking-wider bg-surface-raised rounded px-1.5 py-1 text-frost-dim">Ended</div>
      </div>
    );
  }

  const hours = Math.floor(remaining / 3600);
  const mins = Math.floor((remaining % 3600) / 60);
  const secs = remaining % 60;
  const urgency = hours < 1 ? 'text-loss' : hours < 6 ? 'text-amber-400' : 'text-frost-dim';

  let display, sub;
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    const remHours = hours % 24;
    display = `${days}d ${remHours}h ${mins.toString().padStart(2, '0')}m ${secs.toString().padStart(2, '0')}s`;
    sub = 'left';
  } else if (hours >= 1) {
    display = `${hours}h ${mins.toString().padStart(2, '0')}m ${secs.toString().padStart(2, '0')}s`;
    sub = 'left';
  } else {
    display = `${mins}:${secs.toString().padStart(2, '0')}`;
    sub = 'left';
  }

  return (
    <div className={`w-32 text-center shrink-0 ${urgency}`}>
      <div className="text-xs font-bold font-mono">{display}</div>
      <div className="text-[9px] uppercase tracking-wider">{sub}</div>
    </div>
  );
};

const calcRemaining = (endTime) => {
  if (!endTime) return 0;
  const end = new Date(endTime).getTime();
  return Math.max(0, Math.floor((end - Date.now()) / 1000));
};


const ConfidenceBadge = ({ source }) => {
  if (!source || source === 'scp') {
    return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gain/15 text-gain border border-gain/20">SCP</span>;
  }
  if (source === 'sold_comps') {
    return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/20">Sold Comps</span>;
  }
  if (source === 'ebay_comps') {
    return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20">Market Comps</span>;
  }
  return null;
};


const Stat = ({ label, value, gain }) => (
  <div className="bg-surface-card rounded-lg px-3 py-2">
    <div className="text-[10px] text-frost-dim mb-0.5">{label}</div>
    <div className={`text-sm font-mono font-semibold ${gain ? 'text-gain' : 'text-frost-light'}`}>{value}</div>
  </div>
);


const MyBidCard = ({ bid, onCancel }) => {
  const [remaining, setRemaining] = useState(() => calcRemaining(bid.end_time));

  useEffect(() => {
    if (!bid.end_time) return;
    const id = setInterval(() => setRemaining(calcRemaining(bid.end_time)), 1000);
    return () => clearInterval(id);
  }, [bid.end_time]);

  const hours = Math.floor(remaining / 3600);
  const mins = Math.floor((remaining % 3600) / 60);
  const secs = remaining % 60;
  const pad = (n) => n.toString().padStart(2, '0');
  const ended = remaining <= 0;
  const approaching = !ended && remaining <= bid.snipe_seconds * 2;
  const urgent = !ended && remaining <= 3600;

  let timeDisplay;
  if (ended) timeDisplay = 'Ended';
  else if (hours >= 24) timeDisplay = `${Math.floor(hours/24)}d ${hours%24}h ${pad(mins)}m ${pad(secs)}s`;
  else if (hours >= 1) timeDisplay = `${hours}h ${pad(mins)}m ${pad(secs)}s`;
  else timeDisplay = `${mins}:${pad(secs)}`;

  return (
    <div className={`card-surface min-w-[260px] max-w-[300px] shrink-0 p-3 ${
      approaching ? 'border-loss/50 animate-pulse' : urgent ? 'border-amber-500/30' : ''
    }`}>
      <div className="flex items-start gap-2 mb-2">
        {bid.image_url && (
          <div className="w-8 h-11 rounded overflow-hidden bg-surface-raised shrink-0">
            <img src={bid.image_url} alt="" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-frost-light truncate">{bid.player_name}</div>
          <div className="text-[10px] text-frost-dim truncate">
            {bid.card_year} {bid.card_set}{bid.card_number ? ` #${bid.card_number}` : ''}
            {bid.parallel ? ` - ${bid.parallel}` : ''}
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mb-2">
        <div className={`text-xs font-mono font-bold ${
          ended ? 'text-frost-dim' : approaching ? 'text-loss' : urgent ? 'text-amber-400' : 'text-frost-light'
        }`}>
          {timeDisplay}
        </div>
        <div className="text-xs font-mono font-semibold text-blue-400">
          Max: ${bid.max_bid?.toFixed(2)}
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[9px] text-frost-dim">Snipe {bid.snipe_seconds}s before end</span>
        <div className="flex gap-1.5">
          {bid.ebay_url && (
            <a href={bid.ebay_url} target="_blank" rel="noopener noreferrer"
              className="px-2 py-0.5 rounded text-[9px] font-medium bg-surface-raised text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
              View
            </a>
          )}
          {!ended && (
            <button onClick={onCancel}
              className="px-2 py-0.5 rounded text-[9px] font-medium bg-loss/10 text-loss border border-loss/20 hover:bg-loss/20 transition-colors">
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
};


export default Opportunities;
