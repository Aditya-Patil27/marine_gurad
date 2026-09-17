import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Individual chat message component with markdown support
 */
export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg p-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-md border border-gray-200 dark:border-gray-700'
        }`}
      >
        {/* Message Content */}
        <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : 'dark:prose-invert'}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Metadata for Assistant Messages */}
        {!isUser && message.confidence !== undefined && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
            {/* Confidence Score */}
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-600 dark:text-gray-400">Data Confidence:</span>
              <div className="flex items-center space-x-2">
                <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      message.confidence >= 80
                        ? 'bg-green-500'
                        : message.confidence >= 60
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${message.confidence}%` }}
                  ></div>
                </div>
                <span className="font-semibold text-gray-700 dark:text-gray-300">
                  {message.confidence}%
                </span>
              </div>
            </div>

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="text-xs">
                <span className="text-gray-600 dark:text-gray-400">Sources: </span>
                <span className="text-gray-700 dark:text-gray-300">
                  {message.sources.join(', ')}
                </span>
              </div>
            )}

            {/* Tool Calls (Debug Info) */}
            {message.toolCalls && message.toolCalls.length > 0 && (
              <details className="text-xs text-gray-500 dark:text-gray-400">
                <summary className="cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
                  🔧 Tool Calls ({message.toolCalls.length})
                </summary>
                <div className="mt-2 space-y-1 pl-2">
                  {message.toolCalls.map((tool, idx) => (
                    <div key={idx} className="font-mono text-[10px] bg-gray-100 dark:bg-gray-900 p-2 rounded">
                      <div className="font-semibold text-blue-600 dark:text-blue-400">
                        {tool.name}
                      </div>
                      <div className="text-gray-600 dark:text-gray-400 truncate">
                        {JSON.stringify(tool.arguments)}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className={`text-[10px] mt-2 ${isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
