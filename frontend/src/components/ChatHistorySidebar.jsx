import React from 'react';
import { 
  Plus, 
  Search, 
  Edit3, 
  Trash2, 
  Clock, 
  Check, 
  X,
  MessageSquare 
} from 'lucide-react';

function ChatHistorySidebar({
  allChatSessions = [],
  currentSession,
  isLoadingSessions,
  searchTerm,
  setSearchTerm,
  editingSession,
  newSessionTitle,
  setNewSessionTitle,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onStartEdit,
  onSaveEdit,
  onCancelEdit
}) {
  
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const filteredSessions = allChatSessions.filter(session =>
    session.title?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="w-80 bg-gradient-to-b from-slate-900 to-slate-800 border-r border-slate-700 flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold text-white flex items-center">
            <MessageSquare className="w-5 h-5 mr-2" />
            Chats
          </h2>
          <button
            onClick={onNewChat}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
            title="New Chat"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search chats..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Chat Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {isLoadingSessions ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="ml-3 text-gray-400">Loading your chats...</p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 px-4 text-center">
            <MessageSquare className="w-12 h-12 text-gray-600 mb-2" />
            <p className="text-gray-400 text-sm">No chats yet</p>
            <p className="text-gray-500 text-xs mt-1">Create your first chat to get started</p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {filteredSessions.map((session) => (
              <div
                key={session.id}
                className={`group relative rounded-lg transition-all ${
                  currentSession?.id === session.id
                    ? 'bg-blue-600/20 border border-blue-500/50'
                    : 'bg-slate-800/50 hover:bg-slate-700/50 border border-transparent'
                }`}
              >
                {editingSession === session.id ? (
                  <div className="p-3 flex items-center space-x-2">
                    <input
                      type="text"
                      value={newSessionTitle}
                      onChange={(e) => setNewSessionTitle(e.target.value)}
                      className="flex-1 px-2 py-1 bg-slate-900 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') onSaveEdit(session.id);
                        if (e.key === 'Escape') onCancelEdit();
                      }}
                    />
                    <button
                      onClick={() => onSaveEdit(session.id)}
                      className="p-1 rounded bg-green-600 hover:bg-green-700 text-white"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={onCancelEdit}
                      className="p-1 rounded bg-gray-600 hover:bg-gray-700 text-white"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div
                    onClick={() => onSelectSession(session)}
                    className="p-3 cursor-pointer"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-white font-medium text-sm truncate mb-1">
                          {session.title || 'Untitled Chat'}
                        </h3>
                        <div className="flex items-center text-xs text-gray-400">
                          <Clock className="w-3 h-3 mr-1" />
                          <span>{formatTime(session.created_at)}</span>
                          {session.message_count && (
                            <>
                              <span className="mx-2">•</span>
                              <span>{session.message_count} messages</span>
                            </>
                          )}
                        </div>
                      </div>
                      
                      {/* Action Buttons */}
                      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onStartEdit(session);
                          }}
                          className="p-1.5 rounded hover:bg-slate-600 text-gray-400 hover:text-white"
                          title="Rename"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm('Delete this chat?')) {
                              onDeleteSession(session.id);
                            }
                          }}
                          className="p-1.5 rounded hover:bg-red-600 text-gray-400 hover:text-white"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatHistorySidebar;
