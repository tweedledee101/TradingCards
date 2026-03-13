import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getCard } from '../api/client';
import PriceChart from '../components/PriceChart';
import ProfitCalculator from '../components/ProfitCalculator';

const CardDetail = () => {
  const { id } = useParams();
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [gradingData, setGradingData] = useState(null);
  const [benchmarkData, setBenchmarkData] = useState(null);

  useEffect(() => {
    const fetchCard = async () => {
      try {
        const data = await getCard(id);
        setCard(data);
        
        // Fetch grading data
        try {
          const gradingRes = await fetch(`http://localhost:8000/api/grading/${id}`);
          if (gradingRes.ok) {
            const gradingData = await gradingRes.json();
            setGradingData(gradingData);
          }
        } catch (err) {
          console.log('No grading data available');
        }
        
        // Fetch price benchmarks
        try {
          const benchmarkRes = await fetch(`http://localhost:8000/api/benchmarks/${id}`);
          if (benchmarkRes.ok) {
            const benchmarkData = await benchmarkRes.json();
            setBenchmarkData(benchmarkData);
          }
        } catch (err) {
          console.log('No benchmark data available');
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCard();
  }, [id]);

  if (loading) return <div className="flex justify-center items-center h-screen">Loading...</div>;
  if (!card) return <div className="flex justify-center items-center h-screen">Card not found</div>;

  const buyPrice = (card.current_trend.avg_price * 0.93).toFixed(2);
  const cardImageUrl = `https://via.placeholder.com/300x420/1e40af/ffffff?text=${encodeURIComponent(card.player_name + '\n' + card.card_year + ' ' + card.card_set)}`;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <Link to="/" className="text-blue-600 hover:underline mb-4 inline-block">
          ← Back to Trending
        </Link>

        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <div className="flex gap-6">
            <div className="flex-shrink-0">
              <img 
                src={cardImageUrl} 
                alt={`${card.player_name} ${card.card_year} ${card.card_set}`}
                className="w-64 h-auto rounded-lg shadow-lg"
              />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">
                {card.player_name}
              </h1>
              <div className="space-y-2 text-lg">
                <div><span className="font-semibold">Year:</span> {card.card_year}</div>
                <div><span className="font-semibold">Set:</span> {card.card_set}</div>
                {card.card_number && <div><span className="font-semibold">Card #:</span> {card.card_number}</div>}
                {card.parallel && <div><span className="font-semibold">Parallel:</span> <span className="text-purple-600 font-bold">{card.parallel}</span></div>}
                {card.grade_company && card.grade_value && (
                  <div><span className="font-semibold">Grade:</span> <span className="text-green-600 font-bold">{card.grade_company} {card.grade_value}</span></div>
                )}
                <div><span className="font-semibold">Sport:</span> {card.sport}</div>
                {card.is_rookie && <div className="inline-block bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">Rookie Card</div>}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-sm text-gray-600">Average Price</div>
            <div className="text-3xl font-bold">${card.current_trend.avg_price?.toFixed(2) || 'N/A'}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-sm text-gray-600">Hotness Score</div>
            <div className="text-3xl font-bold text-orange-600">{card.current_trend.hotness_score?.toFixed(1) || 'N/A'}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-sm text-gray-600">🎯 Buy Under</div>
            <div className="text-3xl font-bold text-green-600">${buyPrice}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <PriceChart sales={card.recent_sales} />
          <ProfitCalculator avgPrice={card.current_trend.avg_price || 0} />
        </div>

        {benchmarkData && (
          <div className="bg-white p-6 rounded-lg shadow mb-6">
            <h3 className="text-lg font-semibold mb-4">📈 Price Benchmarks</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {benchmarkData.benchmarks.map((b, i) => (
                <div key={i} className="border rounded-lg p-4">
                  <div className="font-semibold text-lg mb-2 capitalize">{b.source}</div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Current:</span>
                      <span className="font-bold">${b.current_price?.toFixed(2) || 'N/A'}</span>
                    </div>
                    {b.change_7d !== null && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">7d Change:</span>
                        <span className={b.change_7d > 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                          {b.change_7d > 0 ? '+' : ''}{b.change_7d.toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {b.change_30d !== null && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">30d Change:</span>
                        <span className={b.change_30d > 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                          {b.change_30d > 0 ? '+' : ''}{b.change_30d.toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {b.velocity_rating && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Velocity:</span>
                        <span className={`font-semibold ${
                          b.velocity_rating === 'Hot' ? 'text-red-600' :
                          b.velocity_rating === 'Warm' ? 'text-orange-600' :
                          b.velocity_rating === 'Cold' ? 'text-blue-600' : 'text-gray-600'
                        }`}>
                          {b.velocity_rating}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    {new Date(b.date_recorded).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">Recent Sales ({card.recent_sales.length})</h3>
            <div className="space-y-2">
              {card.recent_sales.map((sale, i) => (
                <div key={i} className="flex justify-between border-b pb-2">
                  <div>
                    <div className="font-semibold">${sale.price.toFixed(2)}</div>
                    <div className="text-sm text-gray-600">
                      {new Date(sale.date).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="text-sm text-gray-600">
                    {sale.graded && `${sale.grade_company} ${sale.grade_value}`}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {gradingData ? (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold mb-4">🏆 PSA Grading Population</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">PSA 10:</span>
                  <span className="font-bold text-green-600">
                    {gradingData.psa_10_count} ({(gradingData.psa_10_rate * 100).toFixed(1)}%)
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">PSA 9:</span>
                  <span className="font-semibold">{gradingData.psa_9_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">PSA 8:</span>
                  <span className="font-semibold">{gradingData.psa_8_count}</span>
                </div>
                <div className="border-t pt-3 mt-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700 font-semibold">Total Graded:</span>
                    <span className="font-bold text-blue-600">{gradingData.total_graded}</span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-2">
                  Last updated: {new Date(gradingData.date_recorded).toLocaleDateString()}
                </div>
                {gradingData.psa_10_rate > 0.25 && (
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
                    <div className="text-sm text-green-800 font-semibold">
                      ✅ High PSA 10 Rate - Good grading candidate!
                    </div>
                  </div>
                )}
                {gradingData.psa_10_rate < 0.15 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <div className="text-sm text-yellow-800 font-semibold">
                      ⚠️ Low PSA 10 Rate - Consider selling raw
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold mb-4">
                🛒 Where to Buy
              </h3>
              <div className="space-y-3">
                <div className="text-sm text-gray-600 mb-3">
                  Find raw (ungraded) cards near your buy zone: <span className="font-bold text-green-600">${buyPrice}</span>
                </div>
                
                {/* eBay - Specific search with exact card details */}
                <a
                  href={`https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(
                    card.player_name + ' ' + 
                    card.card_year + ' ' + 
                    card.card_set + 
                    (card.card_number ? ' #' + card.card_number : '') +
                    (card.parallel && card.parallel !== 'Base' ? ' ' + card.parallel : '') +
                    (card.grade_company && card.grade_value ? ' ' + card.grade_company + ' ' + card.grade_value : ' raw')
                  )}&_udlo=${Math.floor(parseFloat(buyPrice) * 0.8)}&_udhi=${Math.ceil(parseFloat(buyPrice) * 1.2)}&LH_BIN=1&_sop=15`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between bg-blue-600 text-white px-4 py-3 rounded hover:bg-blue-700 font-medium"
                >
                  <span>🔵 eBay - Exact Match</span>
                  <span className="text-sm bg-blue-700 px-2 py-1 rounded">${Math.floor(parseFloat(buyPrice) * 0.8)}-${Math.ceil(parseFloat(buyPrice) * 1.2)}</span>
                </a>
                
                {/* Facebook Marketplace */}
                <a
                  href={`https://www.facebook.com/marketplace/search?query=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set)}&maxPrice=${Math.ceil(parseFloat(buyPrice))}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between bg-blue-500 text-white px-4 py-3 rounded hover:bg-blue-600 font-medium"
                >
                  <span>📱 Facebook Marketplace</span>
                  <span className="text-sm bg-blue-600 px-2 py-1 rounded">Best deals</span>
                </a>
                
                {/* COMC */}
                <a
                  href={`https://www.comc.com/Cards,sh,=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set).replace(/%20/g, '+')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between bg-orange-600 text-white px-4 py-3 rounded hover:bg-orange-700 font-medium"
                >
                  <span>🏪 COMC - Bulk Discounts</span>
                  <span className="text-sm bg-orange-700 px-2 py-1 rounded">Wholesale</span>
                </a>
                
                {/* Facebook Marketplace */}
                <a
                  href={`https://www.facebook.com/marketplace/search?query=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set)}&maxPrice=${Math.ceil(parseFloat(buyPrice))}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between bg-blue-500 text-white px-4 py-3 rounded hover:bg-blue-600 font-medium"
                >
                  <span>📱 Facebook - Local Deals</span>
                  <span className="text-sm bg-blue-600 px-2 py-1 rounded">≤ ${Math.ceil(parseFloat(buyPrice))}</span>
                </a>
                
                {/* Mercari */}
                <a
                  href={`https://www.mercari.com/search/?keyword=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between bg-red-500 text-white px-4 py-3 rounded hover:bg-red-600 font-medium"
                >
                  <span>🛍️ Mercari - Marketplace</span>
                  <span className="text-sm bg-red-600 px-2 py-1 rounded">Varies</span>
                </a>
              </div>
              
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
                <div className="font-semibold text-yellow-800 mb-1">💡 Dealer Strategy:</div>
                <ul className="text-yellow-700 space-y-1 text-xs">
                  <li>• <strong>Facebook</strong>: Best margins (40-60%) - sellers don't comp properly</li>
                  <li>• <strong>COMC</strong>: Bulk discounts - buy 10+ cards at wholesale</li>
                  <li>• <strong>Whatnot</strong>: Snipe deals during live auctions</li>
                  <li>• <strong>Mercari</strong>: Check daily - fast turnover, motivated sellers</li>
                  <li>• <strong>eBay</strong>: Market rate baseline - sell here after buying cheaper elsewhere</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CardDetail;
