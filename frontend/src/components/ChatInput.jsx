// components/ChatInput.jsx
import React from "react";
import { Send, Sparkles } from "lucide-react";

function ChatInput({
  userInput = "",
  setUserInput = () => {},
  handleSendMessage = () => {},
  isTyping = false,
  inputRef = null,
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {/* 🔥 LangGraph indicator */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs text-purple-600">
          <Sparkles className="w-3 h-3" />
          <span className="font-medium">Multi-agent AI ready</span>
        </div>
        <span className="text-xs text-gray-400">
          Press Enter to send, Shift+Enter for new line
        </span>
      </div>

      <div className="flex gap-2">
        <textarea
          ref={inputRef}
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents..."
          disabled={isTyping}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          rows={3}
        />
        <button
          onClick={handleSendMessage}
          disabled={isTyping || !userInput.trim()}
          className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 font-medium shadow-md hover:shadow-lg"
        >
          <Send className="w-5 h-5" />
          <span>Send</span>
        </button>
      </div>
    </div>
  );
}

export default ChatInput;
