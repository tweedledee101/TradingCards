import { Link } from 'react-router-dom';
import { useState } from 'react';
import { addToWatchlist, addToInventory } from '../api/client';
import ScoreExplainer from './ScoreExplainer';

const TrendingTable = ({ cards }) => {
  const [actionLoading, setActionLoading] = useState({});

  const getCategoryColor = (category) => {
    if (!category) return 'text-gray-500';
    if (category.includes('FIRE')) return 'text-red-600 font-bold';
    if (category.includes('TRENDING')) return 'text-orange-500 font-semibold';
    if (category.includes('WATCH')) return 'text-yellow-600';
    if (category.includes('STABLE')) return 'text-gray-500';
    return 'text-blue-500';
  };

  const getBuyZone = (avgPrice, velocity) => {
    let multiplier;
    if (velocity > 70) multiplier = 0.85;
    else if (velocity > 40) multiplier = 0.75;
    else multiplier = 0.65;
    return (avgPrice * multiplier).toFixed(2);
  };

  const getNetProfit = (avgPrice, velocity) => {
    const buyZone = parseFloat(getBuyZone(avgPrice, velocity));
    const ebayFees = avgPrice * 0.1315; // 13.15%
    const shipping = 5.00;
    const netProfit = avgPrice - buyZone - ebayFees - shipping;
    return netProfit;
  };

  const getRealROI = (avgPrice, velocity) => {
    const buyZone = parseFloat(getBuyZone(avgPrice, velocity));
    const netProfit = getNetProfit(avgPrice, velocity);
    return ((netProfit / buyZone) * 100).toFixed(1);
  };

  const getRowColor = (avgPrice, velocity) => {
    const buyZone = parseFloat(getBuyZone(avgPrice, velocity));
    if (avgPrice <= buyZone * 1.05) return 'bg-green-50'; // In buy zone
    if (avgPrice <= buyZone * 1.15) return 'bg-yellow-50'; // Close to buy zone
    return ''; // Overpriced
  };

  const handleAddToWatchlist = async (card) => {
    setActionLoading({ ...actionLoading, [`watch-${card.card_id}`]: true });
    try {
      const buyZone = getBuyZone(card.avg_price, card.velocity_score);
      await addToWatchlist({
        card_id: card.card_id,
        target_price: parseFloat(buyZone),
        alert_threshold: 5.0,
        notes: `Auto-added from trending (hotness: ${card.hotness_score.toFixed(1)})`
      });
      alert('Added to watchlist!');
    } catch (error) {
      alert('Failed to add to watchlist');
      console.error(error);
    } finally {
      setActionLoading({ ...actionLoading, [`watch-${card.card_id}`]: false });
    }
  };

  const handleMarkPurchased = async (card) => {
    const price = prompt(`Enter purchase price for ${card.player_name}:`);
    if (!price) return;
    
    setActionLoading({ ...actionLoading, [`buy-${card.card_id}`]: true });
    try {
      await addToInventory({
        card_id: card.card_id,
        purchase_price: parseFloat(price),
        purchase_date: new Date().toISOString().split('T')[0],
        quantity: 1,
        condition: 'raw',
        storage_location: 'home'
      });
      alert('Added to inventory!');
    } catch (error) {
      alert('Failed to add to inventory');
      console.error(error);
    } finally {
      setActionLoading({ ...actionLoading, [`buy-${card.card_id}`]: false });
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Card image">Image</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Card ranking by hotness score">Rank</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Player name and sport">Player</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Card year and set name">Year / Set</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Average sold price (last 7 days)">Avg Price</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Recommended buy price (velocity-adjusted)">Buy Zone</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Net profit after eBay fees (13%), shipping ($5)">Net Profit</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="ROI % after all fees and costs">ROI</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Average days from listing to sale">Days to Sell</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Number of sales (last 7 days)">Volume</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Price change velocity (higher = hotter)">Velocity</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase" title="Overall hotness score (0-100)">Hotness</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {cards.map((card, index) => {
            const buyZone = parseFloat(getBuyZone(card.avg_price, card.velocity_score));
            const isInBuyZone = card.avg_price <= buyZone * 1.05;
            return (
              <tr key={index} className={`hover:bg-gray-100 ${getRowColor(card.avg_price, card.velocity_score)}`}>
                <td className="px-4 py-4 whitespace-nowrap">
                  <img 
                    src={card.image_url || 'https://via.placeholder.com/80x112/1e40af/ffffff?text=No+Image'} 
                    alt={`${card.player_name} ${card.card_year}`}
                    className="w-20 h-28 object-cover rounded shadow"
                    onError={(e) => e.target.src = 'https://via.placeholder.com/80x112/1e40af/ffffff?text=No+Image'}
                  />
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {index + 1}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <Link to={`/card/${card.card_id || index + 1}`} className="text-blue-600 hover:underline">
                    <div className="text-sm font-medium text-gray-900">{card.player_name}</div>
                    <div className="text-xs text-gray-500">{card.sport}</div>
                    {card.card_number && (
                      <div className="text-xs font-semibold text-blue-600">#{card.card_number}</div>
                    )}
                  </Link>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                  <div className="font-medium">{card.card_year}</div>
                  <div className="text-xs text-gray-500">{card.card_set}</div>
                  {card.parallel && card.parallel !== 'Base' && (
                    <div className="text-xs font-semibold text-purple-600">{card.parallel}</div>
                  )}
                  {card.grade_company && card.grade_value && (
                    <div className="text-xs font-semibold text-green-600">{card.grade_company} {card.grade_value}</div>
                  )}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                  ${card.avg_price.toFixed(2)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold text-green-600">
                  ${getBuyZone(card.avg_price, card.velocity_score)}
                  {isInBuyZone && (
                    <div className="text-xs text-green-700 font-bold">✅ BUY</div>
                  )}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold">
                  <div className={getNetProfit(card.avg_price, card.velocity_score) > 10 ? 'text-green-600' : 'text-yellow-600'}>
                    ${getNetProfit(card.avg_price, card.velocity_score).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500">after fees</div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold text-blue-600">
                  {getRealROI(card.avg_price, card.velocity_score)}%
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                  {card.avg_days_to_sell ? (
                    <>
                      <div className="font-semibold">{Math.round(card.avg_days_to_sell)}d</div>
                      <div className="text-xs">
                        {card.avg_days_to_sell <= 7 ? '⚡ Fast' : card.avg_days_to_sell <= 14 ? '📊 Moderate' : '🐌 Slow'}
                      </div>
                    </>
                  ) : (
                    <div className="text-gray-400">~14d</div>
                  )}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                  {card.sales_count}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                  {card.velocity_score.toFixed(1)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="text-sm font-semibold">{card.hotness_score.toFixed(1)}</div>
                  {card.category && (
                    <div className={`text-xs ${getCategoryColor(card.category)}`}>
                      {card.category}
                    </div>
                  )}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm">
                  <div className="flex gap-1">
                    <ScoreExplainer card={card} />
                    <button
                      onClick={() => handleAddToWatchlist(card)}
                      disabled={actionLoading[`watch-${card.card_id}`]}
                      className="px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
                      title="Add to Watchlist"
                    >
                      👁️
                    </button>
                    <button
                      onClick={() => handleMarkPurchased(card)}
                      disabled={actionLoading[`buy-${card.card_id}`]}
                      className="px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50"
                      title="Mark as Purchased"
                    >
                      ✅
                    </button>
                    <Link
                      to={`/card/${card.card_id || index + 1}`}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                      title="View Details"
                    >
                      ℹ️
                    </Link>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default TrendingTable;
