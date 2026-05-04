import { useEffect, useState } from 'react';

const EbayCallback = () => {
  const [code, setCode] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const c = params.get('code');
    if (c) setCode(c);
  }, []);

  return (
    <div className="max-w-xl mx-auto px-4 py-16 text-center">
      <h1 className="text-xl font-display font-bold text-frost-light mb-4">eBay Account Connected</h1>
      {code ? (
        <div className="text-left bg-surface-card p-4 rounded-lg border border-surface-border">
          <p className="text-sm text-gain mb-3">Authorization successful. Run this in your terminal:</p>
          <code className="block text-xs font-mono bg-surface-base text-frost-light p-3 rounded border border-surface-border break-all select-all">
            /usr/local/bin/python3.12 _ebay_login.py
          </code>
          <p className="text-xs text-frost-dim mt-3">Then paste this URL at the prompt:</p>
          <textarea
            readOnly
            value={window.location.href}
            rows={3}
            className="w-full text-xs font-mono bg-surface-base text-frost-light p-2 rounded border border-surface-border mt-1"
            onClick={(e) => e.target.select()}
          />
        </div>
      ) : (
        <p className="text-sm text-frost-dim">No authorization code received.</p>
      )}
    </div>
  );
};

const EbayDeclined = () => (
  <div className="max-w-xl mx-auto px-4 py-16 text-center">
    <h1 className="text-xl font-display font-bold text-frost-light mb-4">Connection Declined</h1>
    <p className="text-sm text-frost-dim">You chose not to connect your eBay account. No data was shared.</p>
    <a href="/" className="text-ember hover:underline text-sm mt-4 inline-block">Return to Home</a>
  </div>
);

export { EbayCallback, EbayDeclined };
