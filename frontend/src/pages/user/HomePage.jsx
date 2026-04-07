import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import toast, { Toaster } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import { 
  Send, 
  Sparkles, 
  MessageSquarePlus, 
  Menu, 
  X, 
  User, 
  Bot, 
  Settings,
  Plus,
  Edit3,
  Trash2,
  Clock,
  Search,
  Folder,
  FolderOpen,
  File,
  FileText,
  ChevronDown,
  ChevronRight,
  Upload,
  FileX,
  Crown,
  Shield,
  CheckCircle2,
  BarChart3,
  PieChart,
  TrendingUp,
  Download
} from 'lucide-react';

import {
  fetchProjects,
  createProject,
  fetchProjectFiles,
  uploadFiles,
  askQuestion,
  enhanceQuery,
  getChatSessions,
  createChatSession,
  askQuestionInSession,
  getChatSessionDetail,
  deleteChatSession,
  updateChatSession,
  askGeneralQuestion
} from '../../services/api';

const BACKEND_URL = 'http://localhost:8000';

function HomePage() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [token, setToken] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [projects, setProjects] = useState([]);
  
  // Multiple selections with arrays
  const [selectedProjects, setSelectedProjects] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  const [projectFiles, setProjectFiles] = useState({});
  
  // database-only storage
  const [chatMessages, setChatMessages] = useState([]);
  
  const [userInput, setUserInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [showProjectCreation, setShowProjectCreation] = useState(false);
  const [showProjectSidebar, setShowProjectSidebar] = useState(false);

  // database-only storage
  const [allChatSessions, setAllChatSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  
  const [expandedProjects, setExpandedProjects] = useState(new Set());
  const [editingSession, setEditingSession] = useState(null);
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Project access information
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [projectAccessInfo, setProjectAccessInfo] = useState({});

  // Upload state per project
  const [uploadQueue, setUploadQueue] = useState({});         // { [projectId]: File[] }
  const [uploadProgress, setUploadProgress] = useState({});   // { [projectId]: number 0..100 }
  const [uploadingProjectId, setUploadingProjectId] = useState(null);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  // Chart helper functions
  const getChartIcon = (chartType) => {
    switch (chartType?.toLowerCase()) {
      case 'pie':
        return <PieChart className="w-4 h-4" />;
      case 'line':
        return <TrendingUp className="w-4 h-4" />;
      case 'bar':
      default:
        return <BarChart3 className="w-4 h-4" />;
    }
  };

  const downloadChart = (chartUrl, filename = 'chart.png') => {
    const link = document.createElement('a');
    link.href = `${BACKEND_URL}${chartUrl}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Helpers
  const formatTime = (timestamp) =>
    new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const getFileIcon = (fileName) => {
    const ext = fileName.split(".").pop()?.toLowerCase();
    const iconClass = "w-4 h-4";
    
    switch (ext) {
      case "pdf": return <FileText className={`${iconClass} text-red-500`} />;
      case "doc": case "docx": return <FileText className={`${iconClass} text-blue-500`} />;
      case "xls": case "xlsx": case "csv": return <FileText className={`${iconClass} text-green-500`} />;
      case "ppt": case "pptx": return <FileText className={`${iconClass} text-orange-500`} />;
      case "txt": return <FileText className={`${iconClass} text-slate-500`} />;
      default: return <File className={`${iconClass} text-slate-400`} />;
    }
  };

  // Query enhancement
  const handleEnhanceQuery = async () => {
    if (!userInput.trim()) return;
    
    setIsEnhancing(true);
    try {
      const enhancedQuery = await enhanceQuery(userInput);
      setUserInput(enhancedQuery);
      toast.success("✨ Query enhanced!");
    } catch (error) {
      toast.error("Failed to enhance query");
    } finally {
      setIsEnhancing(false);
    }
  };

  // Sessions
  const loadSessionsFromBackend = async () => {
    try {
      setIsLoadingSessions(true);
      const backendSessions = await getChatSessions();
      setAllChatSessions(backendSessions || []);
      
      if (backendSessions && backendSessions.length > 0 && !currentSession) {
        await handleSessionSelect(backendSessions[0]);
      } else if (!backendSessions || backendSessions.length === 0) {
        setChatMessages([{
          id: 'welcome',
          sender: 'ai',
          text: "👋 Hello! I'm your AI assistant. I can help with general questions. Select a project on the right to analyze documents.",
          timestamp: new Date(),
          sessionId: null,
          contextUsed: false,
        }]);
      }
    } catch (error) {
      console.error('❌ Failed to load sessions:', error);
      setAllChatSessions([]);
      toast.error('Failed to load chat sessions');
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const createNewChatSession = async () => {
    try {
      const backendSession = await createChatSession(
        selectedProjects.length > 0 ? selectedProjects[0] : null,
        selectedProjects.length > 0 ? 'New Project Chat' : 'New General Chat'
      );
      
      const newSession = {
        ...backendSession,
        message_count: 0,
        last_message_at: null
      };
      
      setAllChatSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession);
      
      const welcomeMessage = {
        id: 'welcome-' + newSession.id,
        sender: 'ai',
        text: selectedProjects.length > 0 
          ? `🚀 New project chat started!`
          : "👋 New general chat started! Ask me anything, or select a project to analyze documents.",
        timestamp: new Date(),
        sessionId: newSession.id,
        contextUsed: false,
      };
      
      setChatMessages([welcomeMessage]);
      toast.success('✅ New chat session created!');
      return newSession;
      
    } catch (error) {
      console.error('❌ Session creation failed:', error);
      toast.error('Failed to create chat session');
      throw error;
    }
  };

  const handleSessionSelect = async (session) => {
    try {
      setCurrentSession(session);
      const sessionDetail = await getChatSessionDetail(session.id);
      
      if (sessionDetail && sessionDetail.messages && sessionDetail.messages.length > 0) {
        const formattedMessages = sessionDetail.messages.map(msg => {
          const metadata = msg.message_metadata ? 
            (typeof msg.message_metadata === 'string' ? 
              JSON.parse(msg.message_metadata) : msg.message_metadata) : {};
          
          return {
            id: msg.id,
            sender: msg.message_type === 'user' ? 'user' : 'ai',
            text: msg.content,
            timestamp: new Date(msg.created_at),
            sessionId: session.id,
            contextUsed: metadata.context_used || false,
            sources: metadata.sources || [],
            hasChart: metadata.has_chart || false,
            chartUrl: metadata.chart_url || null,
            chartType: metadata.chart_type || null
          };
        });
        
        setChatMessages(formattedMessages);
      } else {
        const welcomeMessage = {
          id: 'welcome-' + session.id,
          sender: 'ai',
          text: session.project_id 
            ? "👋 Welcome back to your project chat! How can I help you today?"
            : "👋 Welcome back! How can I help you today?",
          timestamp: new Date(session.created_at),
          sessionId: session.id,
          contextUsed: false,
        };
        setChatMessages([welcomeMessage]);
      }
    } catch (error) {
      console.error('❌ Failed to load session messages:', error);
      toast.error('Failed to load session messages');
      setChatMessages([]);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteChatSession(sessionId);
      toast.success('Session deleted successfully');
      
      setAllChatSessions(prev => prev.filter(s => s.id !== sessionId));
      
      if (currentSession?.id === sessionId) {
        const remaining = allChatSessions.filter(s => s.id !== sessionId);
        if (remaining.length > 0) {
          await handleSessionSelect(remaining[0]);
        } else {
          setCurrentSession(null);
          setChatMessages([{
            id: 'welcome',
            sender: 'ai',
            text: "👋 Hello! Create a new chat to get started.",
            timestamp: new Date(),
            sessionId: null,
            contextUsed: false,
          }]);
        }
      }
    } catch (error) {
      console.error('❌ Failed to delete session:', error);
      toast.error('Failed to delete session');
    }
  };

  const handleRenameSession = async (sessionId, newTitle) => {
    try {
      await updateChatSession(sessionId, { title: newTitle });
      toast.success('Session renamed successfully');
      
      setAllChatSessions(prev => 
        prev.map(session => 
          session.id === sessionId 
            ? { ...session, title: newTitle, updated_at: new Date().toISOString() }
            : session
        )
      );
      
      if (currentSession?.id === sessionId) {
        setCurrentSession(prev => ({ ...prev, title: newTitle }));
      }
    } catch (error) {
      console.error('❌ Failed to update session title:', error);
      toast.error('Failed to rename session');
    }
  };

  const startEditSession = (session) => {
    setEditingSession(session.id);
    setNewSessionTitle(session.title);
  };

  const finishEditSession = async (session) => {
    if (newSessionTitle.trim() && newSessionTitle !== session.title) {
      await handleRenameSession(session.id, newSessionTitle.trim());
    }
    setEditingSession(null);
    setNewSessionTitle('');
  };

  // Projects
  const toggleProject = (projectId) => {
    if (selectedProjects.includes(projectId)) {
      setSelectedProjects(selectedProjects.filter(id => id !== projectId));
    } else {
      setSelectedProjects([projectId]);
    }
  };

  const toggleFile = (fileName) => {
    if (selectedFiles.includes(fileName)) {
      setSelectedFiles(selectedFiles.filter(name => name !== fileName));
    } else {
      setSelectedFiles([...selectedFiles, fileName]);
    }
  };

  const toggleProjectExpansion = async (projectId) => {
    const newExpanded = new Set(expandedProjects);
    
    if (newExpanded.has(projectId)) {
      newExpanded.delete(projectId);
    } else {
      newExpanded.add(projectId);
      
      if (!projectFiles[projectId]) {
        try {
          const data = await fetchProjectFiles(projectId);
          const files = Array.isArray(data.files) ? data.files : [];
          setProjectFiles(prev => ({
            ...prev,
            [projectId]: files
          }));
        } catch (error) {
          console.error('Failed to fetch project files:', error);
        }
      }
    }
    
    setExpandedProjects(newExpanded);
  };

  // File upload handlers per project
  const handleProjectFileChoose = (projectId, fileList) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    setUploadQueue(prev => ({
      ...prev,
      [projectId]: (prev[projectId] || []).concat(files)
    }));
  };

  const clearProjectUploadQueue = (projectId) => {
    setUploadQueue(prev => {
      const clone = { ...prev };
      delete clone[projectId];
      return clone;
    });
    setUploadProgress(prev => {
      const clone = { ...prev };
      delete clone[projectId];
      return clone;
    });
  };

  // ✅ FIXED: Use the working uploadFiles function
  const handleProjectFileUpload = async (projectId) => {
    const files = uploadQueue[projectId];
    if (!files || files.length === 0) {
      toast.error('Please choose files to upload.');
      return;
    }

    try {
      setUploadingProjectId(projectId);
      setUploadProgress(prev => ({ ...prev, [projectId]: 0 }));

      // ✅ USE YOUR WORKING uploadFiles FUNCTION WITH PROGRESS
      await uploadFiles(projectId, files, {
        onUploadProgress: (evt) => {
          if (!evt.total) return;
          const pct = Math.round((evt.loaded * 100) / evt.total);
          setUploadProgress(prev => ({ ...prev, [projectId]: pct }));
        }
      });

      toast.success(`✅ Uploaded ${files.length} file(s) to project ${projectId}`);

      // Refresh files list for the project
      try {
        const data = await fetchProjectFiles(projectId);
        const refreshed = Array.isArray(data.files) ? data.files : [];
        setProjectFiles(prev => ({ ...prev, [projectId]: refreshed }));
      } catch {
        // ignore refresh failure
      }

      // Clear queue and progress
      clearProjectUploadQueue(projectId);
    } catch (error) {
      console.error('❌ Upload failed:', error);
      toast.error('Upload failed');
    } finally {
      setUploadingProjectId(null);
    }
  };

  // Initialize user and sessions
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const storedToken = localStorage.getItem('token');
        if (!storedToken) {
          navigate('/login');
          return;
        }
        setToken(storedToken);

        const res = await axios.get(`${BACKEND_URL}/users/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
        });
        setUser(res.data);
        
        await loadSessionsFromBackend();
        
      } catch (error) {
        console.error('Error fetching user info:', error);
        toast.error('Session expired. Please log in again.');
        localStorage.removeItem('token');
        navigate('/login');
      }
    };
    fetchUser();
  }, [navigate]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isTyping]);

  // Load projects for sidebar
  useEffect(() => {
    const getProjects = async () => {
      if (!user) return;
      
      setLoadingProjects(true);
      try {
        const data = await fetchProjects();
        
        let projectsData = [];
        if (Array.isArray(data)) {
          projectsData = data;
        } else if (data?.projects && Array.isArray(data.projects)) {
          projectsData = data.projects;
        } else {
          projectsData = [];
        }

        const accessInfo = {};
        projectsData.forEach(project => {
          accessInfo[project.id] = {
            isOwner: project.creator_id === user.id,
            accessType: project.creator_id === user.id ? 'owner' : 'shared',
            creatorEmail: project.creator_email || 'Unknown',
            permissionCount: project.permission_count || 0
          };
        });

        setProjects(projectsData);
        setProjectAccessInfo(accessInfo);
        
      } catch (error) {
        console.error('❌ Error fetching projects:', error);
        setProjects([]);
        setProjectAccessInfo({});
      } finally {
        setLoadingProjects(false);
      }
    };
    
    getProjects();
  }, [user]);

  const simulateTyping = (message, callback) => {
    setIsTyping(true);
    setTimeout(() => {
      try {
        setIsTyping(false);
        callback(message);
      } catch (error) {
        console.error('❌ Error in simulateTyping callback:', error);
        setIsTyping(false);
      }
    }, 800 + Math.random() * 800);
  };

  const handleCreateProject = async () => {
    const name = projectName.trim();
    const description = projectDescription.trim();

    if (!name || !description) {
      toast.error('Please enter both project name and description.');
      return;
    }

    try {
      const res = await createProject(name, description, token);
      
      const newProject = {
        id: res.id || res.project_id || `id_${Date.now()}`,
        name: res.name || res.project_name || name,
        description: res.description || description,
        created_at: res.created_at || new Date().toISOString(),
        creator_id: user?.id,
        creator_email: user?.email,
        permission_count: 0
      };
      
      setProjectAccessInfo(prev => ({
        ...prev,
        [newProject.id]: {
          isOwner: true,
          accessType: 'owner',
          creatorEmail: user?.email,
          permissionCount: 0
        }
      }));
      
      setProjects((prev) => [...prev, newProject]);
      setProjectName('');
      setProjectDescription('');
      setShowProjectCreation(false);
      
      toast.success(`✅ Project "${name}" created successfully!`);
      
    } catch (error) {
      console.error(error);
      toast.error('Failed to create project.');
    }
  };

  // Ask
  const handleAsk = async () => {
    const trimmed = userInput.trim();
    if (!trimmed) return;

    if (!currentSession) {
      await createNewChatSession();
      return;
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: trimmed,
      timestamp: new Date(),
      sessionId: currentSession.id,
    };

    setChatMessages(prev => [...prev, userMessage]);
    setUserInput('');

    try {
      const data = await askQuestionInSession(
        currentSession.id,
        trimmed,
        true,
        selectedFiles,
        selectedProjects.length > 0 ? selectedProjects[0] : null
      );

      if (!data || typeof data.answer === 'undefined') {
        throw new Error('Invalid response from server');
      }

      const answerText = data.answer || 'No answer returned.';
      const hasChartData = data.chartBase64 || data.chartUrl;
      
      simulateTyping(answerText, (message) => {
        const aiMessage = {
          id: data.message_id || `ai-${Date.now()}`,
          sender: 'ai',
          text: message,
          timestamp: new Date(),
          sessionId: currentSession.id,
          contextUsed: data.context_used || false,
          sources: data.sources || [],
          hasChart: data.has_chart || hasChartData,
          chartBase64: data.chartBase64,
          chartUrl: data.chartUrl,
          chartType: data.chart_type
        };
        
        setChatMessages(prev => [...prev, aiMessage]);

        if (hasChartData) {
          toast.success('📊 Chart generated successfully!');
        }

        loadSessionsFromBackend();
      });

    } catch (error) {
      console.error('❌ handleAsk failed:', error);
      
      simulateTyping('❌ Sorry, I encountered an error. Please try again.', (message) => {
        const errorMsg = {
          id: `error-${Date.now()}`,
          sender: 'ai',
          text: message,
          timestamp: new Date(),
          sessionId: currentSession.id,
          contextUsed: false,
        };
        
        setChatMessages(prev => [...prev, errorMsg]);
      });
    }
  };

  // Logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setToken('');
    setAllChatSessions([]);
    setCurrentSession(null);
    setChatMessages([]);
    navigate('/login');
  };

  const getContextStatus = () => {
    if (selectedProjects.length > 0) {
      const projectName = projects.find(p => p.id === selectedProjects[0])?.name;
      return `Project: ${projectName || 'Unknown'} • ${selectedFiles.length} files selected`;
    }
    return "General chat mode • Select a project for document analysis";
  };

  const filteredSessions = allChatSessions.filter(session =>
    session.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoadingSessions) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading your chats...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Toaster position="top-right" />
      
      {/* ChatGPT-Style Layout */}
      <div className="flex h-screen bg-slate-100">
        
        {/* Left Sidebar - Chat Sessions */}
        <div className="w-80 h-full bg-slate-900 text-white flex flex-col">
          {/* Sessions Header */}
          <div className="p-4 border-b border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Chats</h2>
              <button
                onClick={createNewChatSession}
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                title="New Chat"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
            
            {allChatSessions.length > 5 && (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search chats..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto">
            {filteredSessions.length === 0 ? (
              <div className="p-4 text-center text-slate-400">
                <MessageSquarePlus className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No chats yet</p>
                <p className="text-xs mt-1">Create your first chat to get started</p>
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {filteredSessions.map((session) => (
                  <div
                    key={session.id}
                    className={`group relative p-3 rounded-lg cursor-pointer transition-colors ${
                      currentSession?.id === session.id
                        ? 'bg-slate-800 border border-slate-600'
                        : 'hover:bg-slate-800'
                    }`}
                    onClick={() => handleSessionSelect(session)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0 mr-2">
                        {editingSession === session.id ? (
                          <input
                            type="text"
                            value={newSessionTitle}
                            onChange={(e) => setNewSessionTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') finishEditSession(session);
                              if (e.key === 'Escape') {
                                setEditingSession(null);
                                setNewSessionTitle('');
                              }
                            }}
                            onBlur={() => finishEditSession(session)}
                            className="w-full p-1 text-sm bg-slate-700 border border-slate-500 rounded text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                            autoFocus
                          />
                        ) : (
                          <h3 className="font-medium text-sm truncate mb-1">
                            {session.title}
                            <span className="ml-1 text-green-400 text-xs">✓</span>
                          </h3>
                        )}
                        
                        <div className="flex items-center space-x-2 text-xs text-slate-400">
                          <Clock className="w-3 h-3" />
                          <span>{formatTime(new Date(session.updated_at))}</span>
                          {session.message_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{session.message_count} messages</span>
                            </>
                          )}
                        </div>
                      </div>
                      
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              startEditSession(session);
                            }}
                            className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded"
                            title="Rename"
                          >
                            <Edit3 className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm('Delete this chat?')) {
                                handleDeleteSession(session.id);
                              }
                            }}
                            className="p-1 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded"
                            title="Delete"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {currentSession?.id === session.id && (
                      <div className="absolute left-0 top-2 bottom-2 w-1 bg-blue-500 rounded-r-full"></div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content Area - Center */}
        <div className="flex-1 flex flex-col min-w-0">
          
          {/* Header */}
          <div className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-slate-800">
                  {currentSession?.title || 'AI Assistant'}
                  <span className="ml-2 text-green-600 text-sm">✓ Database Synced</span>
                </h1>
                <div className="text-xs text-slate-500">
                  {getContextStatus()}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {user && (
                <div className="flex items-center space-x-2 text-sm">
                  <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                    <User className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-slate-600">{user.email}</span>
                </div>
              )}
              
              <button
                onClick={() => setShowProjectSidebar(!showProjectSidebar)}
                className={`p-2 rounded-lg transition-colors ${
                  showProjectSidebar 
                    ? 'text-blue-600 bg-blue-50' 
                    : 'text-slate-500 hover:bg-slate-100'
                }`}
                title={showProjectSidebar ? 'Hide projects' : 'Show projects'}
              >
                <Folder className="w-5 h-5" />

              </button>
              
              <button
                onClick={handleLogout}
                className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="Logout"
              >
                Logout
              </button>
            </div>
          </div>
          
          {/* Chat Area with scrolling */}
          <div className="flex-1 min-h-0 bg-white flex flex-col">
            <div 
              className="flex-1 overflow-y-auto p-6"
              style={{ maxHeight: 'calc(100vh - 200px)' }}
            >
              {chatMessages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center max-w-md mx-auto p-8">
                    <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Bot className="w-8 h-8 text-white" />
                    </div>
                    <h3 className="text-xl font-semibold text-slate-800 mb-3">Ready to Chat!</h3>
                    <p className="text-slate-600">Start a conversation or select a project to analyze documents.</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-6 max-w-4xl mx-auto">
                  {chatMessages.map((msg, idx) => (
                    <div key={msg.id ?? idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`flex max-w-[80%] ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
                        
                        <div className={`flex-shrink-0 ${msg.sender === 'user' ? 'ml-3' : 'mr-3'}`}>
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                            msg.sender === 'user' 
                              ? 'bg-blue-500 text-white' 
                              : 'bg-slate-200 text-slate-600'
                          }`}>
                            {msg.sender === 'user' ? (
                              <User className="w-4 h-4" />
                            ) : (
                              <Bot className="w-4 h-4" />
                            )}
                          </div>
                        </div>

                        <div className={`max-w-full ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}>
                          <div className={`rounded-2xl px-4 py-3 ${
                            msg.sender === 'user'
                              ? "bg-blue-500 text-white"
                              : "bg-slate-100 text-slate-800"
                          }`}>
                            <div className="whitespace-pre-wrap break-words">
                              {msg.text}
                            </div>
                          </div>
                          
                          {/* Chart display */}
                          {msg.hasChart && (msg.chartBase64 || msg.chartUrl) && (
                            <div className="mt-3 bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center space-x-2 text-sm font-medium text-slate-700">
                                  {getChartIcon(msg.chartType)}
                                  <span>Generated Chart</span>
                                  {msg.chartType && (
                                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full capitalize">
                                      {msg.chartType}
                                    </span>
                                  )}
                                </div>
                                
                                {msg.chartUrl && (
                                  <button
                                    onClick={() => downloadChart(msg.chartUrl, `chart-${Date.now()}.png`)}
                                    className="flex items-center space-x-1 px-2 py-1 text-xs text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                                    title="Download Chart"
                                  >
                                    <Download className="w-3 h-3" />
                                    <span>Download</span>
                                  </button>
                                )}
                              </div>
                              
                              <div className="relative">
                                {msg.chartBase64 ? (
                                  <img 
                                    src={`data:image/png;base64,${msg.chartBase64}`}
                                    alt="Generated Chart"
                                    className="w-full h-auto rounded-lg border border-slate-200 shadow-sm"
                                    style={{ maxHeight: '400px', objectFit: 'contain' }}
                                  />
                                ) : msg.chartUrl ? (
                                  <img 
                                    src={`${BACKEND_URL}${msg.chartUrl}`}
                                    alt="Generated Chart"
                                    className="w-full h-auto rounded-lg border border-slate-200 shadow-sm"
                                    style={{ maxHeight: '400px', objectFit: 'contain' }}
                                    onError={(e) => {
                                      e.target.style.display = 'none';
                                      e.target.nextSibling.style.display = 'flex';
                                    }}
                                  />
                                ) : null}
                                
                                <div 
                                  className="hidden items-center justify-center h-32 bg-slate-50 border border-slate-200 rounded-lg text-slate-500"
                                >
                                  <div className="text-center">
                                    <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">Chart could not be loaded</p>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                          
                          <div className={`mt-1 text-xs text-slate-500 ${
                            msg.sender === 'user' ? 'text-right' : 'text-left'
                          }`}>
                            {formatTime(msg.timestamp)}
                            {msg.contextUsed && (
                              <span className="ml-2 text-green-600">• Context used</span>
                            )}
                            {msg.hasChart && (
                              <span className="ml-2 text-purple-600">• Chart generated</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {isTyping && (
                    <div className="flex justify-start">
                      <div className="flex items-center space-x-2 bg-slate-100 rounded-2xl px-4 py-3">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span className="text-slate-600 text-sm">AI is thinking...</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div ref={chatEndRef} />
          </div>
          
          {/* Chat Input */}
          <div className="bg-white border-t border-slate-200 p-4">
            <div className="max-w-4xl mx-auto">
              {selectedFiles.length > 0 && (
                <div className="mb-3 flex items-center space-x-2">
                  <div className="text-xs text-slate-600">Analyzing files:</div>
                  <div className="flex flex-wrap gap-1">
                    {selectedFiles.slice(0, 3).map(fileName => (
                      <span key={fileName} className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                        📄 {fileName}
                      </span>
                    ))}
                    {selectedFiles.length > 3 && (
                      <span className="text-xs text-slate-500">+{selectedFiles.length - 3} more</span>
                    )}
                  </div>
                </div>
              )}
              
              <div className="flex items-end space-x-3">
                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleAsk();
                      }
                    }}
                    placeholder={
                      selectedProjects.length > 0 
                        ? `Ask about your documents${selectedFiles.length > 0 ? ' in selected files' : ''}...`
                        : "Ask me anything, or select a project to analyze documents..."
                    }
                    className="w-full resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-50 transition-all duration-200 shadow-sm"
                    disabled={isTyping}
                    rows={1}
                    style={{ minHeight: '48px', maxHeight: '120px' }}
                  />
                </div>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleEnhanceQuery}
                    disabled={!userInput.trim() || isEnhancing}
                    className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 transition-all duration-200 shadow-sm"
                    title="Enhance query"
                  >
                    {isEnhancing ? (
                      <div className="animate-spin">
                        <Sparkles className="w-5 h-5" />
                      </div>
                    ) : (
                      <Sparkles className="w-5 h-5" />
                    )}
                  </button>
                  
                  <button
                    onClick={handleAsk}
                    disabled={!userInput.trim() || isTyping || !currentSession}
                    className="p-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 transition-all duration-200 shadow-sm"
                    title="Send message"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT SIDEBAR - PROJECTS */}
        {showProjectSidebar && (
          <div className="w-80 h-full bg-white border-l border-slate-200 flex flex-col">
            <div className="p-4 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-slate-800">Projects</h2>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setShowProjectCreation(!showProjectCreation)}
                    className="p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    title="Create new project"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setShowProjectSidebar(false)}
                    className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-md transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {showProjectCreation && (
                <div className="p-4 bg-blue-50 border-b border-blue-200">
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={projectName}
                      onChange={(e) => setProjectName(e.target.value)}
                      placeholder="Enter project name..."
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                    <textarea
                      value={projectDescription}
                      onChange={(e) => setProjectDescription(e.target.value)}
                      placeholder="Enter project description..."
                      rows={3}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={handleCreateProject}
                      disabled={!projectName.trim() || !projectDescription.trim()}
                      className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors"
                    >
                      Create Project
                    </button>
                  </div>
                </div>
              )}

              {user && (
                <div className="text-xs text-slate-600 bg-white rounded px-2 py-1">
                  <span className="font-medium">{user.email}</span>
                  <span className="ml-2 text-slate-500 capitalize">({user.role})</span>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="p-4">
                <div className="mb-4 p-3 bg-slate-50 rounded-lg">
                  <div className="text-sm font-medium text-slate-700 mb-2">Selection Status</div>
                  <div className="text-xs text-slate-600">
                    {selectedProjects.length > 0 ? (
                      <div>
                        <div>✓ {selectedProjects.length} project(s) selected</div>
                        <div>✓ {selectedFiles.length} file(s) selected</div>
                        <div className="mt-1 text-green-600">Enhanced context active</div>
                      </div>
                    ) : (
                      <div>
                        <div>○ No projects selected</div>
                        <div className="mt-1 text-blue-600">General chat mode active</div>
                      </div>
                    )}
                  </div>
                </div>

                {loadingProjects ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  </div>
                ) : projects.length === 0 ? (
                  <div className="text-center py-8">
                    <Folder className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                    <p className="text-sm text-slate-600">No projects yet</p>
                    <p className="text-xs text-slate-500">Create your first project to get started</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {projects.map((proj) => {
                      const projectId = proj.project_id || proj.id;
                      const name = proj.project_name || proj.name || "Unnamed Project";
                      const isSelected = selectedProjects.includes(projectId);
                      const isExpanded = expandedProjects.has(projectId);
                      const files = projectFiles[projectId] || [];
                      const queue = uploadQueue[projectId] || [];
                      const pct = uploadProgress[projectId] || 0;
                      const isUploading = uploadingProjectId === projectId;
                      
                      return (
                        <div key={projectId} className="border border-slate-200 rounded-lg">
                          <div className="p-3">
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => toggleProjectExpansion(projectId)}
                                className="p-1 hover:bg-slate-100 rounded transition-colors"
                              >
                                {isExpanded ? (
                                  <ChevronDown className="w-4 h-4 text-slate-500" />
                                ) : (
                                  <ChevronRight className="w-4 h-4 text-slate-500" />
                                )}
                              </button>
                              
                              <label className="flex items-center space-x-2 cursor-pointer flex-1">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleProject(projectId)}
                                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                                />
                                
                                {isExpanded ? (
                                  <FolderOpen className="w-4 h-4 text-blue-500 flex-shrink-0" />
                                ) : (
                                  <Folder className="w-4 h-4 text-blue-500 flex-shrink-0" />
                                )}
                                
                                <div className="flex-1 min-w-0">
                                  <div className="text-sm font-medium text-slate-700 truncate">
                                    {name}
                                  </div>
                                  <div className="text-xs text-slate-500 mt-1">
                                    ID: {projectId}
                                  </div>
                                </div>
                              </label>
                            </div>
                          </div>

                          {isExpanded && (
                            <div className="border-t border-slate-200 bg-slate-50 p-3 space-y-3">
                              {/* Upload UI */}
                              <div className="bg-white border border-slate-200 rounded-md p-3">
                                <div className="flex items-center justify-between">
                                  <div className="text-sm font-medium text-slate-700">Upload files</div>
                                  {queue.length > 0 && (
                                    <button
                                      className="text-xs text-slate-500 hover:text-slate-700"
                                      onClick={() => clearProjectUploadQueue(projectId)}
                                    >
                                      Clear selection
                                    </button>
                                  )}
                                </div>
                                <div className="mt-2 flex items-center space-x-2">
                                  <label className="inline-flex items-center px-3 py-2 text-sm bg-white border border-slate-300 rounded-md shadow-sm hover:bg-slate-50 cursor-pointer">
                                    <Upload className="w-4 h-4 mr-2 text-slate-600" />
                                    Choose files
                                    <input
                                      type="file"
                                      multiple
                                      className="hidden"
                                      onChange={(e) => handleProjectFileChoose(projectId, e.target.files)}
                                    />
                                  </label>

                                  <button
                                    onClick={() => handleProjectFileUpload(projectId)}
                                    disabled={queue.length === 0 || isUploading}
                                    className={`inline-flex items-center px-3 py-2 text-sm rounded-md text-white shadow-sm ${
                                      queue.length === 0 || isUploading
                                        ? 'bg-slate-300 cursor-not-allowed'
                                        : 'bg-blue-600 hover:bg-blue-700'
                                    }`}
                                  >
                                    {isUploading ? (
                                      <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                                        Uploading... {pct}%
                                      </>
                                    ) : (
                                      <>
                                        <Upload className="w-4 h-4 mr-2" />
                                        Upload
                                      </>
                                    )}
                                  </button>
                                </div>

                                {queue.length > 0 && (
                                  <div className="mt-2 text-xs text-slate-600">
                                    {queue.length} file(s) selected
                                  </div>
                                )}

                                {isUploading && (
                                  <div className="mt-3">
                                    <div className="w-full bg-slate-200 h-2 rounded">
                                      <div
                                        className="bg-blue-600 h-2 rounded"
                                        style={{ width: `${pct}%` }}
                                      ></div>
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Files list */}
<div>
  <div className="text-xs font-medium text-slate-600 mb-2 flex items-center justify-between">
    <span>Files</span>

    {/* 🔥 Select All button */}
    {files.length > 0 && (
      <button
        onClick={() => {
          const all = files.map(f => f.name || f.file_name);
          const alreadyAllSelected = all.every(f => selectedFiles.includes(f));

          if (alreadyAllSelected) {
            // Deselect all
            setSelectedFiles([]);
          } else {
            // Select all
            setSelectedFiles(all);
          }
        }}
        className="text-[10px] text-blue-600 hover:underline"
      >
        {(() => {
          const all = files.map(f => f.name || f.file_name);
          return all.every(f => selectedFiles.includes(f)) ? "Deselect All" : "Select All";
        })()}
      </button>
    )}
  </div>

  {files.length === 0 ? (
    <div className="text-center py-4 bg-white border border-slate-200 rounded-md">
      <FileX className="w-8 h-8 mx-auto mb-2 text-slate-300" />
      <p className="text-xs text-slate-500">No files uploaded</p>
    </div>
  ) : (
    <div className="space-y-1 max-h-[75vh] overflow-y-auto bg-white border border-slate-200 rounded-md p-2">
      {files.map((file, index) => {
        const fileName = file.name || file.file_name || `File ${index + 1}`;
        const isFileSelected = selectedFiles.includes(fileName);

        return (
          <label key={file.file_id || fileName} className="flex items-center space-x-2 p-2 hover:bg-slate-50 rounded cursor-pointer">
            <input
              type="checkbox"
              checked={isFileSelected}
              onChange={() => toggleFile(fileName)}
              className="w-3 h-3 text-blue-600 rounded"
            />
            {getFileIcon(fileName)}

            <div className="flex-1 min-w-0">
              {/* Tooltip on hover full filename */}
              <div className="text-xs font-medium text-slate-700 truncate" title={fileName}>
                {fileName}
              </div>
            </div>
          </label>
        );
      })}
    </div>
  )}
</div>


                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default HomePage;
