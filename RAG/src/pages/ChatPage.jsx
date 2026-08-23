import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Chat from './Chat';
import Footer from '../components/Footer';

export default function ChatPage() {
  return (
    <>
      <div className="chat-page">
        <div className="container editorial-grid chat-page-grid">
          <div className="margin-label">
            <Link to="/" className="chat-back-link">
              <ArrowLeft size={14} />
              Back
            </Link>
          </div>
          <Chat />
        </div>
      </div>
      <Footer />
    </>
  );
}
