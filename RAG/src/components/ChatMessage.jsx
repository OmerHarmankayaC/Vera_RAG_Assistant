const SOURCES_PATTERN = /\n\(sources?:\s*[^)]*\)\s*$/i;

const SPEAKER_LABEL = { user: 'YOU', ai: 'VERA', system: 'NOTICE' };

export default function ChatMessage({ text, sender }) {
  const isAnswer = sender === 'ai';

  // Only model answers carry a trailing "(sources: ...)" line worth splitting out.
  const sourcesMatch = isAnswer ? text.match(SOURCES_PATTERN) : null;
  const mainText = sourcesMatch ? text.slice(0, sourcesMatch.index) : text;
  const sourcesText = sourcesMatch ? sourcesMatch[0].trim() : null;

  return (
    <div className={`message ${sender}`}>
      <div className="speaker-label">{SPEAKER_LABEL[sender] ?? 'VERA'}</div>
      <div className="message-content">{mainText}</div>
      {sourcesText && <div className="message-sources">{sourcesText}</div>}
    </div>
  );
}
