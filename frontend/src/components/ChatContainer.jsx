import React, { useEffect } from 'react';
import { Bot, Sparkles } from 'lucide-react';
import Message from './Message';

function ChatContainer({ 
  chatMessages = [],
  isTyping = false,
  chatEndRef,
  BACKEND_URL = 'http://localhost:8000'
}) {

  // 🔥 FIXED: Smart scroll behavior
  useEffect(() => {
    if (chatEndRef?.current) {
      const chatContainer = chatEndRef.current.parentElement;
      if (!chatContainer) return;

      const isNearBottom = 
        chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 150;

      if (isNearBottom || isTyping) {
        setTimeout(() => {
          chatEndRef.current?.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'end',
            inline: 'nearest'
          });
        }, 100);
      }
    }
  }, [chatMessages, isTyping, chatEndRef]);

  useEffect(() => {
    if (chatEndRef?.current && chatMessages.length > 0) {
      setTimeout(() => {
        chatEndRef.current?.scrollIntoView({ 
          behavior: 'auto', 
          block: 'end' 
        });
      }, 200);
    }
  }, []);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
      {chatMessages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center p-8">
          <div className="bg-gradient-to-br from-blue-500 to-indigo-600 p-6 rounded-full mb-6 shadow-xl">
            <Sparkles className="w-16 h-16 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-800 mb-3">
            Welcome to AI Assistant
          </h2>
          <p className="text-gray-600 text-lg max-w-md mb-6">
            Start a conversation or select a project to analyze documents.
          </p>
        </div>
      ) : (
        <>
          {chatMessages.map((msg, idx) => (
            <Message 
              key={`msg-${idx}-${msg.timestamp || Date.now()}`}
              sender={msg.sender}
              text={msg.text}
              timestamp={msg.timestamp}
              images={msg.images}
              contextUsed={msg.contextUsed}
              sources={msg.sources}
              sessionId={msg.sessionId}
              formatTime={(t) => new Date(t).toLocaleTimeString()}
            />
          ))}
        </>
      )}

      {isTyping && (
        <div className="flex items-start space-x-3 animate-fadeIn">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
          </div>
          <div className="flex-1 bg-white rounded-2xl shadow-sm p-4 border border-gray-100">
            <div className="flex space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        </div>
      )}

      <div ref={chatEndRef} />
    </div>
  );
}

export default ChatContainer;
