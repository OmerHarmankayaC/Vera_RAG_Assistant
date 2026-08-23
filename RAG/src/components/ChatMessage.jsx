const SOURCES_PATTERN = /\n\(sources?:\s*[^)]*\)\s*$/i;

export default function ChatMessage({ text, sender }) {
  const isUser = sender === 'user';
  const speakerLabel = isUser ? 'YOU' : 'VERA';

  const sourcesMatch = !isUser && text.match(SOURCES_PATTERN);
  const mainText = sourcesMatch ? text.slice(0, sourcesMatch.index) : text;
  const sourcesText = sourcesMatch ? sourcesMatch[0].trim() : null;

  return (
    <div className={`message ${isUser ? 'user' : 'ai'}`}>
      <div className="speaker-label">{speakerLabel}</div>
      <div className="message-content">
        {mainText}
      </div>
      {sourcesText && (
        <div className="message-sources">{sourcesText}</div>
      )}
    </div>
  );
}
