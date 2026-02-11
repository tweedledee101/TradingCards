import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getInventory, getInventoryStats } from '../api/client';

export default function Inventory() {
  const [inventory, setInventory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('owned');

  useEffect(() => {
    loadData();
  }, [filter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [invData, statsData] = await Promise.all([
        getInventory(filter),
        getInventoryStats()
      ]);
      setInventory(invData.inventory);
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load inventory:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">My Inventory</h1>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Total Invested</div>
            <div className="text-2xl font-bold">${stats.total_invested}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Current Value</div>
            <div className="text-2xl font-bold">${stats.current_value}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Total Profit</div>
            <div className={`text-2xl font-bold ${stats.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ${stats.total_profit}
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">ROI</div>
            <div className={`text-2xl font-bold ${stats.roi_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.roi_percentage}%
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setFilter('owned')}
          className={`px-4 py-2 rounded ${filter === 'owned' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Owned
        </button>
        <button
          onClick={() => setFilter('listed')}
          className={`px-4 py-2 rounded ${filter === 'listed' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Listed
        </button>
        <button
          onClick={() => setFilter('sold')}
          className={`px-4 py-2 rounded ${filter === 'sold' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Sold
        </button>
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Card</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Purchase</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Profit</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ROI</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grade</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {inventory.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <Link to={`/card/${item.card.id}`} className="text-blue-600 hover:underline">
                    <div className="font-medium">{item.card.player_name}</div>
                    <div className="text-sm text-gray-500">
                      {item.card.card_year} {item.card.card_set}
                    </div>
                  </Link>
                </td>
                <td className="px-6 py-4">
                  <div className="font-medium">${item.purchase_price}</div>
                  <div className="text-sm text-gray-500">{item.purchase_date}</div>
                </td>
                <td className="px-6 py-4">
                  {item.current_value ? `$${item.current_value}` : '-'}
                </td>
                <td className="px-6 py-4">
                  {item.unrealized_profit !== null ? (
                    <span className={item.unrealized_profit >= 0 ? 'text-green-600' : 'text-red-600'}>
                      ${item.unrealized_profit}
                    </span>
                  ) : '-'}
                </td>
                <td className="px-6 py-4">
                  {item.roi_percentage !== null ? (
                    <span className={item.roi_percentage >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {item.roi_percentage}%
                    </span>
                  ) : '-'}
                </td>
                <td className="px-6 py-4">{item.quantity}</td>
                <td className="px-6 py-4">
                  {item.graded ? `${item.grade_company} ${item.grade_value}` : 'Raw'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
