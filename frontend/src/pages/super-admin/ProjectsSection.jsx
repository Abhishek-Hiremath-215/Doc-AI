import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";

// Test component for API connectivity
const TestProjectFiles = ({ projectId = 1 }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const testAbsoluteUrl = async () => {
    setLoading(true);
    setResult(null);

    try {
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');

      // Use absolute URL to bypass proxy issues
      const response = await fetch(`http://localhost:8000/projects/${projectId}/files`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      const text = await response.text();
      console.log('Response text:', text);

      if (text.startsWith('<!DOCTYPE') || text.startsWith('<html')) {
        setResult({ error: 'Received HTML instead of JSON', html: text.substring(0, 200) + '...' });
      } else {
        const data = JSON.parse(text);
        setResult({ success: true, data });
      }

    } catch (error) {
      console.error('Test error:', error);
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  const testRelativeUrl = async () => {
    setLoading(true);
    setResult(null);

    try {
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');

      // Use relative URL (through proxy)
      const response = await fetch(`/projects/${projectId}/files`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
      });

      console.log('Response status:', response.status);
      const text = await response.text();
      console.log('Response text:', text);

      if (text.startsWith('<!DOCTYPE') || text.startsWith('<html')) {
        setResult({ error: 'Received HTML instead of JSON (Proxy Issue)', html: text.substring(0, 200) + '...' });
      } else {
        const data = JSON.parse(text);
        setResult({ success: true, data });
      }

    } catch (error) {
      console.error('Test error:', error);
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-4">
      <h3 className="font-bold text-yellow-800 mb-3">🧪 API Connection Test</h3>

      <div className="flex gap-2 mb-4">
        <button
          onClick={testAbsoluteUrl}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          Test Direct Backend (localhost:8000)
        </button>
        <button
          onClick={testRelativeUrl}
          disabled={loading}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          Test Through Proxy (/api)
        </button>
      </div>

      {loading && <p className="text-blue-600">Testing...</p>}

      {result && (
        <div className="mt-4 p-3 border rounded">
          {result.success ? (
            <div className="text-green-600">
              <p className="font-bold">✅ Success!</p>
              <pre className="text-xs mt-2 bg-green-50 p-2 rounded overflow-x-auto">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="text-red-600">
              <p className="font-bold">❌ Failed: {result.error}</p>
              {result.html && (
                <pre className="text-xs mt-2 bg-red-50 p-2 rounded overflow-x-auto">
                  {result.html}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// File viewer modal component
const FileViewerModal = ({ file, projectId, projectName, onClose }) => {
  // Helper function to generate authenticated file URLs
  const getAuthenticatedFileUrl = (projectId, filename) => {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    const safeName = encodeURIComponent(filename);
    return token
      ? `http://localhost:8000/projects/${projectId}/files/${safeName}?token=${token}`
      : `http://localhost:8000/projects/${projectId}/files/${safeName}`;
  };

  const getFileIcon = (fileName) => {
    const extension = fileName.split('.').pop().toLowerCase();
    const iconMap = {
      pdf: "📄",
      doc: "📝", docx: "📝",
      xls: "📊", xlsx: "📊",
      ppt: "📊", pptx: "📊",
      txt: "📄",
      jpg: "🖼️", jpeg: "🖼️", png: "🖼️", gif: "🖼️", webp: "🖼️",
      mp4: "🎥", avi: "🎥", mov: "🎥", mkv: "🎥",
      mp3: "🎵", wav: "🎵", flac: "🎵",
      zip: "📦", rar: "📦", tar: "📦", gz: "📦",
      csv: "📊", json: "📄", xml: "📄",
      py: "🐍", js: "📜", jsx: "⚛️", ts: "📘", tsx: "⚛️",
      html: "🌐", css: "🎨", scss: "🎨",
    };
    return iconMap[extension] || "📄";
  };

  const renderFileContent = () => {
    const extension = file.name.split('.').pop().toLowerCase();
    const fileUrl = getAuthenticatedFileUrl(projectId, file.name);

    // For images
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(extension)) {
      return (
        <div className="flex justify-center">
          <img 
            src={fileUrl} 
            alt={file.name}
            className="max-w-full max-h-96 object-contain rounded-lg shadow-md"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'block';
            }}
          />
          <div className="hidden text-center py-8">
            <div className="text-6xl mb-4">🖼️</div>
            <p className="text-gray-600 mb-4">Failed to load image</p>
            <a
              href={fileUrl}
              download={file.name}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              📥 Download Image
            </a>
          </div>
        </div>
      );
    }

    // For PDFs
 // For PDFs - FIXED VERSION
if (extension === 'pdf') {
  return (
    <div className="text-center py-8">
      <div className="text-6xl mb-4">📄</div>
      <p className="text-gray-600 mb-4">{file.name}</p>
      <p className="text-sm text-gray-500 mb-6">Click below to view the PDF</p>
      <div className="space-y-2">
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 mr-2"
        >
          🔗 Open PDF in New Tab
        </a>
        <a
          href={fileUrl}
          download={file.name}
          className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
        >
          📥 Download PDF
        </a>
      </div>
    </div>
  );
}


    // For videos
    if (['mp4', 'webm', 'ogg', 'avi', 'mov', 'mkv'].includes(extension)) {
      return (
        <div className="flex justify-center">
          <video 
            controls 
            className="max-w-full max-h-96 rounded-lg shadow-md"
            src={fileUrl}
            onError={() => {
              toast.error('Failed to load video');
            }}
          >
            Your browser does not support the video tag.
          </video>
        </div>
      );
    }

    // For audio files
    if (['mp3', 'wav', 'ogg', 'flac', 'm4a'].includes(extension)) {
      return (
        <div className="text-center py-8">
          <div className="text-6xl mb-4">🎵</div>
          <audio controls className="w-full max-w-md mx-auto mb-4">
            <source src={fileUrl} type={`audio/${extension}`} />
            Your browser does not support the audio tag.
          </audio>
          <p className="text-gray-600">{file.name}</p>
        </div>
      );
    }

    // For text files and code
    if (['txt', 'md', 'json', 'xml', 'csv', 'log', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css'].includes(extension)) {
      const [textContent, setTextContent] = useState('Loading...');

      useEffect(() => {
        fetch(fileUrl)
          .then(response => {
            if (!response.ok) throw new Error('Failed to load file');
            return response.text();
          })
          .then(text => setTextContent(text))
          .catch(() => setTextContent('Failed to load file content'));
      }, [fileUrl]);

      return (
        <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto border">
          <pre className="whitespace-pre-wrap text-sm font-mono">
            {textContent}
          </pre>
        </div>
      );
    }

    // For Office documents (Word, Excel, PowerPoint)
    if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(extension)) {
      return (
        <div className="text-center py-8">
          <div className="text-6xl mb-4">{getFileIcon(file.name)}</div>
          <p className="text-gray-600 mb-4">Office document preview not available in browser</p>
          <div className="space-y-2">
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 mr-2"
            >
              👁️ Open in New Tab
            </a>
            <a
              href={fileUrl}
              download={file.name}
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              📥 Download to View
            </a>
          </div>
        </div>
      );
    }

    // Default fallback for unsupported files
    return (
      <div className="text-center py-8">
        <div className="text-6xl mb-4">{getFileIcon(file.name)}</div>
        <p className="text-gray-600 mb-2">Preview not available for this file type</p>
        <p className="text-sm text-gray-500 mb-4">File: {file.name}</p>
        <div className="space-y-2">
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 mr-2"
          >
            🔗 Open in New Tab
          </a>
          <a
            href={fileUrl}
            download={file.name}
            className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            📥 Download File
          </a>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-5xl w-full max-h-[95vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b bg-gray-50">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              {getFileIcon(file.name)} {file.name}
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Size: {file.size_kb} KB • 
              Type: {file.type.toUpperCase()} • 
              Project: {projectName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-3xl font-bold leading-none p-2 hover:bg-gray-100 rounded-full"
            title="Close"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(95vh-180px)]">
          {renderFileContent()}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-500">
            File size: {file.size_kb} KB • Type: {file.type || 'Unknown'}
          </div>
          <div className="flex gap-2">
            <a
              href={getAuthenticatedFileUrl(projectId, file.name)}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              🔗 Open in New Tab
            </a>
            <a
              href={getAuthenticatedFileUrl(projectId, file.name)}
              download={file.name}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
            >
              📥 Download
            </a>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// File list component for a project
const ProjectFilesList = ({ project, files, onFileClick, onRefresh, isLoading }) => {
  // Helper function to generate authenticated file URLs
  const getAuthenticatedFileUrl = (projectId, filename) => {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    const safeName = encodeURIComponent(filename);
    return token
      ? `http://localhost:8000/projects/${projectId}/files/${safeName}?token=${token}`
      : `http://localhost:8000/projects/${projectId}/files/${safeName}`;
  };

  const getFileIcon = (fileName) => {
    const extension = fileName.split('.').pop().toLowerCase();
    const iconMap = {
      pdf: "📄",
      doc: "📝", docx: "📝",
      xls: "📊", xlsx: "📊",
      ppt: "📊", pptx: "📊",
      txt: "📄", md: "📄",
      jpg: "🖼️", jpeg: "🖼️", png: "🖼️", gif: "🖼️", webp: "🖼️",
      mp4: "🎥", avi: "🎥", mov: "🎥", mkv: "🎥",
      mp3: "🎵", wav: "🎵", flac: "🎵",
      zip: "📦", rar: "📦", tar: "📦", gz: "📦",
      csv: "📊", json: "📄", xml: "📄",
      py: "🐍", js: "📜", jsx: "⚛️", ts: "📘", tsx: "⚛️",
      html: "🌐", css: "🎨", scss: "🎨",
    };
    return iconMap[extension] || "📄";
  };

  const formatFileSize = (sizeKb) => {
    if (!sizeKb || sizeKb === 0) return 'Unknown size';

    if (sizeKb >= 1024) {
      return `${(sizeKb / 1024).toFixed(1)} MB`;
    }
    return `${sizeKb} KB`;
  };

  const getFileTypeColor = (fileType) => {
    const colorMap = {
      pdf: "text-red-600 bg-red-50",
      doc: "text-blue-600 bg-blue-50", docx: "text-blue-600 bg-blue-50",
      xls: "text-green-600 bg-green-50", xlsx: "text-green-600 bg-green-50",
      ppt: "text-orange-600 bg-orange-50", pptx: "text-orange-600 bg-orange-50",
      jpg: "text-purple-600 bg-purple-50", jpeg: "text-purple-600 bg-purple-50", 
      png: "text-purple-600 bg-purple-50", gif: "text-purple-600 bg-purple-50",
      mp4: "text-pink-600 bg-pink-50", avi: "text-pink-600 bg-pink-50",
      mp3: "text-indigo-600 bg-indigo-50", wav: "text-indigo-600 bg-indigo-50",
      py: "text-yellow-600 bg-yellow-50", js: "text-yellow-600 bg-yellow-50",
      txt: "text-gray-600 bg-gray-50", md: "text-gray-600 bg-gray-50",
    };
    return colorMap[fileType.toLowerCase()] || "text-gray-600 bg-gray-50";
  };

  return (
    <div className="mt-4 border-t pt-4">
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-sm font-medium text-gray-700 flex items-center">
          📁 Project Files 
          <span className="ml-2 px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs">
            {files.length}
          </span>
        </h4>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 flex items-center"
        >
          <span className={isLoading ? "animate-spin" : ""}>🔄</span>
          <span className="ml-1">{isLoading ? 'Loading...' : 'Refresh'}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-6">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-sm text-gray-500">Loading project files...</p>
        </div>
      ) : files.length === 0 ? (
        <div className="text-center py-6 text-gray-500 text-sm bg-gray-50 rounded-lg">
          <div className="text-3xl mb-2">📂</div>
          <p className="font-medium">No files in this project</p>
          <p className="text-xs mt-1">Files will appear here once uploaded</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
          {files.map((file, index) => (
            <div
              key={file.name + index}
              className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 cursor-pointer transition-all duration-200 hover:shadow-sm"
              onClick={() => onFileClick(file)}
            >
              <div className="flex items-center flex-1 min-w-0">
                <div className={`p-2 rounded-md mr-3 ${getFileTypeColor(file.type)}`}>
                  <span className="text-lg">{getFileIcon(file.name)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate" title={file.name}>
                    {file.name}
                  </p>
                  <div className="flex items-center text-xs text-gray-500 mt-1">
                    <span>{formatFileSize(file.size_kb)}</span>
                    <span className="mx-2">•</span>
                    <span className="uppercase">{file.type || 'Unknown'}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-1 ml-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onFileClick(file);
                  }}
                  className="p-2 text-blue-600 hover:bg-blue-100 rounded-md text-sm transition-colors"
                  title="View file"
                >
                  👁️
                </button>
                <a
                  href={getAuthenticatedFileUrl(project.id, file.name)}
                  download={file.name}
                  onClick={(e) => e.stopPropagation()}
                  className="p-2 text-green-600 hover:bg-green-100 rounded-md text-sm transition-colors"
                  title="Download file"
                >
                  📥
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Main Projects Section Component
const ProjectsSection = ({
  projects,
  users,
  loadingProjects,
  loadProjects,
  assigning,
  handleAssignProject,
  handleManageProjectAccess
}) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedProjectName, setSelectedProjectName] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [showFileViewer, setShowFileViewer] = useState(false);
  const [projectFiles, setProjectFiles] = useState({});
  const [loadingFiles, setLoadingFiles] = useState({});
  const [expandedProjects, setExpandedProjects] = useState(new Set());

  // Function to fetch project files from your existing backend API
  const fetchProjectFiles = async (project) => {
    setLoadingFiles(prev => ({ ...prev, [project.id]: true }));
    try {
      console.log(`📁 Fetching files for project ${project.id}: ${project.name}`);

      const token = localStorage.getItem('token') || localStorage.getItem('access_token');
      console.log(`🔑 Token available: ${token ? 'Yes' : 'No'}`);

      // Try absolute URL first to bypass proxy issues
      const response = await fetch(`http://localhost:8000/projects/${project.id}/files`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
      });

      console.log(`📥 Response status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log(`✅ Loaded ${data.files.length} files for project ${project.name}`);

      // Your API returns { files: [...], project_name: "..." }
      setProjectFiles(prev => ({
        ...prev,
        [project.id]: data.files || []
      }));

    } catch (error) {
      console.error('Error fetching project files:', error);
      toast.error(`Failed to load files for ${project.name}: ${error.message}`);
      setProjectFiles(prev => ({
        ...prev,
        [project.id]: []
      }));
    } finally {
      setLoadingFiles(prev => ({ ...prev, [project.id]: false }));
    }
  };

  const handleFileClick = (file, projectId, projectName) => {
    setSelectedFile(file);
    setSelectedProjectId(projectId);
    setSelectedProjectName(projectName);
    setShowFileViewer(true);
  };

  const handleToggleProject = (project) => {
    const newExpanded = new Set(expandedProjects);
    if (newExpanded.has(project.id)) {
      newExpanded.delete(project.id);
    } else {
      newExpanded.add(project.id);
      // Load files when expanding
      if (!projectFiles[project.id] && !loadingFiles[project.id]) {
        fetchProjectFiles(project);
      }
    }
    setExpandedProjects(newExpanded);
  };

  const handleRefreshFiles = (project) => {
    fetchProjectFiles(project);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Projects Management</h2>
        <div className="flex gap-2">
         
    
          <button 
            onClick={loadProjects}
            className="px-4 py-2 bg-blue-500 text-white rounded-md text-sm hover:bg-blue-600 disabled:opacity-50 transition-colors"
            disabled={loadingProjects}
          >
            {loadingProjects ? (
              <>
                <span className="animate-spin inline-block mr-2">🔄</span>
                Refreshing...
              </>
            ) : (
              'Refresh Projects'
            )}
          </button>
        </div>
      </div>

      {/* Debug Mode */}

      <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6 rounded-r-lg">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className="text-xl">ℹ️</span>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              <strong>SuperAdmin Project Management:</strong> You can assign projects to users, grant access permissions, and revoke assignments. 
              Click project names to expand and view files. Use "Manage Access" for detailed permissions.
            </p>
          </div>
        </div>
      </div>

      {loadingProjects ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading projects...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg">
          <div className="text-6xl mb-4">📂</div>
          <p className="text-lg font-medium mb-2">No projects found</p>
          <p className="text-sm mb-4">Create a project to get started</p>
          <button 
            onClick={loadProjects}
            className="px-6 py-3 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => {
            const isExpanded = expandedProjects.has(project.id);
            const files = projectFiles[project.id] || [];
            const isLoadingFiles = loadingFiles[project.id];

            return (
              <div 
                key={project.id} 
                className={`border border-gray-200 rounded-xl p-5 hover:shadow-lg transition-all duration-300 ${
                  isExpanded ? 'shadow-lg ring-2 ring-blue-100' : 'hover:shadow-md'
                }`}
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 
                    className="text-lg font-semibold text-gray-900 flex-1 cursor-pointer hover:text-blue-600 transition-colors flex items-center"
                    onClick={() => handleToggleProject(project)}
                    title="Click to view files"
                  >
                    <span className="mr-2 text-xl">
                      {isExpanded ? '📂' : '📁'}
                    </span>
                    {project.name}
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleToggleProject(project)}
                      className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-md hover:bg-gray-200 transition-colors"
                      title={isExpanded ? "Collapse" : "View Files"}
                    >
                      {isExpanded ? '▼' : '▶'}
                    </button>
                    <button
                      onClick={() => handleManageProjectAccess(project)}
                      className="px-3 py-1 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600 transition-colors"
                    >
                      Manage Access
                    </button>
                  </div>
                </div>

                {project.description && (
                  <p className="text-sm text-gray-600 mb-4 leading-relaxed">{project.description}</p>
                )}

                <div className="text-xs text-gray-500 space-y-2 mb-4 bg-gray-50 p-3 rounded-lg">
                  <p><strong>Owner:</strong> {project.creator_email || 'Unknown'}</p>
                  <p><strong>Organization:</strong> {project.organization?.name || project.organization_name || 'No organization'}</p>
                  <p><strong>Users with access:</strong> {project.permission_count || 0}</p>
                  <p><strong>Created:</strong> {new Date(project.created_at).toLocaleDateString()}</p>
                </div>

                {/* Project Files Section */}
                {isExpanded && (
                  <ProjectFilesList
                    project={project}
                    files={files}
                    onFileClick={(file) => handleFileClick(file, project.id, project.name)}
                    onRefresh={() => handleRefreshFiles(project)}
                    isLoading={isLoadingFiles}
                  />
                )}

                {/* Quick Assignment functionality - only show when not expanded */}
                {!isExpanded && (
                  <div className="border-t pt-4 mt-4">
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Quick Transfer Ownership:
                    </label>
                    <select 
                      id={`assign-user-${project.id}`}
                      className="w-full text-xs border border-gray-300 rounded-md px-3 py-2 mb-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      defaultValue=""
                    >
                      <option value="" disabled>Select new owner...</option>
                      {users
                        .filter(u => u.id !== project.creator_id)
                        .map(user => (
                          <option key={user.id} value={user.id}>
                            {user.email} ({user.role})
                            {user.organization?.name && ` - ${user.organization.name}`}
                          </option>
                        ))
                      }
                    </select>
                    <button
                      onClick={() => {
                        const select = document.getElementById(`assign-user-${project.id}`);
                        const selectedUserId = select.value;
                        if (!selectedUserId) {
                          toast.error('Please select a user to assign');
                          return;
                        }
                        handleAssignProject(project.id, selectedUserId);
                      }}
                      disabled={assigning[project.id]}
                      className="w-full px-4 py-2 bg-orange-600 text-white rounded-md text-sm hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {assigning[project.id] ? (
                        <>
                          <span className="animate-spin inline-block mr-2">🔄</span>
                          Transferring...
                        </>
                      ) : (
                        'Quick Transfer'
                      )}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* File Viewer Modal */}
      {showFileViewer && selectedFile && (
        <FileViewerModal
          file={selectedFile}
          projectId={selectedProjectId}
          projectName={selectedProjectName}
          onClose={() => {
            setShowFileViewer(false);
            setSelectedFile(null);
            setSelectedProjectId(null);
            setSelectedProjectName('');
          }}
        />
      )}
    </div>
  );
};

export default ProjectsSection;