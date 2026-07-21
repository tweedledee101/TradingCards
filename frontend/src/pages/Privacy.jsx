const Privacy = () => {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-2xl font-display font-bold text-frost-light mb-6">Privacy Policy</h1>
      <div className="text-sm text-frost-dim space-y-4">
        <p><strong className="text-frost-light">Last updated:</strong> July 21, 2026</p>

        <h2 className="text-lg text-frost-light mt-6">What We Collect</h2>
        <p>When you connect your eBay account to Ragnarok Gamez, we access your public listing data
        (active listings, item details, pricing) to display your cards for sale on our storefront.
        We do not collect your eBay password.</p>
        <p>When you buy or sell through Ragnarok Exclusive checkout, we collect your email, shipping
        address, and order history. Payment card details are collected and processed directly by
        Stripe, our payment processor - we never see or store your full card number. Sellers go
        through Stripe Connect onboarding, which collects identity and payout information directly
        with Stripe on our behalf; we store only the resulting account reference, not your banking
        details.</p>

        <h2 className="text-lg text-frost-light mt-6">How We Use Your Data</h2>
        <p>Your eBay listing data is used solely to display your cards on ragnarokgamez.com and to
        help you manage your trading card inventory. Checkout and shipping data is used to process
        orders, arrange shipping, and handle disputes or refunds. We do not sell or share your data
        with third parties beyond the processors (Stripe, AWS) needed to run the site.</p>

        <h2 className="text-lg text-frost-light mt-6">Data Storage</h2>
        <p>Your data is stored securely on AWS infrastructure (RDS, S3) in the us-east-1 region.
        OAuth tokens are encrypted and stored server-side only. Payment information is stored by
        Stripe under their own security and compliance program, not on our servers.</p>

        <h2 className="text-lg text-frost-light mt-6">Your Rights</h2>
        <p>You can revoke Ragnarok Gamez's access to your eBay account at any time through your
        eBay account settings under Third-party app access. Upon revocation, we will delete your
        stored tokens and listing data.</p>

        <h2 className="text-lg text-frost-light mt-6">Contact</h2>
        <p>Questions about this policy? Contact us at privacy@ragnarokgamez.com.</p>
      </div>
    </div>
  );
};

export default Privacy;
