import { useState, useEffect, lazy, Suspense } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getCard, getGradingForCard, getPriceBenchmarksForCard } from '../api/client';

const PriceChart = lazy(() => import('../components/PriceChart'));

const CardDetail = () => {
  const { id } = useParams();
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [gradingData, setGradingData] = useState(null);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [buyPrice, setBuyPrice] = useState('');
  const [sellPrice, setSellPrice] = useState('');

  useEffect(() => {
    const fetchCard = async () => {
      try {
        const data = await getCard(id);
        setCard(data);
        const avg = data.current_trend?.avg_price || 0;
        setBuyPrice((avg * 0.93).toFixed(2));
        setSellPrice(avg.toFixed(2));

        try {
          const g = await getGradingForCard(id);
          setGradingData(g);
        } catch {
          /* no grading row */
        }

        try {
          const b = await getPriceBenchmarksForCard(id);
          setBenchmarkData(b);
        } catch {
          /* no benchmarks */
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchCard();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Loading card data...</div>
      </div>
    );
  }

  if (!card) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Card not found</div>
      </div>
    );
  }

  const avg = card.current_trend?.avg_price || 0;
  const hotness = card.current_trend?.hotness_score || 0;
  const velocity = card.current_trend?.velocity_score || 0;
  const volume = card.current_trend?.sales_count || card.recent_sales?.length || 0;

  // Profit calculator
  const buy = parseFloat(buyPrice) || 0;
  const sell = parseFloat(sellPrice) || 0;
  const fees = sell * 0.13;
  const netProfit = sell - buy - fees;
  const roi = buy > 0 ? ((netProfit / buy) * 100) : 0;

  const ebaySearch = `https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(
    card.player_name + ' ' + card.card_year + ' ' + card.card_set +
    (card.card_number ? ' #' + card.card_number : '') +
    (card.parallel && card.parallel !== 'Base' ? ' ' + card.parallel : '')
  )}&LH_BIN=1&_sop=15`;

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Back nav */}
      <Link to="/" className="text-sm text-frost-dim hover:text-frost-light transition-colors mb-6 inline-flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-ember/40 rounded">
        <span aria-hidden="true">&larr;</span> Back to Market
      </Link>

      {/* Header card */}
      <div className="card-surface p-5 mb-6">
        <div className="flex gap-5">
          {/* Image */}
          <div className="w-48 h-64 rounded-lg overflow-hidden bg-surface-raised shrink-0">
            {card.image_url ? (
              <img src={card.image_url} alt="" loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-frost-dim text-xs">No Image</div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-3">
              {card.player_name}
            </h1>
            <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
              <DetailRow label="Year" value={card.card_year} />
              <DetailRow label="Set" value={card.card_set} />
              {card.card_number && <DetailRow label="Card #" value={card.card_number} />}
              {card.parallel && <DetailRow label="Parallel" value={card.parallel} accent />}
              {card.grade_company && card.grade_value && (
                <DetailRow label="Grade" value={`${card.grade_company} ${card.grade_value}`} />
              )}
              <DetailRow label="Sport" value={card.sport} />
            </div>
            {card.is_rookie && (
              <span className="badge-ember text-xs mt-3 inline-block">RC</span>
            )}
          </div>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard label="Avg Price" value={`$${avg.toFixed(2)}`} />
        <MetricCard label="Hotness" value={hotness.toFixed(0)} color={hotness >= 70 ? 'ember' : hotness >= 40 ? 'amber' : 'dim'} />
        <MetricCard label="Velocity" value={`${velocity > 0 ? '+' : ''}${velocity.toFixed(1)}%`} color={velocity > 0 ? 'gain' : velocity < 0 ? 'loss' : 'dim'} />
        <MetricCard label="Volume" value={`${volume} sales`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Price chart */}
        <Suspense fallback={<div className="card-surface p-4 h-72 flex items-center justify-center text-frost-dim text-xs">Loading chart...</div>}>
          <PriceChart sales={card.recent_sales} />
        </Suspense>

        {/* Profit calculator */}
        <div className="card-surface p-4">
          <div className="text-label mb-3">Profit Calculator</div>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-frost-dim mb-1 block">Buy Price</label>
              <input
                type="number"
                value={buyPrice}
                onChange={e => setBuyPrice(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm bg-surface-raised border border-surface-border text-frost-light focus:outline-none focus:border-ember/40 font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-frost-dim mb-1 block">Sell Price</label>
              <input
                type="number"
                value={sellPrice}
                onChange={e => setSellPrice(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm bg-surface-raised border border-surface-border text-frost-light focus:outline-none focus:border-ember/40 font-mono"
              />
            </div>
            <div className="border-t border-surface-border pt-3 space-y-1.5 text-xs">
              <CalcRow label="Gross" value={`$${(sell - buy).toFixed(2)}`} />
              <CalcRow label="Fees (13%)" value={`-$${fees.toFixed(2)}`} dim />
              <div className="border-t border-surface-border pt-1.5">
                <CalcRow label="Net Profit" value={`${netProfit >= 0 ? '+' : ''}$${netProfit.toFixed(2)}`} gain={netProfit > 0} loss={netProfit < 0} />
                <CalcRow label="ROI" value={`${roi.toFixed(1)}%`} gain={roi > 0} loss={roi < 0} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Benchmarks */}
      {benchmarkData && benchmarkData.benchmarks?.length > 0 && (
        <div className="card-surface p-4 mb-6">
          <div className="text-label mb-3">Price Benchmarks</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {benchmarkData.benchmarks.map((b, i) => (
              <div key={i} className="bg-surface-raised rounded-lg p-3">
                <div className="text-sm font-medium text-frost-light mb-2 capitalize">{b.source}</div>
                <div className="space-y-1.5 text-xs">
                  <CalcRow label="Current" value={b.current_price ? `$${b.current_price.toFixed(2)}` : '--'} />
                  {b.change_7d != null && (
                    <CalcRow label="7d" value={`${b.change_7d > 0 ? '+' : ''}${b.change_7d.toFixed(1)}%`} gain={b.change_7d > 0} loss={b.change_7d < 0} />
                  )}
                  {b.change_30d != null && (
                    <CalcRow label="30d" value={`${b.change_30d > 0 ? '+' : ''}${b.change_30d.toFixed(1)}%`} gain={b.change_30d > 0} loss={b.change_30d < 0} />
                  )}
                  {b.velocity_rating && <CalcRow label="Velocity" value={b.velocity_rating} />}
                </div>
                <div className="text-[10px] text-frost-dim mt-2">{new Date(b.date_recorded).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Recent sales */}
        <div className="card-surface p-4">
          <div className="text-label mb-3">Recent Sales ({card.recent_sales?.length || 0})</div>
          <div className="space-y-1.5 max-h-80 overflow-y-auto">
            {(card.recent_sales || []).map((sale, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-surface-raised rounded-lg px-3 py-2">
                <div>
                  <span className="font-mono font-semibold text-frost-light">${sale.price.toFixed(2)}</span>
                  {sale.graded && (
                    <span className="text-frost-dim ml-2">{sale.grade_company} {sale.grade_value}</span>
                  )}
                </div>
                <span className="text-frost-dim">{new Date(sale.date).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Grading or buy links */}
        {gradingData ? (
          <div className="card-surface p-4">
            <div className="text-label mb-3">PSA Grading Population</div>
            <div className="space-y-2 text-sm">
              <CalcRow label="PSA 10" value={`${gradingData.psa_10_count} (${(gradingData.psa_10_rate * 100).toFixed(1)}%)`} />
              <CalcRow label="PSA 9" value={String(gradingData.psa_9_count)} />
              <CalcRow label="PSA 8" value={String(gradingData.psa_8_count)} />
              <div className="border-t border-surface-border pt-2">
                <CalcRow label="Total Graded" value={String(gradingData.total_graded)} accent />
              </div>
              <div className="text-[10px] text-frost-dim">Updated {new Date(gradingData.date_recorded).toLocaleDateString()}</div>
              {gradingData.psa_10_rate > 0.25 && (
                <div className="bg-gain/10 border border-gain/20 rounded-lg px-3 py-2 text-xs text-gain">
                  High PSA 10 rate — good grading candidate
                </div>
              )}
              {gradingData.psa_10_rate < 0.15 && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 text-xs text-amber-400">
                  Low PSA 10 rate — consider selling raw
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="card-surface p-4">
            <div className="text-label mb-3">Search Listings</div>
            <div className="space-y-2">
              <ExternalLink href={ebaySearch} label="eBay — Buy It Now" sublabel="Sorted by price" />
              <ExternalLink
                href={`https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set + (card.card_number ? ' #' + card.card_number : ''))}&LH_Auction=1&_sop=1`}
                label="eBay — Auctions"
                sublabel="Ending soonest"
              />
              <ExternalLink
                href={`https://www.comc.com/Cards,sh,=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set).replace(/%20/g, '+')}`}
                label="COMC"
                sublabel="Bulk pricing"
              />
              <ExternalLink
                href={`https://www.mercari.com/search/?keyword=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set)}`}
                label="Mercari"
                sublabel="Marketplace"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


const DetailRow = ({ label, value, accent }) => (
  <div className="flex items-baseline gap-2">
    <span className="text-xs text-frost-dim w-16 shrink-0">{label}</span>
    <span className={`text-sm font-medium ${accent ? 'text-ember-light' : 'text-frost-light'}`}>{value}</span>
  </div>
);

const MetricCard = ({ label, value, color }) => {
  const colorClass = color === 'ember' ? 'text-ember-light' : color === 'amber' ? 'text-amber-400' : color === 'gain' ? 'text-gain' : color === 'loss' ? 'text-loss' : 'text-frost-light';
  return (
    <div className="card-surface p-3 text-center">
      <div className="text-label mb-1">{label}</div>
      <div className={`text-lg font-bold font-mono ${colorClass}`}>{value}</div>
    </div>
  );
};

const CalcRow = ({ label, value, gain, loss, dim, accent }) => (
  <div className="flex justify-between">
    <span className="text-frost-dim">{label}</span>
    <span className={`font-mono font-semibold ${gain ? 'text-gain' : loss ? 'text-loss' : accent ? 'text-ember-light' : dim ? 'text-frost-dim' : 'text-frost-light'}`}>
      {value}
    </span>
  </div>
);

const ExternalLink = ({ href, label, sublabel }) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="flex items-center justify-between bg-surface-raised border border-surface-border rounded-lg px-4 py-3 hover:border-ember/30 hover:bg-surface-hover transition-colors"
  >
    <span className="text-sm font-medium text-frost-light">{label}</span>
    <span className="text-xs text-frost-dim">{sublabel}</span>
  </a>
);


export default CardDetail;
