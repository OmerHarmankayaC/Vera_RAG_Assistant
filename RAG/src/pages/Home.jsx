import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="hero-wrapper">
      <div className="container editorial-grid">
        <div className="margin-label">Vera Q&A</div>
        <div className="hero-content">
          <h1>An informational assistant for exploring Vera-Finance's privacy-first design.</h1>
          <p>
            Ask how Vera-Finance handles your data, what it can do, and how it's built — answered from its own documentation.
          </p>

          <div className="hero-action">
            <button
              className="primary-btn"
              onClick={() => navigate('/chat')}
            >
              Try it <ArrowRight size={16} />
            </button>
            <div className="hero-preview">
              e.g. "Where does Vera store my data?"
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
