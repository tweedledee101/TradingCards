export function VerificationBadge({ status }) {
  const s = status || 'pending';
  if (s === 'verified') {
    return (
      <span title="Cross-source checks passed" className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gain/15 text-gain border border-gain/25 shrink-0">
        Verified
      </span>
    );
  }
  if (s === 'conflict') {
    return (
      <span title="Sources disagree — review manually" className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-loss/15 text-loss border border-loss/25 shrink-0">
        Conflict
      </span>
    );
  }
  if (s === 'skipped') {
    return (
      <span title="Automated verification not applied" className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-surface-raised text-frost-dim border border-surface-border shrink-0">
        Skipped
      </span>
    );
  }
  return (
    <span title="Automated cross-check not complete" className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-frost-dim/10 text-frost-dim border border-surface-border/80 shrink-0">
      Unverified
    </span>
  );
}

export function ConfidenceBadge({ source }) {
  if (!source || source === 'scp') {
    return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gain/15 text-gain border border-gain/20">SCP</span>;
  }
  if (source === 'sold_comps') {
    return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/20">Sold Comps</span>;
  }
  if (source === 'ebay_comps') {
    return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20">Market Comps</span>;
  }
  return null;
}
