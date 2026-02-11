import { useState, useEffect } from 'react';
import { getTrendingCards } from '../api/client';
import TrendingTable from '../components/TrendingTable';

const Home = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [focusMode, setFocusMode] = useState(false);
  const [maxBudget, setMaxBudget] = useState(null);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('hotness');
  const itemsPerPage = 25;

  useEffect(() => {
    fetchCards();
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

  const getProfitMargin = (avgPrice, velocity) => {
    const buyZone = getBuyZone(avgPrice, velocity);
    return ((avgPrice - buyZone) / buyZone) * 100;
  };

  let filteredCards = cards;
  
  if (maxBudget) {
    filteredCards = filteredCards.filter(card => {
      const buyZone = getBuyZone(card.avg_price, card.velocity_score);
      return buyZone <= maxBudget;
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
                onClick={fetchCards}
                className="px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
              >
                🔄 Refresh
              </button>
            </div>
          </div>
          
          <div className="flex gap-4 items-center bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Max Budget:</label>
              <input
                type="number"
                placeholder="No limit"
                value={maxBudget || ''}
                onChange={(e) => setMaxBudget(e.target.value ? parseFloat(e.target.value) : null)}
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
