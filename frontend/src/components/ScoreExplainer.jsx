import { useState } from 'react';

const ScoreExplainer = ({ card }) => {
  const [isOpen, setIsOpen] = useState(false);

  const getBuyZone = (avgPrice, velocity) => {
    let multiplier;
    if (velocity > 70) multiplier = 0.85;
    else if (velocity > 40) multiplier = 0.75;
    else multiplier = 0.65;
    return avgPrice * multiplier;
  };

  const buyZone = getBuyZone(card.avg_price, card.velocity_score);
  const velocityMultiplier = card.velocity_score > 70 ? 0.85 : card.velocity_score > 40 ? 0.75 : 0.65;

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 text-xs"
        title="Explain Score"
      >
        📊
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setIsOpen(false)}>
          <div className="bg-white rounded-lg p-6 max-w-3xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-bold">{card.player_name} - Score Breakdown</h2>
              <button onClick={() => setIsOpen(false)} className="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>

            {/* Hotness Score */}
            <div className="mb-6 p-4 bg-orange-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">🔥 Hotness Score: {card.hotness_score.toFixed(1)}</h3>
              <p className="text-sm text-gray-700 mb-3">
                Composite score indicating overall market momentum (0-100 scale)
              </p>
              <div className="bg-white p-3 rounded border">
                <div className="font-mono text-sm mb-2">
                  Hotness = (Velocity × 0.40) + (Momentum × 0.35) + (Social × 0.25)
                </div>
                <div className="text-sm space-y-1">
                  <div>• Velocity Score: {card.velocity_score.toFixed(1)} × 0.40 = {(card.velocity_score * 0.40).toFixed(1)}</div>
                  <div>• Momentum Score: {card.momentum_score?.toFixed(1) || 'N/A'} × 0.35 = {((card.momentum_score || 0) * 0.35).toFixed(1)}</div>
                  <div>• Social Score: {card.social_score?.toFixed(1) || '0'} × 0.25 = {((card.social_score || 0) * 0.25).toFixed(1)}</div>
                </div>
              </div>
              <div className="mt-3 text-sm">
                <strong>Interpretation:</strong>
                <ul className="list-disc ml-5 mt-1">
                  <li>80-100: 🔥 FIRE - Strong buy signal, high momentum</li>
                  <li>60-79: 📈 TRENDING - Good opportunity, watch closely</li>
                  <li>40-59: 👀 WATCH - Moderate interest, monitor</li>
                  <li>0-39: 😴 STABLE - Low activity, skip for now</li>
                </ul>
              </div>
            </div>

            {/* Velocity Score */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">⚡ Velocity Score: {card.velocity_score.toFixed(1)}</h3>
              <p className="text-sm text-gray-700 mb-3">
                Measures price change rate over time (week-over-week)
              </p>
              <div className="bg-white p-3 rounded border">
                <div className="font-mono text-sm mb-2">
                  Velocity = ((Current Price - Week Ago Price) / Week Ago Price) × 100
                </div>
                <div className="text-sm">
                  <div>Current Avg: ${card.avg_price.toFixed(2)}</div>
                  <div>Week Ago: ${(card.avg_price / (1 + card.velocity_score/100)).toFixed(2)} (estimated)</div>
                  <div>Change: {card.velocity_score > 0 ? '+' : ''}{card.velocity_score.toFixed(1)}%</div>
                </div>
              </div>
              <div className="mt-3 text-sm">
                <strong>Data Source:</strong> eBay sold listings (last 14 days)
              </div>
            </div>

            {/* Buy Zone */}
            <div className="mb-6 p-4 bg-green-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">🎯 Buy Zone: ${buyZone.toFixed(2)}</h3>
              <p className="text-sm text-gray-700 mb-3">
                Recommended maximum purchase price based on velocity
              </p>
              <div className="bg-white p-3 rounded border">
                <div className="font-mono text-sm mb-2">
                  Buy Zone = Avg Price × Velocity Multiplier
                </div>
                <div className="text-sm space-y-1">
                  <div>• Avg Price: ${card.avg_price.toFixed(2)}</div>
                  <div>• Velocity: {card.velocity_score.toFixed(1)}</div>
                  <div>• Multiplier: {velocityMultiplier} ({card.velocity_score > 70 ? 'Hot' : card.velocity_score > 40 ? 'Moderate' : 'Cold'})</div>
                  <div>• Buy Zone: ${card.avg_price.toFixed(2)} × {velocityMultiplier} = ${buyZone.toFixed(2)}</div>
                </div>
              </div>
              <div className="mt-3 text-sm">
                <strong>Multiplier Logic:</strong>
                <ul className="list-disc ml-5 mt-1">
                  <li>Velocity &gt; 70: 0.85 (Hot - buy closer to market)</li>
                  <li>Velocity 40-70: 0.75 (Moderate - standard discount)</li>
                  <li>Velocity &lt; 40: 0.65 (Cold - deeper discount needed)</li>
                </ul>
              </div>
            </div>

            {/* Profit Margin */}
            <div className="mb-6 p-4 bg-purple-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">💰 Profit Margin: {(((card.avg_price - buyZone) / buyZone) * 100).toFixed(1)}%</h3>
              <p className="text-sm text-gray-700 mb-3">
                Expected profit if bought at buy zone and sold at average price
              </p>
              <div className="bg-white p-3 rounded border">
                <div className="font-mono text-sm mb-2">
                  Margin = ((Avg Price - Buy Zone) / Buy Zone) × 100
                </div>
                <div className="text-sm space-y-1">
                  <div>• Buy at: ${buyZone.toFixed(2)}</div>
                  <div>• Sell at: ${card.avg_price.toFixed(2)}</div>
                  <div>• Gross Profit: ${(card.avg_price - buyZone).toFixed(2)}</div>
                  <div>• Margin: {(((card.avg_price - buyZone) / buyZone) * 100).toFixed(1)}%</div>
                </div>
              </div>
              <div className="mt-3 text-sm text-yellow-700">
                <strong>⚠️ Note:</strong> This is gross margin. Subtract eBay fees (~13%), shipping, and grading costs for net profit.
              </div>
            </div>

            {/* Data Sources */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">📊 Data Sources</h3>
              <div className="text-sm space-y-2">
                <div>✅ <strong>eBay Browse API:</strong> Sold listings, prices, volume</div>
                <div>✅ <strong>Card Ladder:</strong> Price benchmarks, velocity ratings</div>
                <div>✅ <strong>PSA Population:</strong> Grading data, PSA 10 rates</div>
                <div>⏳ <strong>Social Media:</strong> Coming soon (Twitter/Reddit sentiment)</div>
              </div>
            </div>

            {/* How to Use */}
            <div className="p-4 bg-yellow-50 rounded-lg border-2 border-yellow-300">
              <h3 className="text-lg font-semibold mb-2">💡 How to Use These Scores</h3>
              <ol className="list-decimal ml-5 text-sm space-y-2">
                <li><strong>Hotness &gt; 70:</strong> Strong buy signal - add to watchlist immediately</li>
                <li><strong>Current Price ≤ Buy Zone:</strong> Good entry point - consider purchasing</li>
                <li><strong>Profit Margin &gt; 20%:</strong> Good flip potential after fees</li>
                <li><strong>Volume &gt; 10:</strong> Liquid market - easier to sell</li>
                <li><strong>Green Row:</strong> In buy zone - act fast</li>
                <li><strong>Yellow Row:</strong> Close to buy zone - monitor closely</li>
              </ol>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Got it!
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ScoreExplainer;
