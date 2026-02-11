import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getWatchlist } from '../api/client';

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWatchlist();
  }, []);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const data = await getWatchlist();
      setWatchlist(data.watchlist);
    } catch (error) {
      console.error('Failed to load watchlist:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Watchlist</h1>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Card</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Price</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current Price</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Difference</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hotness</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Alert</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {watchlist.map((item) => {
              const diff = item.current_price && item.target_price 
                ? item.current_price - item.target_price 
                : null;
              const diffPct = diff && item.target_price 
                ? ((diff / item.target_price) * 100).toFixed(1) 
                : null;

              return (
                <tr key={item.id} className={`hover:bg-gray-50 ${item.alert ? 'bg-yellow-50' : ''}`}>
                  <td className="px-6 py-4">
                    <Link to={`/card/${item.card.id}`} className="text-blue-600 hover:underline">
                      <div className="font-medium">{item.card.player_name}</div>
                      <div className="text-sm text-gray-500">
                        {item.card.card_year} {item.card.card_set}
                      </div>
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    {item.target_price ? `$${item.target_price}` : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {item.current_price ? `$${item.current_price}` : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {diff !== null ? (
                      <div>
                        <span className={diff >= 0 ? 'text-red-600' : 'text-green-600'}>
                          ${Math.abs(diff).toFixed(2)}
                        </span>
                        <span className="text-sm text-gray-500 ml-1">
                          ({diffPct}%)
                        </span>
                      </div>
                    ) : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {item.trend?.hotness_score ? (
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-sm">
                        {item.trend.hotness_score.toFixed(1)}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {item.alert && (
                      <span className="px-2 py-1 bg-yellow-200 text-yellow-800 rounded text-sm font-medium">
                        🔔 Alert
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {watchlist.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No cards in watchlist. Add cards from the trending page!
        </div>
      )}
    </div>
  );
}
