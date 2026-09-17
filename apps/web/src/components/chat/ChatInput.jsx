import { useState, useRef, useEffect } from 'react';

/**
 * Chat input component with auto-resize textarea
 */
export default function ChatInput({ onSendMessage, disabled = false }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Send on Enter, new line on Shift+Enter
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Quick suggestion buttons
  const suggestions = [
    '🚢 Show vessel traffic',
    '🛢️ Recent pollution events',
    '🏝️ MPA status',
    '📊 Traffic trends'
  ];

  const handleSuggestionClick = (suggestion) => {
    if (!disabled) {
      const query = suggestion.replace(/^[^\s]+\s/, ''); // Remove emoji
      onSendMessage(query);
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      {/* Quick Suggestions */}
      {input.length === 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={disabled}
              className="text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex items-end space-x-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask MIA about vessels, pollution, MPAs..."
            className="w-full resize-none border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            rows={1}
            style={{ maxHeight: '120px' }}
          />
          <div className="absolute bottom-2 right-2 text-[10px] text-gray-400">
            {input.length > 0 && `${input.length} chars`}
          </div>
        </div>
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg p-2.5 transition-colors"
          aria-label="Send message"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
        </button>
      </form>

      <div className="mt-2 text-[10px] text-gray-500 dark:text-gray-400 text-center">
        Press Enter to send, Shift+Enter for new line
      </div>
    </div>
  );
}
