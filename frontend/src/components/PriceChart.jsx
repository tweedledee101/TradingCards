import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const PriceChart = ({ sales }) => {
  const data = (sales || []).map(sale => ({
    date: new Date(sale.date).toLocaleDateString(),
    price: sale.price,
  })).reverse();

  if (!data.length) {
    return (
      <div className="card-surface p-4">
        <div className="text-label mb-3">Price History</div>
        <div className="flex items-center justify-center h-48 text-frost-dim text-xs">No sales data</div>
      </div>
    );
  }

  return (
    <div className="card-surface p-4">
      <div className="text-label mb-3">Price History</div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2e3345" />
          <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={{ stroke: '#2e3345' }} axisLine={{ stroke: '#2e3345' }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={{ stroke: '#2e3345' }} axisLine={{ stroke: '#2e3345' }} tickFormatter={v => `$${v}`} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1a1d27', border: '1px solid #2e3345', borderRadius: '8px', fontSize: '12px' }}
            labelStyle={{ color: '#64748b' }}
            itemStyle={{ color: '#ff6b1a' }}
            formatter={v => [`$${v.toFixed(2)}`, 'Price']}
          />
          <Line type="monotone" dataKey="price" stroke="#e8590c" strokeWidth={2} dot={{ fill: '#e8590c', r: 3 }} activeDot={{ r: 5, fill: '#ff6b1a' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PriceChart;
