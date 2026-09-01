import { useState } from 'react';
import { ChevronDown, Info } from 'lucide-react';

// Kept in sync by hand with config.DEMO_RATE_LIMITS in server_deploy/config.py.
const LIMITS = {
  perVisitor: '1 question at a time · 3 per minute · 10 per day',
  shared: '3 at a time · 5 per minute · 100 per day across all visitors',
};

const DETAILS = [
  {
    term: 'Runs on a small server',
    detail:
      'A 1.5B-parameter model generating on CPU — no GPU. Expect roughly 10–40 seconds per answer, and slower still when someone else is asking at the same time.',
  },
  {
    term: 'It can get things wrong',
    detail:
      'Answers are grounded in the project documentation, but a model this small can still phrase things oddly, miss context, or occasionally fail to respond at all.',
  },
  {
    term: 'Usage is limited',
    detail: `${LIMITS.perVisitor} per visitor. ${LIMITS.shared}. The limits keep the demo responsive for everyone.`,
  },
];

/**
 * Sets expectations before anyone asks anything: this is a demo on modest
 * hardware, not a production service.
 *
 * variant="full"    — home page, always expanded
 * variant="compact" — chat page, one line that expands on demand
 */
export default function DemoNotice({ variant = 'full' }) {
  const [open, setOpen] = useState(false);
  const isCompact = variant === 'compact';

  if (isCompact) {
    return (
      <aside className="demo-notice demo-notice-compact">
        <button
          className="demo-notice-toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          <Info size={13} aria-hidden="true" />
          <span>Demo on a low-spec server — answers are slow and can be wrong</span>
          <ChevronDown
            size={13}
            aria-hidden="true"
            className={`demo-notice-chevron${open ? ' is-open' : ''}`}
          />
        </button>
        {open && (
          <dl className="demo-notice-list">
            {DETAILS.map(({ term, detail }) => (
              <div key={term}>
                <dt>{term}</dt>
                <dd>{detail}</dd>
              </div>
            ))}
          </dl>
        )}
      </aside>
    );
  }

  return (
    <aside className="demo-notice">
      <div className="demo-notice-label">Before you start</div>
      <p className="demo-notice-lead">
        This is a public demo, not a production service. The assistant runs entirely on a
        modest CPU-only server, so it is slow and occasionally unreliable.
      </p>
      <dl className="demo-notice-list">
        {DETAILS.map(({ term, detail }) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{detail}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
