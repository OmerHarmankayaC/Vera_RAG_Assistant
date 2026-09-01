import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import ChatMessage from '../components/ChatMessage';
import SampleQuestions from '../components/SampleQuestions';
import DemoNotice from '../components/DemoNotice';

const GENERIC_ERROR =
  'Something went wrong on the server. This demo runs on modest hardware, so this happens occasionally — please try again in a moment.';
const NETWORK_ERROR =
  'Could not reach the server. It may be restarting or under load — please try again in a moment.';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [usedQuestions, setUsedQuestions] = useState(new Set());
  const [quotaLeft, setQuotaLeft] = useState(null); // questions left today, from the server
  const [cooldown, setCooldown] = useState(0); // seconds until the next question is allowed

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isWaiting]);

  // Tick the rate-limit countdown so the input re-enables on its own.
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const readQuota = (res) => {
    const left = res.headers.get('X-Demo-Quota-Remaining-Day');
    if (left !== null) setQuotaLeft(Number(left));
  };

  const addMessage = (message) => setMessages((prev) => [...prev, message]);

  const handleSend = async (text) => {
    const question = text.trim();
    if (!question || isTyping || cooldown > 0) return;

    addMessage({ id: Date.now(), text: question, sender: 'user' });
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
      readQuota(res);

      // 429 = rate limited. The server explains which limit was hit and for how
      // long, so show its message verbatim rather than a generic "slow down".
      if (res.status === 429) {
        const body = await res.json().catch(() => null);
        const retryAfter = Number(res.headers.get('Retry-After')) || body?.error?.retry_after || 0;
        setCooldown(Math.min(retryAfter, 60)); // never lock the input for more than a minute
        addMessage({
          id: aiMsgId,
          sender: 'system',
          text:
            body?.error?.message ??
            'You have reached the demo usage limit. Please try again shortly.',
        });
        return;
      }

      if (!res.ok || !res.body) {
        addMessage({ id: aiMsgId, sender: 'system', text: GENERIC_ERROR });
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
          addMessage({ id: aiMsgId, text: answer, sender: 'ai' });
        } else {
          setMessages((prev) => prev.map((m) => (m.id === aiMsgId ? { ...m, text: answer } : m)));
        }
      }
    } catch (error) {
      console.error('Failed to fetch response', error);
      addMessage({ id: aiMsgId, sender: 'system', text: NETWORK_ERROR });
    } finally {
      setIsTyping(false);
      setIsWaiting(false);
    }
  };

  const handleQuestionClick = (questionText) => {
    setUsedQuestions((prev) => new Set(prev).add(questionText));
    handleSend(questionText);
  };

  const inputDisabled = isTyping || cooldown > 0;

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <p>Welcome to Vera Q&amp;A.</p>
            <p>Ask a question to start the chat.</p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} text={msg.text} sender={msg.sender} />
        ))}

        {isWaiting && (
          <div className="message ai">
            <div className="speaker-label">VERA</div>
            <div className="typing-indicator">
              <span className="typing-label">is answering</span>
              <span className="typing-cursor"></span>
            </div>
            <div className="typing-hint">
              CPU-only server — this usually takes 10–40 seconds.
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <DemoNotice variant="compact" />

        {/* Sample questions are a way in for a fresh visitor — hide them while an
            answer is being generated so they can't queue up another request. */}
        {!isTyping && <SampleQuestions onSelect={handleQuestionClick} usedQuestions={usedQuestions} />}

        <div className="input-wrapper">
          <input
            type="text"
            className="chat-input"
            placeholder={cooldown > 0 ? `Rate limited — ${cooldown}s` : 'Ask a question...'}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend(inputValue);
            }}
            disabled={inputDisabled}
          />
          <button
            className="send-btn"
            onClick={() => handleSend(inputValue)}
            disabled={!inputValue.trim() || inputDisabled}
            aria-label="Send"
          >
            <Send size={24} />
          </button>
        </div>

        <div className="chat-status" role="status">
          {cooldown > 0
            ? `Please wait ${cooldown}s before asking again.`
            : quotaLeft !== null && `${quotaLeft} question${quotaLeft === 1 ? '' : 's'} left today.`}
        </div>
      </div>
    </div>
  );
}
