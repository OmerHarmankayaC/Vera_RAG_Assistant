const defaultQuestions = [
  "What are the app's features?",
  "How does it ensure security?",
  "What's the difference between free and premium plans?",
  "How does the personal inflation module work?"
];

export default function SampleQuestions({ onSelect, usedQuestions }) {
  // Filtreleme işlemi: Sadece kullanılmamış soruları göster
  const availableQuestions = defaultQuestions.filter(q => !usedQuestions.has(q));

  if (availableQuestions.length === 0) {
    return null;
  }

  return (
    <div className="sample-questions">
      {availableQuestions.map((q, idx) => (
        <button 
          key={idx} 
          className="sample-btn"
          onClick={() => onSelect(q)}
        >
          {q}
        </button>
      ))}
    </div>
  );
}
