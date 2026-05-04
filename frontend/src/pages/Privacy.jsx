const Privacy = () => {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-2xl font-display font-bold text-frost-light mb-6">Privacy Policy</h1>
      <div className="text-sm text-frost-dim space-y-4">
        <p><strong className="text-frost-light">Last updated:</strong> May 3, 2026</p>

        <h2 className="text-lg text-frost-light mt-6">What We Collect</h2>
        <p>When you connect your eBay account to Ragnarok Gaming, we access your public listing data
        (active listings, item details, pricing) to display your cards for sale on our storefront.
        We do not collect your eBay password.</p>

        <h2 className="text-lg text-frost-light mt-6">How We Use Your Data</h2>
        <p>Your eBay listing data is used solely to display your cards on ragnarokgamez.com and to
        help you manage your trading card inventory. We do not sell or share your data with third parties.</p>

        <h2 className="text-lg text-frost-light mt-6">Data Storage</h2>
        <p>Your data is stored securely on AWS infrastructure (RDS, S3) in the us-east-1 region.
        OAuth tokens are encrypted and stored server-side only.</p>

        <h2 className="text-lg text-frost-light mt-6">Your Rights</h2>
        <p>You can revoke Ragnarok Gaming's access to your eBay account at any time through your
        eBay account settings under Third-party app access. Upon revocation, we will delete your
        stored tokens and listing data.</p>

        <h2 className="text-lg text-frost-light mt-6">Contact</h2>
        <p>Questions about this policy? Contact us at privacy@ragnarokgamez.com.</p>
      </div>
    </div>
  );
};

export default Privacy;
