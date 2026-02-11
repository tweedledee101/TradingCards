import { Link } from 'react-router-dom';

const TrendingTable = ({ cards }) => {
  const getCategoryColor = (category) => {
    if (category.includes('FIRE')) return 'text-red-600 font-bold';
    if (category.includes('TRENDING')) return 'text-orange-500 font-semibold';
    if (category.includes('WATCH')) return 'text-yellow-600';
    if (category.includes('STABLE')) return 'text-gray-500';
    return 'text-blue-500';
  };

  const getBuyPrice = (avgPrice) => {
    return (avgPrice * 0.93).toFixed(2); // Buy 7% below avg
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Rank</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Player</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Card</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Avg Price</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Sales (7d)</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Velocity</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Hotness</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Buy Under</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {cards.map((card, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {index + 1}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Link to={`/card/${card.id || index + 1}`} className="text-blue-600 hover:underline">
                  <div className="text-sm font-medium text-gray-900">{card.player_name}</div>
                  {card.is_rookie && <span className="text-xs text-green-600">🏆 ROOKIE</span>}
                </Link>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {card.card_year} {card.card_set}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                ${card.avg_price.toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {card.sales_count}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {card.velocity_score.toFixed(1)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-semibold">{card.hotness_score.toFixed(1)}</div>
                <div className={`text-xs ${getCategoryColor(card.category)}`}>
                  {card.category}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-green-600">
                ${getBuyPrice(card.avg_price)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TrendingTable;
