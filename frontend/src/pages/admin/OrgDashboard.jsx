import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import Header from "../../components/Header";
import {
  fetchUsers,
  fetchProjects,
  toggleUserActive,
  deleteUser,
  registerUser,
  listOrganizations,
  getProjectPermissions,
  getAvailableUsersForProject,
  grantProjectAccess,
  revokeProjectAccess,
  getAssignedUsers,
  assignProjectToUser,
} from "../../services/api";
import { toast } from "react-hot-toast";

// ✅ File viewing components from ProjectsSection.jsx

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

// Simple File List Modal (for viewing project files)
const ProjectFilesModal = ({ project, onClose }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showFileViewer, setShowFileViewer] = useState(false);

  useEffect(() => {
    loadProjectFiles();
  }, [project.id]);

  const loadProjectFiles = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('token') || localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/projects/${project.id}/files`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setFiles(data.files || []);
    } catch (err) {
      console.error('Error loading project files:', err);
      setError(err.message);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileClick = (file) => {
    setSelectedFile(file);
    setShowFileViewer(true);
  };

  const getFileIcon = (fileName) => {
    const extension = fileName.split('.').pop().toLowerCase();
    const iconMap = {
      pdf: "📄", doc: "📝", docx: "📝", xls: "📊", xlsx: "📊", ppt: "📊", pptx: "📊",
      txt: "📄", jpg: "🖼️", jpeg: "🖼️", png: "🖼️", gif: "🖼️", webp: "🖼️",
      mp4: "🎥", avi: "🎥", mov: "🎥", mp3: "🎵", wav: "🎵", flac: "🎵",
      zip: "📦", rar: "📦", py: "🐍", js: "📜", jsx: "⚛️", html: "🌐", css: "🎨",
    };
    return iconMap[extension] || "📄";
  };

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <div className="flex justify-between items-center p-6 border-b">
            <div>
              <h3 className="text-xl font-bold text-gray-800">Project Files</h3>
              <p className="text-sm text-gray-600">{project.name}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
            >
              ×
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin text-4xl mb-4">⏳</div>
                <div className="text-gray-600">Loading project files...</div>
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-600">
                <div className="text-4xl mb-4">❌</div>
                <div>Error: {error}</div>
                <button
                  onClick={loadProjectFiles}
                  className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Retry
                </button>
              </div>
            ) : files.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-4">📂</div>
                <div>No files in this project</div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="border rounded-lg p-4 hover:shadow-md cursor-pointer transition-shadow"
                    onClick={() => handleFileClick(file)}
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-2">{getFileIcon(file.name)}</div>
                      <div className="text-sm font-medium text-gray-900 truncate" title={file.name}>
                        {file.name}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {file.size_kb} KB • {file.type?.toUpperCase() || 'Unknown'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border-t p-4 bg-gray-50">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {/* File Viewer Modal */}
      {showFileViewer && selectedFile && (
        <FileViewerModal
          file={selectedFile}
          projectId={project.id}
          projectName={project.name}
          onClose={() => {
            setShowFileViewer(false);
            setSelectedFile(null);
          }}
        />
      )}
    </>
  );
};

// ✅ Enhanced Project Management Modal (same as SuperAdminDashboard)
const ProjectManagementModal = ({ project, users = [], onClose, onRefresh }) => {
  const [allUsersWithAccess, setAllUsersWithAccess] = useState([]);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [selectedUserForAccess, setSelectedUserForAccess] = useState('');
  const [selectedUserForTransfer, setSelectedUserForTransfer] = useState('');
  const [loading, setLoading] = useState(true);
  const [isGranting, setIsGranting] = useState(false);
  const [isTransferring, setIsTransferring] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAllAccessData();
  }, [project.id, users]);

  const loadAllAccessData = async () => {
    try {
      setLoading(true);
      setError('');

      console.log('🔍 Loading access data for project:', project.name);

      // Fetch from BOTH APIs to get complete user access data
      const [permissionsResult, assignedResult] = await Promise.all([
        getProjectPermissions(project.id).catch((err) => {
          console.log('⚠️ Permissions API failed:', err);
          return { permissions: [] };
        }),
        getAssignedUsers(project.id).catch((err) => {
          console.log('⚠️ Assigned users API failed:', err);
          return { assigned_users: [] };
        })
      ]);

      console.log('📊 Permissions API response:', permissionsResult);
      console.log('📊 Assigned users API response:', assignedResult);

      // Create a comprehensive map of all users with access
      const usersWithAccessMap = new Map();

      // Add users from permissions API
      if (permissionsResult.permissions && Array.isArray(permissionsResult.permissions)) {
        permissionsResult.permissions.forEach(permission => {
          const userInfo = users.find(u => u.id === permission.user_id) || {};
          usersWithAccessMap.set(permission.user_id, {
            user_id: permission.user_id,
            user_email: permission.user_email,
            user_role: userInfo.role || 'user',
            organization_name: userInfo.organization?.name || 'No Organization',
            granted_by: permission.granted_by,
            granted_at: permission.granted_at,
            access_type: permission.user_id === project.creator_id ? 'owner' : 'permission'
          });
        });
      }

      // Add users from assigned API (additional source)
      if (assignedResult.assigned_users && Array.isArray(assignedResult.assigned_users)) {
        assignedResult.assigned_users.forEach(assigned => {
          if (!usersWithAccessMap.has(assigned.user_id)) {
            const userInfo = users.find(u => u.id === assigned.user_id) || {};
            usersWithAccessMap.set(assigned.user_id, {
              user_id: assigned.user_id,
              user_email: assigned.user_email,
              user_role: assigned.user_role || userInfo.role || 'user',
              organization_name: userInfo.organization?.name || 'No Organization',
              granted_by: assigned.assigned_by || 'System',
              granted_at: assigned.assigned_at || assigned.granted_at,
              access_type: assigned.user_id === project.creator_id ? 'owner' : 'assigned'
            });
          }
        });
      }

      // Always ensure project owner is included
      if (!usersWithAccessMap.has(project.creator_id)) {
        const ownerInfo = users.find(u => u.id === project.creator_id) || {};
        usersWithAccessMap.set(project.creator_id, {
          user_id: project.creator_id,
          user_email: project.creator_email,
          user_role: ownerInfo.role || 'user',
          organization_name: ownerInfo.organization?.name || 'No Organization',
          granted_by: 'System',
          granted_at: project.created_at,
          access_type: 'owner'
        });
      }

      // Convert map to array and sort (owner first)
      const allAccessList = Array.from(usersWithAccessMap.values());
      allAccessList.sort((a, b) => {
        if (a.access_type === 'owner') return -1;
        if (b.access_type === 'owner') return 1;
        return 0;
      });

      setAllUsersWithAccess(allAccessList);

      // Calculate available users (those without access)
      const usersWithAccessIds = new Set(allAccessList.map(u => u.user_id));
      const available = users.filter(u => !usersWithAccessIds.has(u.id));
      setAvailableUsers(available);

      console.log('✅ Final users with access:', allAccessList.length, allAccessList);
      console.log('✅ Available users for granting:', available.length);

    } catch (err) {
      console.error('❌ Error loading access data:', err);
      setError('Failed to load project access data');
    } finally {
      setLoading(false);
    }
  };

  const handleGrantAccess = async () => {
    if (!selectedUserForAccess) {
      toast.error('Please select a user');
      return;
    }

    try {
      setIsGranting(true);
      await grantProjectAccess(project.id, selectedUserForAccess);
      toast.success('Access granted successfully!');
      setSelectedUserForAccess('');

      await loadAllAccessData();
      onRefresh();
    } catch (error) {
      console.error('Error granting access:', error);
      toast.error(error?.response?.data?.detail || 'Failed to grant access');
    } finally {
      setIsGranting(false);
    }
  };

  const handleTransferOwnership = async () => {
    if (!selectedUserForTransfer) {
      toast.error('Please select a user');
      return;
    }

    const selectedUser = users.find(u => u.id === selectedUserForTransfer);
    if (!window.confirm(`⚠️ WARNING: Transfer ownership of "${project.name}" to ${selectedUser?.email}?\n\nThis action cannot be undone!`)) {
      return;
    }

    try {
      setIsTransferring(true);
      await assignProjectToUser(project.id, selectedUserForTransfer);
      toast.success('Project ownership transferred successfully!');
      setSelectedUserForTransfer('');

      // Update local project info
      project.creator_id = selectedUserForTransfer;
      project.creator_email = selectedUser?.email;

      await loadAllAccessData();
      onRefresh();
    } catch (error) {
      console.error('Error transferring ownership:', error);
      toast.error(error?.response?.data?.detail || 'Failed to transfer ownership');
    } finally {
      setIsTransferring(false);
    }
  };

  const handleRevokeAccess = async (userId, userEmail, accessType) => {
    if (accessType === 'owner') {
      toast.error('Cannot revoke access from project owner. Transfer ownership first if needed.');
      return;
    }

    if (!window.confirm(`Are you sure you want to revoke access from ${userEmail}?`)) return;

    try {
      await revokeProjectAccess(project.id, userId);
      toast.success('Access revoked successfully!');

      await loadAllAccessData();
      onRefresh();
    } catch (error) {
      console.error('Error revoking access:', error);
      toast.error('Failed to revoke access');
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            Loading project access data...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-xl">
        {/* Header */}
        <div className="flex justify-between items-center mb-6 pb-4 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Project Access Management</h2>
            <p className="text-sm text-gray-600 mt-1">Manage who can access "{project.name}"</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl font-bold">&times;</button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            <div className="flex justify-between items-center">
              <span>{error}</span>
              <button onClick={loadAllAccessData} className="underline hover:no-underline">Retry</button>
            </div>
          </div>
        )}

        {/* Project Information */}
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold mb-3 text-blue-900">📋 Project Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p><strong>Name:</strong> {project.name}</p>
              <p><strong>Description:</strong> {project.description || 'No description'}</p>
            </div>
            <div>
              <p><strong>Current Owner:</strong> {project.creator_email || 'Unknown'}</p>
              <p><strong>Organization:</strong> {project.organization?.name || project.organization_name || 'No organization'}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Current Access List */}
          <div className="lg:col-span-2">
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 rounded-t-lg">
                <h3 className="text-lg font-semibold text-gray-900">
                  👥 Users with Access ({allUsersWithAccess.length})
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  All users who can access this project
                </p>
              </div>

              <div className="max-h-96 overflow-y-auto">
                {allUsersWithAccess.length === 0 ? (
                  <div className="p-6 text-center text-gray-500">
                    <p>No users found with access.</p>
                    <button 
                      onClick={loadAllAccessData} 
                      className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                    >
                      Refresh Data
                    </button>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {allUsersWithAccess.map((access) => (
                      <div key={access.user_id} className={`p-4 hover:bg-gray-50 transition-colors ${access.access_type === 'owner' ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}`}>
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="font-medium text-gray-900">{access.user_email}</span>
                              {access.access_type === 'owner' && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  👑 Owner
                                </span>
                              )}
                              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                access.user_role === 'superadmin' ? 'bg-red-100 text-red-800' :
                                access.user_role === 'orgadmin' ? 'bg-purple-100 text-purple-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {access.user_role}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600 space-y-1">
                              <p><strong>Organization:</strong> {access.organization_name}</p>
                              <p><strong>Access granted:</strong> {new Date(access.granted_at).toLocaleDateString()} by {access.granted_by}</p>
                              <p><strong>Access type:</strong> {
                                access.access_type === 'owner' ? 'Full ownership and control' : 
                                access.access_type === 'permission' ? 'View and interact with project' :
                                access.access_type === 'assigned' ? 'Project assignment access' :
                                'Project access (inferred)'
                              }</p>
                            </div>
                          </div>
                          <div className="ml-4">
                            {access.access_type === 'owner' ? (
                              <span className="inline-flex items-center px-3 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-blue-50 cursor-not-allowed">
                                Project Owner
                              </span>
                            ) : (
                              <button
                                onClick={() => handleRevokeAccess(access.user_id, access.user_email, access.access_type)}
                                className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
                              >
                                Revoke Access
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Actions */}
          <div className="space-y-6">
            {/* Grant Access Section */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-green-800 mb-3">🔐 Grant Access</h3>
              <p className="text-sm text-green-700 mb-4">Give users access to view and use the project</p>

              <div className="space-y-3">
                <select
                  value={selectedUserForAccess}
                  onChange={(e) => setSelectedUserForAccess(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 text-sm"
                  disabled={isGranting}
                >
                  <option value="">Select user...</option>
                  {availableUsers.map(user => (
                    <option key={user.id} value={user.id}>
                      {user.email} ({user.role}) - {user.organization?.name || 'No org'}
                    </option>
                  ))}
                </select>

                {availableUsers.length === 0 && (
                  <p className="text-sm text-gray-500 italic">All users already have access</p>
                )}

                <button
                  onClick={handleGrantAccess}
                  disabled={!selectedUserForAccess || isGranting || availableUsers.length === 0}
                  className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium transition-colors"
                >
                  {isGranting ? 'Granting Access...' : 'Grant Access'}
                </button>
              </div>
            </div>

            {/* Transfer Ownership Section */}
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-red-800 mb-3">⚠️ Transfer Ownership</h3>
              <div className="bg-red-100 border border-red-300 rounded p-3 mb-4">
                <p className="text-sm text-red-800 font-medium">⚠️ Dangerous Action!</p>
                <p className="text-xs text-red-700 mt-1">This will transfer complete control and cannot be undone.</p>
              </div>

              <div className="space-y-3">
                <select
                  value={selectedUserForTransfer}
                  onChange={(e) => setSelectedUserForTransfer(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500 text-sm"
                  disabled={isTransferring}
                >
                  <option value="">Select new owner...</option>
                  {users
                    .filter(user => user.id !== project.creator_id)
                    .map(user => (
                      <option key={user.id} value={user.id}>
                        {user.email} ({user.role}) - {user.organization?.name || 'No org'}
                      </option>
                    ))
                  }
                </select>

                <button
                  onClick={handleTransferOwnership}
                  disabled={!selectedUserForTransfer || isTransferring}
                  className="w-full bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium transition-colors"
                >
                  {isTransferring ? 'Transferring...' : 'Transfer Ownership'}
                </button>
              </div>
            </div>

            {/* Refresh Button */}
            <button 
              onClick={loadAllAccessData} 
              className="w-full bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600 text-sm font-medium transition-colors"
              disabled={loading}
            >
              {loading ? 'Refreshing...' : '🔄 Refresh Data'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-gray-200 flex justify-between items-center">
          <div className="text-sm text-gray-600">
            <strong>Summary:</strong> {allUsersWithAccess.filter(a => a.access_type !== 'owner').length} users with access • Owner: {project.creator_email}
          </div>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

const OrgDashboard = () => {
  const { user: currentUser } = useAuth();
  const [activeSection, setActiveSection] = useState("overview");
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [creatingUser, setCreatingUser] = useState(false);
  const [userSearch, setUserSearch] = useState("");

  // ✅ Updated modal state management
  const [selectedProjectForAccess, setSelectedProjectForAccess] = useState(null);
  const [showProjectAccessModal, setShowProjectAccessModal] = useState(false);

  // ✅ File viewing state variables (NEW)
  const [selectedProjectForFiles, setSelectedProjectForFiles] = useState(null);
  const [showProjectFilesModal, setShowProjectFilesModal] = useState(false);

  useEffect(() => {
    if (currentUser) {
      loadUsers();
      loadProjects();
    }
  }, [currentUser]);

  const loadUsers = async () => {
    setLoadingUsers(true);
    try {
      const users = await fetchUsers(null);
      const orgUsers = users.filter(user => 
        user.organization_id === currentUser?.organization_id
      );
      setUsers(orgUsers || []);
    } catch (err) {
      toast.error("Failed to fetch users");
    } finally {
      setLoadingUsers(false);
    }
  };

  // ✅ Enhanced project loading with debug logging
  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      console.log("🔍 OrgAdmin - Loading projects...");
      console.log("🔍 Current user org ID:", currentUser?.organization_id);

      const res = await fetchProjects();
      console.log("📊 Raw fetchProjects response:", res);

      let projectsData = [];
      if (Array.isArray(res)) {
        projectsData = res;
      } else if (res?.projects) {
        projectsData = res.projects;
      } else if (res?.data) {
        projectsData = res.data;
      }

      console.log("📋 Extracted projects data:", projectsData);

      // ✅ More robust filtering with debug logs
      const orgProjects = projectsData.filter(project => {
        const projectOrgId = String(project.organization_id || '');
        const userOrgId = String(currentUser?.organization_id || '');
        const match = projectOrgId === userOrgId && projectOrgId !== '';

        console.log(`🔍 Project "${project.name}":`, {
          projectOrgId,
          userOrgId,
          match
        });

        return match;
      });

      console.log("✅ Filtered org projects:", orgProjects);
      setProjects(orgProjects);

    } catch (err) {
      console.error('❌ Error loading projects:', err);
      toast.error("Failed to fetch projects");
      setProjects([]);
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUserEmail || !newUserPassword) {
      return toast.error("Email and password are required");
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newUserEmail)) {
      return toast.error("Please enter a valid email address");
    }
    if (newUserPassword.length < 6) {
      return toast.error("Password must be at least 6 characters long");
    }

    setCreatingUser(true);
    try {
      const userData = {
        email: newUserEmail,
        password: newUserPassword,
        role: "user",
        organization_id: currentUser.organization_id
      };
      await registerUser(userData);
      toast.success(`User '${newUserEmail}' created successfully!`);
      setNewUserEmail("");
      setNewUserPassword("");
      await loadUsers();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to create user");
    } finally {
      setCreatingUser(false);
    }
  };

  const handleToggleUser = async (userId, currentStatus) => {
    try {
      await toggleUserActive(userId, !currentStatus);
      toast.success("User status updated successfully");
      await loadUsers();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to update user status");
    }
  };

  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`Are you sure you want to delete user: ${userEmail}?`)) return;
    try {
      await deleteUser(userId);
      toast.success("User deleted successfully");
      await loadUsers();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to delete user");
    }
  };

  // ✅ Updated modal handlers
  const handleManageProjectAccess = (project) => {
    setSelectedProjectForAccess(project);
    setShowProjectAccessModal(true);
  };

  const closeProjectAccessModal = () => {
    setShowProjectAccessModal(false);
    setSelectedProjectForAccess(null);
  };

  // ✅ NEW: File viewing modal handlers
  const handleViewProjectFiles = (project) => {
    setSelectedProjectForFiles(project);
    setShowProjectFilesModal(true);
  };

  const closeProjectFilesModal = () => {
    setShowProjectFilesModal(false);
    setSelectedProjectForFiles(null);
  };

  const totalUsers = users.length;
  const activeUsers = users.filter((u) => u.is_active).length;
  const filteredUsers = users.filter(user => 
    user.email.toLowerCase().includes(userSearch.toLowerCase())
  );

  const menuItems = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "users", label: "Users", icon: "👥" },
    { id: "projects", label: "Projects", icon: "📁" },
    { id: "createUser", label: "Create User", icon: "➕" },
  ];

  const renderOverview = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600 mr-4">
              <span className="text-2xl">👥</span>
            </div>
            <div>
              <p className="text-sm text-gray-600">Organization Users</p>
              <p className="text-3xl font-bold text-gray-800">{totalUsers}</p>
            </div>
          </div>
          <div className="mt-4 flex justify-between text-sm">
            <span className="text-green-600">Active: {activeUsers}</span>
            <span className="text-red-600">Inactive: {totalUsers - activeUsers}</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 text-green-600 mr-4">
              <span className="text-2xl">🏢</span>
            </div>
            <div>
              <p className="text-sm text-gray-600">Organization</p>
              <p className="text-lg font-bold text-gray-800">{currentUser?.organization?.name || "Loading..."}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 text-purple-600 mr-4">
              <span className="text-2xl">📁</span>
            </div>
            <div>
              <p className="text-sm text-gray-600">Projects</p>
              <p className="text-3xl font-bold text-gray-800">{projects.length}</p>
            </div>
          </div>
        </div>
      </div>
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold mb-4">Organization Information</h3>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-xl">ℹ️</span>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>Organization Admin Access:</strong> You can manage users and project access within your organization. 
                Projects are now private by default - you need to explicitly grant access to users.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderUsers = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center gap-4">
          <h2 className="text-2xl font-bold text-gray-800">Organization Users</h2>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Search users..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            />
            <button 
              onClick={loadUsers}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={loadingUsers}
            >
              {loadingUsers ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loadingUsers ? (
              <tr><td colSpan="4" className="px-6 py-4 text-center">Loading users...</td></tr>
            ) : filteredUsers.length === 0 ? (
              <tr><td colSpan="4" className="px-6 py-4 text-center text-gray-500">No users found</td></tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{user.email}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      user.role === 'orgadmin' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-medium space-x-2">
                    <button
                      onClick={() => handleToggleUser(user.id, user.is_active)}
                      className={`px-3 py-1 rounded text-xs ${
                        user.is_active ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                      }`}
                    >
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    {user.role !== 'orgadmin' && (
                      <button
                        onClick={() => handleDeleteUser(user.id, user.email)}
                        className="px-3 py-1 bg-red-100 text-red-700 rounded text-xs"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
  const renderProjects = () => (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Organization Projects</h2>
        <button 
          onClick={loadProjects}
          className="px-3 py-1 bg-blue-500 text-white rounded text-sm"
          disabled={loadingProjects}
        >
          {loadingProjects ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className="text-xl">⚠️</span>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong>New:</strong> Projects are now private by default. Use "Manage Access" to grant specific users access to projects.
            </p>
          </div>
        </div>
      </div>

      {loadingProjects ? (
        <div className="text-center py-8">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No projects found in your organization</p>
          <p className="text-xs mt-2">Check browser console for debug info</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div key={project.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-medium text-gray-900 flex-1">{project.name}</h3>
                <div className="flex gap-2 ml-2">
                  {/* ✅ NEW: View Files Icon Button */}
                  <button
                    onClick={() => handleViewProjectFiles(project)}
                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                    title="View Project Files"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </button>
                  {/* ✅ Updated Manage Access button */}
                  <button
                    onClick={() => handleManageProjectAccess(project)}
                    className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                  >
                    Manage Access
                  </button>
                </div>
              </div>

              {project.description && (
                <p className="text-sm text-gray-600 mb-3">{project.description}</p>
              )}

              <div className="text-xs text-gray-500 space-y-1">
                <p>Creator: {project.creator_email || 'Unknown'}</p>
                <p>Created: {new Date(project.created_at).toLocaleDateString()}</p>
                <p>Users with access: {project.permission_count || 0}</p>
              </div>

              <div className="mt-3 pt-3 border-t border-gray-200">
                <span className={`inline-block px-2 py-1 text-xs rounded-full ${
                  project.creator_id === currentUser?.id 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {project.creator_id === currentUser?.id ? 'Owner' : 'Organization Project'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderCreateUser = () => (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Create New User</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input
          type="email"
          placeholder="User email *"
          value={newUserEmail}
          onChange={(e) => setNewUserEmail(e.target.value)}
          className="border border-gray-300 p-3 rounded-md"
          disabled={creatingUser}
        />
        <input
          type="password"
          placeholder="Password * (min 6 chars)"
          value={newUserPassword}
          onChange={(e) => setNewUserPassword(e.target.value)}
          className="border border-gray-300 p-3 rounded-md"
          disabled={creatingUser}
        />
      </div>
      <div className="mt-4 p-3 bg-blue-50 rounded text-sm text-blue-700">
        <strong>Note:</strong> New users will be created as regular users and automatically assigned to your organization.
        They will only have access to projects that you explicitly grant them access to.
      </div>
      <button
        onClick={handleCreateUser}
        disabled={creatingUser || !newUserEmail || !newUserPassword}
        className="mt-4 px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
      >
        {creatingUser ? 'Creating...' : 'Create User'}
      </button>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6">
          <h1 className="text-xl font-bold text-gray-800">Organization Admin</h1>
          <p className="text-sm text-gray-600 mt-1">{currentUser?.organization?.name}</p>
        </div>
        <nav className="mt-6">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`w-full flex items-center px-6 py-3 text-left hover:bg-blue-50 ${
                activeSection === item.id ? 'bg-blue-100 border-r-4 border-blue-600 text-blue-700' : 'text-gray-700'
              }`}
            >
              <span className="text-xl mr-3">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="Organization Admin Dashboard" />
        <main className="flex-1 overflow-auto p-6">
          {activeSection === "overview" && renderOverview()}
          {activeSection === "users" && renderUsers()}
          {activeSection === "projects" && renderProjects()}
          {activeSection === "createUser" && renderCreateUser()}
        </main>
      </div>

      {/* ✅ Enhanced Project Access Management Modal */}
      {showProjectAccessModal && selectedProjectForAccess && (
        <ProjectManagementModal
          project={selectedProjectForAccess}
          users={users}
          onClose={closeProjectAccessModal}
          onRefresh={loadProjects}
        />
      )}

      {/* ✅ NEW: Project Files Modal */}
      {showProjectFilesModal && selectedProjectForFiles && (
        <ProjectFilesModal
          project={selectedProjectForFiles}
          onClose={closeProjectFilesModal}
        />
      )}
    </div>
  );
};

export default OrgDashboard;