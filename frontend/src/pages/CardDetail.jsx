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

  const buyPrice = (card.trend.avg_price * 0.93).toFixed(2);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <Link to="/" className="text-blue-600 hover:underline mb-4 inline-block">
          ← Back to Trending
        </Link>

        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h1 className="text-3xl font-bold mb-2">
            {card.player_name} - {card.card_year} {card.card_set}
          </h1>
          {card.is_rookie && <span className="text-green-600 font-semibold">🏆 ROOKIE CARD</span>}
          <p className="text-gray-600">{card.sport}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-sm text-gray-600">Average Price</div>
            <div className="text-3xl font-bold">${card.trend.avg_price.toFixed(2)}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-sm text-gray-600">Hotness Score</div>
            <div className="text-3xl font-bold text-orange-600">{card.trend.hotness_score.toFixed(1)}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="text-sm text-gray-600">🎯 Buy Under</div>
            <div className="text-3xl font-bold text-green-600">${buyPrice}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <PriceChart sales={card.recent_sales} />
          <ProfitCalculator avgPrice={card.trend.avg_price} />
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
