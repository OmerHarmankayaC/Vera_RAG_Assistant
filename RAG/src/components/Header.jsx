import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight } from 'lucide-react';

export default function Header() {
  return (
    <div className="container">
      <header className="nav-header">
        <Link to="/" className="nav-brand">
          <img src={`${import.meta.env.BASE_URL}vera_qa_spark_eight_rays_bold.png`} alt="Vera Logo" className="nav-brand-icon" style={{ height: '48px', width: 'auto' }} />
          <span className="nav-brand-text">VERA</span>
          <span className="nav-brand-badge">RAG ASSISTANT</span>
        </Link>
        <nav className="nav-links">
          <a href="https://www.omerharmankaya.com/" className="portfolio-link" target="_blank" rel="noopener noreferrer">
            <ArrowLeft size={14} />
            <span className="portfolio-link-text">Back to portfolio</span>
          </a>
          <a href="https://vera.staticorbit.dev/" className="portfolio-link" target="_blank" rel="noopener noreferrer">
            <span className="portfolio-link-text">Go to Vera</span>
            <ArrowUpRight size={14} />
          </a>
        </nav>
      </header>
    </div>
  );
}
