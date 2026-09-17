import { useState } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { API_URL } from '../../lib/api';

/**
 * Marine Intelligence Assistant (MIA) Chat Interface
 * Floating chat widget with conversation history
 */
export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Hello! I\'m **MIA** (Marine Intelligence Assistant), your high-precision analytical agent for BlueGuard.\n\nI can help you with:\n- 🚢 **Vessel Intelligence**: Track vessels, analyze traffic, identify anomalies\n- 🛢️ **Pollution Data**: Oil spills, plastic density, chemical indicators\n- 🏝️ **MPA Compliance**: Monitor protected areas and violations\n- 📊 **Trend Analysis**: Compare data across time periods\n- 💡 **Platform Guide**: Learn how to use BlueGuard features\n\nWhat would you like to know?',
      timestamp: new Date(),
      confidence: 100,
      sources: []
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    // Add user message
    const userMessage = {
      role: 'user',
      content: messageText,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Prepare conversation history (exclude welcome message)
      const conversationHistory = messages
        .slice(1) // Skip welcome message
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }));

      const response = await fetch(`${API_URL}/api/v1/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          conversation_history: conversationHistory
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      // Add assistant response
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date(data.timestamp),
        confidence: data.data_confidence,
        sources: data.sources,
        toolCalls: data.tool_calls
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage = {
        role: 'assistant',
        content: `⚠️ I encountered an error processing your request: ${error.message}\n\nPlease try:\n- Rephrasing your question\n- Being more specific about the region or time period\n- Checking if the backend service is running`,
        timestamp: new Date(),
        confidence: 0,
        sources: []
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        role: 'assistant',
        content: '🔄 Conversation reset. How can I assist you with marine intelligence today?',
        timestamp: new Date(),
        confidence: 100,
        sources: []
      }
    ]);
  };

  return (
    <>
      {/* Chat Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-full p-4 shadow-2xl z-50 transition-all duration-200 hover:scale-110 ring-4 ring-blue-500/20"
          aria-label="Open chat"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <span className="absolute -top-1 -right-1 bg-green-500 rounded-full w-3 h-3 animate-pulse ring-2 ring-white"></span>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-gradient-to-br from-white to-blue-50 dark:from-gray-900 dark:to-blue-950 rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden border border-blue-200 dark:border-blue-800/50 ring-1 ring-blue-500/10">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-cyan-600 text-white p-4 flex items-center justify-between shadow-lg">
            <div className="flex items-center space-x-3">
              <div className="bg-white/20 backdrop-blur-sm rounded-full p-2 ring-2 ring-white/30">
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
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-sm">Marine Intelligence Assistant</h3>
                <p className="text-xs text-blue-100">MIA • Always Learning</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleReset}
                className="hover:bg-white/20 backdrop-blur-sm rounded p-1.5 transition-colors"
                aria-label="Reset conversation"
                title="Reset conversation"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="hover:bg-white/20 backdrop-blur-sm rounded p-1.5 transition-colors"
                aria-label="Close chat"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-br from-gray-50 to-blue-50/50 dark:from-gray-900 dark:to-blue-950/50">
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}
            {isLoading && (
              <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm">MIA is analyzing...</span>
              </div>
            )}
          </div>

          {/* Input */}
          <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
        </div>
      )}
    </>
  );
}
