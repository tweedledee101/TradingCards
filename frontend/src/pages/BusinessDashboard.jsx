import { useState, useEffect } from 'react';
import { getBusinessDashboard, getBusinessPlan, setBusinessGoal, recordCapitalTransaction } from '../api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const BusinessDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showGoalForm, setShowGoalForm] = useState(false);
  const [showCapitalForm, setShowCapitalForm] = useState(false);
  const [hoursOverride, setHoursOverride] = useState('');

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const dash = await getBusinessDashboard();
      setDashboard(dash);
      if (dash.has_goal) {
        const p = await getBusinessPlan();
        setPlan(p);
      }
    } catch (err) {
      setError('Failed to load business dashboard');
    } finally {
      setLoading(false);
    }
  };

  const refreshPlan = async () => {
    try {
      const hours = hoursOverride ? parseFloat(hoursOverride) : null;
      const p = await getBusinessPlan(hours);
      setPlan(p);
    } catch (err) { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-frost-dim text-sm">Loading business dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-loss text-sm">{error}</div>
      </div>
    );
  }

  if (!dashboard?.has_goal) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8 min-w-0">
        <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-4">Business Planner</h1>
        <p className="text-sm text-frost-dim mb-6">Set your business goal to get started.</p>
        <GoalForm onSave={() => { setShowGoalForm(false); fetchAll(); }} />
      </div>
    );
  }

  const d = dashboard;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8 min-w-0">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl font-display font-semibold text-frost-light tracking-wide mb-1">Business Planner</h1>
          <p className="text-sm text-frost-dim break-words">
            Year 1 target: ${d.year.target_profit?.toLocaleString()} | Day {d.year.pct_complete > 0 ? Math.round(365 * d.year.pct_complete / 100) : 0} of 365
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <button onClick={() => setShowCapitalForm(!showCapitalForm)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-card text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
            Record Transaction
          </button>
          <button onClick={fetchAll}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-ember/20 text-ember-light border border-ember/20 hover:bg-ember/30 transition-colors">
            Refresh
          </button>
        </div>
      </div>

      {/* Capital Transaction Form */}
      {showCapitalForm && (
        <div className="card-surface p-4 mb-6">
          <CapitalForm onSave={() => { setShowCapitalForm(false); fetchAll(); }} />
        </div>
      )}

      {/* Top Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Available Capital" value={`$${d.today.available_capital?.toLocaleString()}`} />
        <StatCard label="Daily Target" value={`$${d.today.daily_target_profit?.toFixed(2)}`}
          sub={d.today.catchup_amount > 0 ? `+$${d.today.catchup_amount.toFixed(2)} catchup` : null} />
        <StatCard label="Today's Profit" value={`$${d.today.profit_so_far?.toFixed(2)}`}
          gain={d.today.profit_so_far > 0} />
        <StatCard label="YTD Profit" value={`$${d.year.actual_profit?.toFixed(2)}`}
          sub={`${d.year.pct_complete}% of target`}
          gain={d.year.actual_profit > 0} />
      </div>

      {/* Week + Month Progress */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        <ProgressCard title="This Week" actual={d.week.actual_profit} target={d.week.target_profit}
          pct={d.week.pct_complete} sub={`${d.week.days_remaining} days left`} />
        <ProgressCard title="This Month" actual={d.month.actual_profit} target={d.month.target_profit}
          pct={d.month.target_profit > 0 ? (d.month.actual_profit / d.month.target_profit * 100) : 0} />
      </div>

      {/* Inventory Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatCard label="Inventory" value={d.inventory.total_cards} sub="cards owned" />
        <StatCard label="Listed" value={d.inventory.listed} />
        <StatCard label="Unlisted" value={d.inventory.unlisted}
          warn={d.inventory.unlisted > 0} />
        <StatCard label="Cost Basis" value={`$${d.inventory.cost_basis?.toFixed(2)}`} />
      </div>

      {/* Today's Plan */}
      {plan && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-lg font-display font-semibold text-frost-light">Today's Plan</h2>
            <span className="text-xs text-frost-dim bg-surface-card px-2 py-0.5 rounded-md">
              {plan.available_hours?.toFixed(1)}h available
            </span>
            <div className="flex-1" />
            <input type="number" placeholder="Hours" value={hoursOverride}
              onChange={e => setHoursOverride(e.target.value)}
              className="w-16 px-2 py-1 rounded-lg text-xs bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40" />
            <button onClick={refreshPlan}
              className="px-2 py-1 rounded-lg text-xs font-medium bg-surface-card text-frost-dim border border-surface-border hover:text-frost-light transition-colors">
              Update
            </button>
          </div>

          <div className="space-y-2">
            {plan.actions?.map((action, i) => (
              <ActionCard key={i} action={action} />
            ))}
            {(!plan.actions || plan.actions.length === 0) && (
              <div className="card-surface p-4 text-center text-xs text-frost-dim">
                No actions generated. Set up inventory or wait for pipeline opportunities.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 12-Month Trajectory */}
      {d.trajectory && d.trajectory.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-display font-semibold text-frost-light mb-3">12-Month Trajectory</h2>
          <div className="card-surface p-4">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={d.trajectory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2e3345" />
                <XAxis dataKey="month" tick={{ fill: '#7b93ab', fontSize: 11 }}
                  tickFormatter={m => `M${m}`} />
                <YAxis tick={{ fill: '#7b93ab', fontSize: 11 }}
                  tickFormatter={v => `$${(v / 1000).toFixed(1)}k`} />
                <Tooltip content={<TrajectoryTooltip />} />
                <Line type="monotone" dataKey="cumulative_profit" stroke="#22c55e"
                  strokeWidth={2} dot={false} name="Cumulative Profit" />
                <Line type="monotone" dataKey="capital" stroke="#e8590c"
                  strokeWidth={2} dot={false} name="Capital" />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex items-center justify-center gap-6 mt-2 text-xs text-frost-dim">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-gain inline-block rounded" /> Cumulative Profit
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-ember inline-block rounded" /> Working Capital
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Goal Settings */}
      <div className="border-t border-surface-border pt-6">
        <button onClick={() => setShowGoalForm(!showGoalForm)}
          className="text-xs text-frost-dim hover:text-frost-light transition-colors">
          {showGoalForm ? 'Hide Goal Settings' : 'Edit Goal Settings'}
        </button>
        {showGoalForm && (
          <div className="mt-4">
            <GoalForm onSave={() => { setShowGoalForm(false); fetchAll(); }} />
          </div>
        )}
      </div>
    </div>
  );
};


const StatCard = ({ label, value, sub, gain, warn }) => (
  <div className="card-surface px-4 py-3">
    <div className="text-[10px] text-frost-dim uppercase tracking-wider mb-1">{label}</div>
    <div className={`text-lg font-mono font-semibold ${gain ? 'text-gain' : warn ? 'text-amber-400' : 'text-frost-light'}`}>
      {value}
    </div>
    {sub && <div className="text-[10px] text-frost-dim mt-0.5">{sub}</div>}
  </div>
);


const ProgressCard = ({ title, actual, target, pct, sub }) => {
  const clampedPct = Math.min(Math.max(pct || 0, 0), 100);
  const color = clampedPct >= 80 ? 'bg-gain' : clampedPct >= 40 ? 'bg-amber-400' : 'bg-ember';

  return (
    <div className="card-surface px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-frost-light">{title}</span>
        <span className="text-xs text-frost-dim">{sub}</span>
      </div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-lg font-mono font-semibold text-frost-light">${actual?.toFixed(2)}</span>
        <span className="text-xs text-frost-dim">/ ${target?.toFixed(2)}</span>
      </div>
      <div className="w-full h-1.5 bg-surface-raised rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${clampedPct}%` }} />
      </div>
    </div>
  );
};


const ActionCard = ({ action }) => {
  const typeColors = {
    buy: 'border-gain/30 bg-gain/5',
    list: 'border-blue-500/30 bg-blue-500/5',
    reprice: 'border-amber-500/30 bg-amber-500/5',
    research: 'border-frost-dim/20 bg-surface-card',
  };
  const typeBadge = {
    buy: 'bg-gain/15 text-gain',
    list: 'bg-blue-500/15 text-blue-400',
    reprice: 'bg-amber-500/15 text-amber-400',
    research: 'bg-surface-raised text-frost-dim',
  };

  const [expanded, setExpanded] = useState(action.type === 'buy');

  return (
    <div className={`rounded-xl border ${typeColors[action.type] || 'border-surface-border bg-surface-card'}`}>
      <div role="button" tabIndex={0} onClick={() => setExpanded(!expanded)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded); } }}
        className="flex items-center gap-3 px-4 py-3 cursor-pointer">
        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${typeBadge[action.type] || ''}`}>
          {action.type}
        </span>
        <span className="text-sm text-frost-light flex-1">{action.description}</span>
        <span className="text-xs text-frost-dim">{action.est_time_min} min</span>
        {action.est_profit > 0 && (
          <span className="text-xs font-mono font-semibold text-gain">+${action.est_profit?.toFixed(2)}</span>
        )}
        <span className={`text-frost-dim text-xs transition-transform ${expanded ? 'rotate-180' : ''}`}>&#9660;</span>
      </div>

      {expanded && action.items?.length > 0 && (
        <div className="border-t border-surface-border px-4 py-3 space-y-1.5">
          {action.items.map((item, i) => (
            <div key={i} className="flex items-center gap-3 text-xs bg-surface-raised rounded-lg px-3 py-2">
              {action.type === 'buy' ? (
                <>
                  <span className="text-frost-light flex-1 min-w-0 truncate">
                    {item.player} - {item.card}{item.parallel ? ` (${item.parallel})` : ''}
                  </span>
                  <span className="font-mono text-frost-light shrink-0">${item.cost?.toFixed(2)}</span>
                  <span className="font-mono text-gain shrink-0">+${item.est_profit?.toFixed(2)}</span>
                  <span className="font-mono text-frost-dim shrink-0">{item.roi?.toFixed(0)}%</span>
                  {item.ebay_url && (
                    <a href={item.ebay_url} target="_blank" rel="noopener noreferrer"
                      className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gain/20 text-gain border border-gain/20 hover:bg-gain/30 transition-colors shrink-0">
                      Buy
                    </a>
                  )}
                </>
              ) : (
                <span className="text-frost-dim">
                  Item #{item.inventory_id} - ${item.purchase_price?.toFixed(2)} cost
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


const TrajectoryTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-xs">
      <div className="text-frost-light font-semibold mb-1">Month {d.month}</div>
      <div className="text-gain">Profit: ${d.cumulative_profit?.toLocaleString()}</div>
      <div className="text-ember-light">Capital: ${d.capital?.toLocaleString()}</div>
      <div className="text-frost-dim">Monthly: ${d.monthly_profit?.toLocaleString()}</div>
    </div>
  );
};


const GoalForm = ({ onSave }) => {
  const [form, setForm] = useState({
    annual_income_target: 120000,
    starting_capital: 1000,
    weekly_hours_weekday: 12.5,
    weekly_hours_weekend: 8,
    target_margin_pct: 0.25,
    platform_fee_pct: 0.13,
    reinvest_pct: 1.0,
    goal_start_date: new Date().toISOString().split('T')[0],
  });
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await setBusinessGoal(form);
      setResult(res);
      if (onSave) onSave();
    } catch (err) {
      setResult({ error: 'Failed to save goal' });
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ label, name, type = 'number', step }) => (
    <div>
      <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">{label}</label>
      <input type={type} step={step || 'any'} value={form[name]}
        onChange={e => setForm({ ...form, [name]: type === 'number' ? parseFloat(e.target.value) : e.target.value })}
        className="w-full px-3 py-1.5 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light focus:outline-none focus:border-ember/40" />
    </div>
  );

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Field label="Annual Target ($)" name="annual_income_target" />
        <Field label="Starting Capital ($)" name="starting_capital" />
        <Field label="Weekday Hours/wk" name="weekly_hours_weekday" />
        <Field label="Weekend Hours/wk" name="weekly_hours_weekend" />
        <Field label="Target Margin %" name="target_margin_pct" step="0.01" />
        <Field label="Platform Fee %" name="platform_fee_pct" step="0.01" />
        <Field label="Reinvest %" name="reinvest_pct" step="0.01" />
        <Field label="Start Date" name="goal_start_date" type="date" />
      </div>
      <button type="submit" disabled={saving}
        className="px-4 py-2 rounded-lg text-sm font-medium bg-ember/20 text-ember-light border border-ember/20 hover:bg-ember/30 transition-colors disabled:opacity-50">
        {saving ? 'Saving...' : 'Set Goal'}
      </button>
      {result?.message && (
        <div className="mt-3 text-sm text-gain">{result.message}</div>
      )}
      {result?.error && (
        <div className="mt-3 text-sm text-loss">{result.error}</div>
      )}
    </form>
  );
};


const CapitalForm = ({ onSave }) => {
  const [form, setForm] = useState({ amount: '', type: 'deposit', description: '' });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.amount) return;
    setSaving(true);
    try {
      await recordCapitalTransaction({
        amount: parseFloat(form.amount),
        type: form.type,
        description: form.description || null,
      });
      if (onSave) onSave();
    } catch (err) { /* ignore */ }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <div>
        <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">Type</label>
        <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
          className="px-3 py-1.5 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light focus:outline-none focus:border-ember/40">
          <option value="deposit">Deposit</option>
          <option value="sale">Sale</option>
          <option value="purchase">Purchase</option>
          <option value="withdrawal">Withdrawal</option>
        </select>
      </div>
      <div>
        <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">Amount ($)</label>
        <input type="number" step="0.01" value={form.amount}
          onChange={e => setForm({ ...form, amount: e.target.value })}
          className="w-24 px-3 py-1.5 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light focus:outline-none focus:border-ember/40" />
      </div>
      <div className="flex-1">
        <label className="text-[10px] text-frost-dim uppercase tracking-wider block mb-1">Description</label>
        <input type="text" value={form.description}
          onChange={e => setForm({ ...form, description: e.target.value })}
          placeholder="Optional note"
          className="w-full px-3 py-1.5 rounded-lg text-sm bg-surface-card border border-surface-border text-frost-light placeholder:text-frost-dim/50 focus:outline-none focus:border-ember/40" />
      </div>
      <button type="submit" disabled={saving}
        className="px-4 py-1.5 rounded-lg text-sm font-medium bg-ember/20 text-ember-light border border-ember/20 hover:bg-ember/30 transition-colors disabled:opacity-50">
        {saving ? '...' : 'Save'}
      </button>
    </form>
  );
};


export default BusinessDashboard;
