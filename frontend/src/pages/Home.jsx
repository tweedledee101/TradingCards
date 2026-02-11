import { useState, useEffect } from 'react';
import { getTrendingCards } from '../api/client';
import TrendingTable from '../components/TrendingTable';

const Home = () => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCards = async () => {
      try {
        const data = await getTrendingCards(25);
        setCards(data.cards);
      } catch (err) {
        setError('Failed to load trending cards');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCards();
  }, []);

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
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🔥 Trending Cards
          </h1>
          <p className="text-gray-600">
            Find hot rookie cards to flip for profit
          </p>
        </div>

        {cards.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow text-center">
            <p className="text-gray-600">No trending cards found. Import data first!</p>
          </div>
        ) : (
          <TrendingTable cards={cards} />
        )}
      </div>
    </div>
  );
};

export default Home;
