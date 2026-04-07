import React, { useState } from "react";
import { Copy, Check, User, Bot, ExternalLink, Zap, Clock, FileText } from 'lucide-react';

function Message({ 
  sender, 
  text = "", 
  timestamp, 
  formatTime = (t) => t, 
  images = [],
  contextUsed = false,
  sources = [],
  sessionId
}) {
  const isUser = sender === "user";
  const [preview, setPreview] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6`}>
      <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
        
        {/* Modern Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-10 h-10 rounded-full flex items-center justify-center shadow-sm ${
            isUser 
              ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white' 
              : 'bg-gradient-to-r from-slate-100 to-slate-200 text-slate-600 border-2 border-white'
          }`}>
            {isUser ? (
              <User className="w-5 h-5" />
            ) : (
              <Bot className="w-5 h-5" />
            )}
          </div>
        </div>

        {/* Message Content */}
        <div className={`group max-w-full ${isUser ? 'text-right' : 'text-left'}`}>
          
          {/* Context Indicator for AI messages */}
          {!isUser && contextUsed && (
            <div className="flex items-center space-x-2 mb-2 text-xs">
              <div className="flex items-center space-x-1 bg-green-50 text-green-700 px-3 py-1 rounded-full border border-green-200">
                <Zap className="w-3 h-3" />
                <span className="font-medium">Used conversation context</span>
              </div>
            </div>
          )}

          {/* Main Message Bubble */}
          <div className={`relative rounded-2xl px-4 py-3 shadow-sm ${
            isUser
              ? "bg-gradient-to-r from-blue-500 to-blue-600 text-white"
              : "bg-white text-slate-800 border border-slate-200"
          }`}>
            
            {/* Message Text */}
            <div className="whitespace-pre-wrap break-words leading-relaxed">
              {text}
            </div>

            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className={`absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg ${
                isUser
                  ? 'text-blue-200 hover:text-white hover:bg-blue-400'
                  : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
              }`}
              title="Copy message"
            >
              {copied ? (
                <Check className="w-4 h-4" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Images/Charts */}
          {Array.isArray(images) && images.length > 0 && (
            <div className="mt-4 space-y-3">
              {images.map((src, idx) => (
                <div key={idx} className="rounded-xl overflow-hidden shadow-lg border border-slate-200">
                  <img
                    src={src}
                    alt={`Attachment ${idx + 1}`}
                    className="w-full cursor-pointer hover:opacity-95 transition-opacity"
                    onClick={() => setPreview(src)}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Sources for AI Messages */}
          {!isUser && sources && sources.length > 0 && (
            <div className="mt-4">
              <div className="text-xs text-slate-600 font-medium mb-3 flex items-center space-x-1">
                <FileText className="w-3 h-3" />
                <span>Sources referenced:</span>
              </div>
              <div className="grid gap-2">
                {sources.slice(0, 3).map((source, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-3 text-xs bg-slate-50 rounded-lg p-3 border border-slate-200 hover:bg-slate-100 transition-colors"
                  >
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-slate-800 truncate">
                        {source.filename || source.title || `Source ${index + 1}`}
                      </div>
                      {source.content_preview && (
                        <div className="text-slate-600 truncate text-xs mt-1">
                          {source.content_preview}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {sources.length > 3 && (
                  <div className="text-xs text-slate-500 text-center py-2 bg-slate-50 rounded-lg border border-slate-200">
                    +{sources.length - 3} more sources
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Timestamp and Session Info */}
          <div className={`mt-2 flex items-center space-x-2 text-xs text-slate-500 ${
            isUser ? 'justify-end' : 'justify-start'
          }`}>
            <Clock className="w-3 h-3" />
            <span>{formatTime(timestamp)}</span>
            {sessionId && (
              <>
                <span>•</span>
                <span className="text-blue-500 font-medium">Session {sessionId.slice(-6)}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Fullscreen Image Preview */}
      {preview && (
        <div
          className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"
          onClick={() => setPreview(null)}
        >
          <div className="relative max-w-[95%] max-h-[95%]">
            <img
              src={preview}
              alt="Preview"
              className="max-w-full max-h-full rounded-xl shadow-2xl"
            />
            <button
              onClick={() => setPreview(null)}
              className="absolute top-4 right-4 bg-black/50 text-white p-3 rounded-full hover:bg-black/70 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Message;
