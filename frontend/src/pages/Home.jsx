import { useState, useEffect } from 'react';
import { getTrendingCards } from '../api/client';
import TrendingTable from '../components/TrendingTable';
import AccuracyDashboard from '../components/AccuracyDashboard';

const Home = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [focusMode, setFocusMode] = useState(false);
  const [profitableOnly, setProfitableOnly] = useState(false);
  const [maxBudget, setMaxBudget] = useState(null);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('hotness');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    sport: '',
    minYear: '',
    maxYear: '',
    minHotness: '',
    maxHotness: ''
  });
  const itemsPerPage = 25;

  useEffect(() => {
    fetchCards();
    // Load saved budget from localStorage
    const savedBudget = localStorage.getItem('maxBudget');
    if (savedBudget) setMaxBudget(parseFloat(savedBudget));
  }, []);

  const fetchCards = async () => {
    setLoading(true);
    try {
      const data = await getTrendingCards(100);
      setCards(data.cards);
    } catch (err) {
      setError('Failed to load trending cards');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getBuyZone = (avgPrice, velocity) => {
    let multiplier;
    if (velocity > 70) multiplier = 0.85;
    else if (velocity > 40) multiplier = 0.75;
    else multiplier = 0.65;
    return avgPrice * multiplier;
  };

  const getNetProfit = (avgPrice, velocity) => {
    const buyZone = getBuyZone(avgPrice, velocity);
    const sellPrice = avgPrice;
    const fees = sellPrice * 0.13; // 13% eBay + PayPal fees
    return sellPrice - buyZone - fees;
  };

  const getProfitMargin = (avgPrice, velocity) => {
    const buyZone = getBuyZone(avgPrice, velocity);
    return ((avgPrice - buyZone) / buyZone) * 100;
  };

  const exportToCSV = () => {
    const headers = ['Rank', 'Player', 'Sport', 'Year', 'Set', 'Avg Price', 'Buy Zone', 'Margin %', 'Volume', 'Velocity', 'Hotness'];
    const rows = filteredCards.map((card, idx) => [
      idx + 1,
      card.player_name,
      card.sport,
      card.card_year,
      card.card_set,
      card.avg_price.toFixed(2),
      getBuyZone(card.avg_price, card.velocity_score).toFixed(2),
      getProfitMargin(card.avg_price, card.velocity_score).toFixed(1),
      card.sales_count,
      card.velocity_score.toFixed(1),
      card.hotness_score.toFixed(1)
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trending-cards-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleBudgetChange = (value) => {
    setMaxBudget(value);
    if (value) {
      localStorage.setItem('maxBudget', value);
    } else {
      localStorage.removeItem('maxBudget');
    }
  };

  const budgetPresets = [25, 50, 100, 250, 500, 1000];

  let filteredCards = cards;
  
  // Apply sport filter
  if (filters.sport) {
    filteredCards = filteredCards.filter(card => 
      card.sport.toLowerCase() === filters.sport.toLowerCase()
    );
  }
  
  // Apply year range filter
  if (filters.minYear) {
    filteredCards = filteredCards.filter(card => card.card_year >= parseInt(filters.minYear));
  }
  if (filters.maxYear) {
    filteredCards = filteredCards.filter(card => card.card_year <= parseInt(filters.maxYear));
  }
  
  // Apply hotness range filter
  if (filters.minHotness) {
    filteredCards = filteredCards.filter(card => card.hotness_score >= parseFloat(filters.minHotness));
  }
  if (filters.maxHotness) {
    filteredCards = filteredCards.filter(card => card.hotness_score <= parseFloat(filters.maxHotness));
  }
  
  // Apply budget filter
  if (maxBudget) {
    filteredCards = filteredCards.filter(card => {
      const buyZone = getBuyZone(card.avg_price, card.velocity_score);
      return buyZone <= maxBudget;
    });
  }
  
  // Apply profitable only filter
  if (profitableOnly) {
    filteredCards = filteredCards.filter(card => {
      const netProfit = getNetProfit(card.avg_price, card.velocity_score);
      return netProfit > 0;
    });
  }
  
  if (focusMode) {
    filteredCards = filteredCards.filter(card => card.hotness_score >= 60).slice(0, 10);
  }
  
  if (sortBy === 'margin') {
    filteredCards = [...filteredCards].sort((a, b) => 
      getProfitMargin(b.avg_price, b.velocity_score) - getProfitMargin(a.avg_price, a.velocity_score)
    );
  }
  
  const totalPages = Math.ceil(filteredCards.length / itemsPerPage);
  const startIdx = (page - 1) * itemsPerPage;
  const displayCards = filteredCards.slice(startIdx, startIdx + itemsPerPage);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-xl">Loading trending cards...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-xl text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                🔥 Trending Cards
              </h1>
              <p className="text-gray-600">
                Cards with the best flip potential - buy low, sell high
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setProfitableOnly(!profitableOnly)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  profitableOnly
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                {profitableOnly ? '💰 Profitable Only' : '💰 Show Profitable'}
              </button>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  showFilters
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                🔍 {showFilters ? 'Hide Filters' : 'Advanced Filters'}
              </button>
              <button
                onClick={() => setFocusMode(!focusMode)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  focusMode 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                {focusMode ? '🎯 Focus Mode' : '📊 Show All'}
              </button>
              <button
                onClick={exportToCSV}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
                title="Export to CSV"
              >
                📥 Export CSV
              </button>
              <button
                onClick={fetchCards}
                className="px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
              >
                🔄 Refresh
              </button>
            </div>
          </div>
          
          {showFilters && (
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200 mb-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sport</label>
                  <select
                    value={filters.sport}
                    onChange={(e) => setFilters({...filters, sport: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                  >
                    <option value="">All Sports</option>
                    <option value="Basketball">Basketball</option>
                    <option value="Football">Football</option>
                    <option value="Baseball">Baseball</option>
                    <option value="Hockey">Hockey</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Year Range</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minYear}
                      onChange={(e) => setFilters({...filters, minYear: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxYear}
                      onChange={(e) => setFilters({...filters, maxYear: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Hotness Range</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minHotness}
                      onChange={(e) => setFilters({...filters, minHotness: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxHotness}
                      onChange={(e) => setFilters({...filters, maxHotness: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    />
                  </div>
                </div>
              </div>
              <div className="mt-3 flex justify-end">
                <button
                  onClick={() => setFilters({sport: '', minYear: '', maxYear: '', minHotness: '', maxHotness: ''})}
                  className="px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded hover:bg-gray-50 text-sm font-medium"
                >
                  Clear All Filters
                </button>
              </div>
            </div>
          )}
          
          <div className="bg-white p-4 rounded-lg border border-gray-200 space-y-3">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Budget Presets:</label>
              <div className="flex gap-2">
                {budgetPresets.map(preset => (
                  <button
                    key={preset}
                    onClick={() => handleBudgetChange(preset)}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      maxBudget === preset
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    ${preset}
                  </button>
                ))}
                <button
                  onClick={() => handleBudgetChange(null)}
                  className="px-3 py-1 rounded text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
                >
                  Clear
                </button>
              </div>
            </div>
            
            <div className="flex gap-4 items-center">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">Custom Budget:</label>
                <input
                  type="number"
                  placeholder="Enter amount"
                  value={maxBudget || ''}
                  onChange={(e) => handleBudgetChange(e.target.value ? parseFloat(e.target.value) : null)}
                  className="px-3 py-1 border border-gray-300 rounded w-32 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">Sort By:</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="hotness">Hotness Score</option>
                  <option value="margin">Profit Margin %</option>
                </select>
              </div>
              {maxBudget && (
                <div className="text-sm text-gray-600">
                  Showing {filteredCards.length} cards under ${maxBudget}
                </div>
              )}
            </div>
          </div>
        </div>

        <AccuracyDashboard />

        {focusMode && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎯</span>
              <div>
                <div className="font-semibold text-blue-900">Focus Mode Active</div>
                <div className="text-sm text-blue-700">
                  Showing top {displayCards.length} cards with hotness ≥ 60
                </div>
              </div>
            </div>
          </div>
        )}

        {cards.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow text-center">
            <p className="text-gray-600">No trending cards found. Import data first!</p>
          </div>
        ) : (
          <>
            <TrendingTable cards={displayCards} />
            
            {!focusMode && totalPages > 1 && (
              <div className="mt-6 flex justify-center items-center gap-4">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ← Previous
                </button>
                <span className="text-sm text-gray-600">
                  Page {page} of {totalPages} ({filteredCards.length} cards)
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Home;
