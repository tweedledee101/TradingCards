import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

function Opportunities() {
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [flipMode, setFlipMode] = useState('all'); // 'quick', 'sit', 'all'
  const [filters, setFilters] = useState({
    minBudget: '',
    maxBudget: '',
    minRoi: '',
    momentumFilter: ''
  });

  const copySearchTerm = (opp) => {
    const searchTerm = `${opp.card_year} ${opp.card_set} ${opp.player_name}${opp.parallel && opp.parallel !== 'Base' ? ` ${opp.parallel}` : ''}${opp.card_number ? ` ${opp.card_number}` : ''}${opp.grade_company ? ` ${opp.grade_company} ${opp.grade_value}` : ''}`;
    navigator.clipboard.writeText(searchTerm);
    alert(`Copied: ${searchTerm}`);
  };

  useEffect(() => {
    fetchOpportunities();
  }, []);

  const fetchOpportunities = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.minBudget) params.min_budget = filters.minBudget;
      if (filters.maxBudget) params.max_budget = filters.maxBudget;
      if (filters.minRoi) params.min_roi = filters.minRoi;
      if (filters.momentumFilter) params.momentum_filter = filters.momentumFilter;

      const response = await axios.get(`${API_BASE}/opportunities`, { params });
      setOpportunities(response.data.opportunities || []);
    } catch (error) {
      console.error('Error fetching opportunities:', error);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceBadge = (confidence) => {
    const badges = {
      'VERY HIGH': '🔥 VERY HIGH',
      'HIGH': '✅ HIGH',
      'MEDIUM': '⚠️ MEDIUM',
      'LOW': '🥶 LOW'
    };
    return badges[confidence] || confidence;
  };

  const filteredOpportunities = opportunities.filter(opp => {
    if (flipMode === 'quick') {
      return opp.market_data?.avg_days_to_sell <= 14;
    } else if (flipMode === 'sit') {
      return opp.market_data?.avg_days_to_sell > 14;
    }
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">💰 Arbitrage Opportunities</h1>
        <p className="text-gray-600">Cards you can buy below market rate and flip for profit</p>
      </div>

      {/* Mode Toggle */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Strategy Mode</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setFlipMode('quick')}
              className={`px-6 py-2 rounded-lg font-semibold transition ${
                flipMode === 'quick'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              🚀 Quick Flip Mode
              <div className="text-xs mt-1">High turnover (≤14 days)</div>
            </button>
            <button
              onClick={() => setFlipMode('sit')}
              className={`px-6 py-2 rounded-lg font-semibold transition ${
                flipMode === 'sit'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              💤 Sit & Wait Mode
              <div className="text-xs mt-1">Patient strategy (>14 days)</div>
            </button>
            <button
              onClick={() => setFlipMode('all')}
              className={`px-6 py-2 rounded-lg font-semibold transition ${
                flipMode === 'all'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              📊 All Opportunities
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">🔍 Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min Budget</label>
            <input
              type="number"
              value={filters.minBudget}
              onChange={(e) => setFilters({...filters, minBudget: e.target.value})}
              className="w-full px-3 py-2 border rounded"
              placeholder="$0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Budget</label>
            <input
              type="number"
              value={filters.maxBudget}
              onChange={(e) => setFilters({...filters, maxBudget: e.target.value})}
              className="w-full px-3 py-2 border rounded"
              placeholder="$1000"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min ROI %</label>
            <input
              type="number"
              value={filters.minRoi}
              onChange={(e) => setFilters({...filters, minRoi: e.target.value})}
              className="w-full px-3 py-2 border rounded"
              placeholder="10"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Momentum</label>
            <select
              value={filters.momentumFilter}
              onChange={(e) => setFilters({...filters, momentumFilter: e.target.value})}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="">All</option>
              <option value="rising">Rising Only</option>
              <option value="stable">Stable Only</option>
            </select>
          </div>
        </div>
        <button
          onClick={fetchOpportunities}
          className="mt-4 bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          Apply Filters
        </button>
      </div>

      {/* Opportunities List */}
      {loading ? (
        <div className="text-center py-12">Loading opportunities...</div>
      ) : filteredOpportunities.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">
            No {flipMode === 'quick' ? 'quick flip' : flipMode === 'sit' ? 'sit & wait' : ''} opportunities found matching your criteria.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-sm text-gray-600 mb-2">
            Showing {filteredOpportunities.length} {flipMode === 'quick' ? 'quick flip' : flipMode === 'sit' ? 'sit & wait' : ''} opportunities
          </div>
          {filteredOpportunities.map((opp, index) => (
            <div key={index} className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-gray-900">
                    {opp.card_year} {opp.card_set} {opp.player_name}
                    {opp.parallel && opp.parallel !== 'Base' && ` ${opp.parallel}`}
                    {opp.card_number && ` #${opp.card_number}`}
                  </h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-sm text-gray-600">{opp.sport}</span>
                    {opp.grade_company && (
                      <span className="text-sm font-semibold text-purple-600">
                        {opp.grade_company} {opp.grade_value}
                      </span>
                    )}
                    {!opp.grade_company && (
                      <span className="text-sm text-gray-500">Raw</span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-blue-600">
                    Score: {opp.opportunity_score?.toFixed(1) || opp.score?.toFixed(1) || 'N/A'}/100
                  </div>
                  <div className="text-sm mt-1">
                    {getConfidenceBadge(opp.confidence_level || opp.confidence)}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Arbitrage Section */}
                <div className="bg-green-50 rounded-lg p-4">
                  <h4 className="font-semibold text-green-900 mb-3">💰 Arbitrage</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-700">Sales (this variant):</span>
                      <span className="font-bold">{opp.market_data?.sales_count || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Buy Price:</span>
                      <span className="font-bold">${opp.arbitrage?.buy_price?.toFixed(2) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Market Rate:</span>
                      <span className="font-bold">${opp.market_data?.avg_price?.toFixed(2) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between border-t pt-2">
                      <span className="text-gray-700">Profit (after fees):</span>
                      <span className="font-bold text-green-600">
                        ${opp.arbitrage?.net_profit?.toFixed(2) || 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">ROI:</span>
                      <span className="font-bold text-green-600">
                        {opp.arbitrage?.roi?.toFixed(1) || 'N/A'}%
                      </span>
                    </div>
                    <div className="flex justify-between border-t pt-2">
                      <span className="text-gray-700">Flip Speed:</span>
                      <span className="font-bold text-blue-600">
                        {opp.market_data?.flip_speed || 'Unknown'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Est. Days to Sell:</span>
                      <span className="font-bold">
                        {opp.market_data?.avg_days_to_sell || 'N/A'} days
                      </span>
                    </div>
                  </div>
                </div>

                {/* Momentum Section */}
                <div className="bg-blue-50 rounded-lg p-4">
                  <h4 className="font-semibold text-blue-900 mb-3">📈 Momentum</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-700">Price Trend:</span>
                      <span className="font-bold">
                        {opp.momentum?.price_trend || 'N/A'} 
                        {opp.momentum?.price_change_45d ? `${opp.momentum.price_change_45d.toFixed(1)}%` : ''}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Sales/Week:</span>
                      <span className="font-bold">{opp.momentum?.sales_per_week?.toFixed(1) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Sell-Through Rate:</span>
                      <span className="font-bold">{opp.momentum?.str_rate?.toFixed(0) || 'N/A'}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Active Listings:</span>
                      <span className="font-bold">{opp.momentum?.active_listings || 'N/A'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                {opp.arbitrage?.ebay_url && (
                  <a
                    href={opp.arbitrage.ebay_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 font-semibold"
                  >
                    🛒 Buy on eBay
                  </a>
                )}
                <button 
                  onClick={() => copySearchTerm(opp)}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  📋 Copy Search Term
                </button>
                <button className="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
                  ⭐ Add to Watchlist
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Opportunities;
