import { Link } from 'react-router-dom';

const linkClass = 'text-frost-dim hover:text-frost-light transition-colors py-2 min-h-[44px] inline-flex items-center sm:min-h-0 sm:py-0';

/**
 * Shared footer: legal placeholders + careers/contact. Works on public and app shells.
 */
export default function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer
      className="border-t border-surface-border bg-surface-card/40 mt-auto pb-[max(2rem,env(safe-area-inset-bottom,0px))]"
      role="contentinfo"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 sm:pt-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 text-sm">
          <div>
            <div className="text-label mb-3">Company</div>
            <ul className="space-y-1 flex flex-col">
              <a href="mailto:careers@ragnarokgamez.com" className={linkClass}>
                Careers
              </a>
              <a href="mailto:hello@ragnarokgamez.com" className={linkClass}>
                Contact
              </a>
            </ul>
          </div>
          <div>
            <div className="text-label mb-3">Legal</div>
            <ul className="space-y-1 flex flex-col">
              <span className={`${linkClass} cursor-default opacity-60 pointer-events-none`} title="Coming soon">
                Privacy Policy
              </span>
              <span className={`${linkClass} cursor-default opacity-60 pointer-events-none`} title="Coming soon">
                Terms of Service
              </span>
            </ul>
          </div>
          <div>
            <div className="text-label mb-3">Product</div>
            <ul className="space-y-1 flex flex-col">
              <Link to="/help" className={linkClass}>
                Help &amp; trust
              </Link>
              <a href="https://ragnarokgamez.com" className={linkClass} target="_blank" rel="noopener noreferrer">
                ragnarokgamez.com
              </a>
            </ul>
          </div>
          <div className="sm:col-span-2 lg:col-span-1 lg:text-right">
            <div className="text-label mb-3 lg:sr-only">Rights</div>
            <p className="text-xs text-frost-dim leading-relaxed">
              © {year} Ragnarok Gaming. All rights reserved.
            </p>
            <p className="text-[10px] text-frost-dim/80 mt-2 leading-relaxed">
              Trademarks and card images are property of their respective owners.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
