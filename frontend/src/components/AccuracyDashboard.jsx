import { useState, useEffect } from 'react';

const AccuracyDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/accuracy/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load accuracy stats:', err);
        setLoading(false);
      });
  }, []);

  if (loading) return null;
  if (!stats || stats.total_predictions === 0) return null;

  const getAccuracyColor = (pct) => {
    if (pct >= 80) return 'text-green-600';
    if (pct >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg border-2 border-purple-200 mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-1">
            📊 Algorithm Accuracy
          </h3>
          <p className="text-sm text-gray-600">
            Tracking predictions since {new Date(stats.first_prediction).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-6">
          <div className="text-center">
            <div className={`text-3xl font-bold ${getAccuracyColor(stats.accuracy_pct)}`}>
              {stats.accuracy_pct}%
            </div>
            <div className="text-xs text-gray-600">Overall Accuracy</div>
            <div className="text-xs text-gray-500">
              {stats.correct_predictions}/{stats.total_predictions} correct
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {stats.avg_price_accuracy?.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Price Accuracy</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {stats.avg_velocity_accuracy?.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Velocity Accuracy</div>
          </div>
        </div>
      </div>
      <div className="mt-3 text-xs text-gray-600">
        💡 Predictions are evaluated after 7 days. Click 📊 on any card to see how scores are calculated.
      </div>
    </div>
  );
};

export default AccuracyDashboard;
