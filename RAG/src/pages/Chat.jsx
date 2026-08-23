import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import ChatMessage from '../components/ChatMessage';
import SampleQuestions from '../components/SampleQuestions';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [usedQuestions, setUsedQuestions] = useState(new Set());

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isWaiting]);

  const handleSend = async (text) => {
    const question = text.trim();
    if (!question || isTyping) return;

    // Add user message
    const userMsg = { id: Date.now(), text: question, sender: 'user' };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsTyping(true);
    setIsWaiting(true);

    const aiMsgId = Date.now() + 1;

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      if (!res.ok || !res.body) {
        const errorText = res.status === 429
          ? 'You are sending questions too fast. Please wait a moment and try again.'
          : `Something went wrong (server returned ${res.status}).`;
        setMessages(prev => [...prev, { id: aiMsgId, text: errorText, sender: 'ai' }]);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let answer = '';
      let started = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        answer += decoder.decode(value, { stream: true });
        if (!started) {
          started = true;
          setIsWaiting(false);
          setMessages(prev => [...prev, { id: aiMsgId, text: answer, sender: 'ai' }]);
        } else {
          setMessages(prev => prev.map(m => (m.id === aiMsgId ? { ...m, text: answer } : m)));
        }
      }
    } catch (error) {
      console.error('Failed to fetch response', error);
      setMessages(prev => [...prev, { id: aiMsgId, text: 'Error: could not reach the server.', sender: 'ai' }]);
    } finally {
      setIsTyping(false);
      setIsWaiting(false);
    }
  };

  const handleQuestionClick = (questionText) => {
    setUsedQuestions(prev => new Set(prev).add(questionText));
    handleSend(questionText);
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', fontWeight: 'bold' }}>
            <p>Welcome to Vera Q&A.</p>
            <p>Ask a question to start the chat.</p>
          </div>
        )}
        
        {messages.map(msg => (
          <ChatMessage key={msg.id} text={msg.text} sender={msg.sender} />
        ))}
        
        {isWaiting && (
          <div className="message ai">
             <div className="speaker-label">VERA</div>
             <div className="typing-indicator">
               <span className="typing-label">is answering</span>
               <span className="typing-cursor"></span>
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {/* Sadece mesaj yokken veya yazım işlemi bittiğinde (boştayken) ve hiç mesaj yokken örnek soruları gösterelim.
            İsterse kullanıcı sohbet ilerledikçe de görebilir ama şartımız "mesaj varken veya yazılırken gizlenmesi" idi.
            Yani: sadece mesajlaşma başlamadan önce gösterelim veya hep gizleyelim? 
            "sorular sorulurken ve cevap hazırlanıp sunulurken örnek sorular gizlenmeli"
            Bu durumda mesaj dizisinde isTyping = true iken gizlensin, ancak cevap geldiğinde tekrar gösterilsin. */}
        {!isTyping && (
          <SampleQuestions 
            onSelect={handleQuestionClick} 
            usedQuestions={usedQuestions} 
          />
        )}
        
        <div className="input-wrapper">
          <input
            type="text"
            className="chat-input"
            placeholder="Ask a question..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend(inputValue);
            }}
            disabled={isTyping}
          />
          <button 
            className="send-btn" 
            onClick={() => handleSend(inputValue)}
            disabled={!inputValue.trim() || isTyping}
            aria-label="Send"
          >
            <Send size={24} />
          </button>
        </div>
      </div>
    </div>
  );
}
