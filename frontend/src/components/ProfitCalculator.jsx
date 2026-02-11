import { useState } from 'react';

const ProfitCalculator = ({ avgPrice }) => {
  const [buyPrice, setBuyPrice] = useState((avgPrice * 0.93).toFixed(2));
  const [sellPrice, setSellPrice] = useState((avgPrice * 1.10).toFixed(2));

  const profit = (sellPrice - buyPrice).toFixed(2);
  const roi = ((profit / buyPrice) * 100).toFixed(1);
  const ebayFees = (sellPrice * 0.13).toFixed(2); // 13% eBay fees
  const netProfit = (profit - ebayFees).toFixed(2);

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">💡 Profit Calculator</h3>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Buy Price
          </label>
          <input
            type="number"
            value={buyPrice}
            onChange={(e) => setBuyPrice(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Sell Price
          </label>
          <input
            type="number"
            value={sellPrice}
            onChange={(e) => setSellPrice(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>

        <div className="border-t pt-4 space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-600">Gross Profit:</span>
            <span className="font-semibold">${profit}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">eBay Fees (13%):</span>
            <span className="text-red-600">-${ebayFees}</span>
          </div>
          <div className="flex justify-between text-lg font-bold">
            <span>Net Profit:</span>
            <span className={netProfit > 0 ? 'text-green-600' : 'text-red-600'}>
              ${netProfit}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">ROI:</span>
            <span className={roi > 0 ? 'text-green-600 font-semibold' : 'text-red-600'}>
              {roi}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfitCalculator;
