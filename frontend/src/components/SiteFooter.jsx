import { Link } from 'react-router-dom';

const sep = <span className="text-surface-border select-none px-1" aria-hidden>·</span>;

/**
 * Compact footer: wrapped link row + short legal line (no tall multi-column list).
 */
export default function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer
      className="border-t border-surface-border bg-surface-card/40 mt-auto pb-[max(1.25rem,env(safe-area-inset-bottom,0px))]"
      role="contentinfo"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-5 sm:pt-6 text-center sm:text-left">
        <nav
          className="flex flex-wrap items-center justify-center sm:justify-start gap-x-1 gap-y-2 text-[11px] sm:text-xs text-frost-dim leading-snug"
          aria-label="Footer"
        >
          <a href="mailto:careers@ragnarokgamez.com" className="hover:text-frost-light transition-colors px-1 py-1 min-h-[40px] sm:min-h-0 inline-flex items-center">
            Careers
          </a>
          {sep}
          <a href="mailto:hello@ragnarokgamez.com" className="hover:text-frost-light transition-colors px-1 py-1 min-h-[40px] sm:min-h-0 inline-flex items-center">
            Contact
          </a>
          {sep}
          <Link to="/help" className="hover:text-frost-light transition-colors px-1 py-1 min-h-[40px] sm:min-h-0 inline-flex items-center">
            Help
          </Link>
          {sep}
          <span className="opacity-50 px-1 py-1 cursor-default" title="Coming soon">
            Privacy
          </span>
          {sep}
          <span className="opacity-50 px-1 py-1 cursor-default" title="Coming soon">
            Terms
          </span>
          {sep}
          <a
            href="https://ragnarokgamez.com"
            className="hover:text-frost-light transition-colors px-1 py-1 min-h-[40px] sm:min-h-0 inline-flex items-center"
            target="_blank"
            rel="noopener noreferrer"
          >
            ragnarokgamez.com
          </a>
        </nav>
        <p className="mt-3 text-[10px] sm:text-[11px] text-frost-dim/85 leading-relaxed max-w-xl mx-auto sm:mx-0">
          © {year} Ragnarok Gaming. All rights reserved. Card names and images belong to their owners.
        </p>
      </div>
    </footer>
  );
}
