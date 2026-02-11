import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getCard } from '../api/client';
import PriceChart from '../components/PriceChart';
import ProfitCalculator from '../components/ProfitCalculator';

const CardDetail = () => {
  const { id } = useParams();
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCard = async () => {
      try {
        const data = await getCard(id);
        setCard(data);
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

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">
              Where to Buy ({card.active_listings_count} active)
            </h3>
            <p className="text-gray-600">
              Search eBay for "{card.player_name} {card.card_year} {card.card_set}"
            </p>
            <a
              href={`https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(card.player_name + ' ' + card.card_year + ' ' + card.card_set)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-block bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
            >
              Search on eBay →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CardDetail;
