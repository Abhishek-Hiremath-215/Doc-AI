import React, { useState, useEffect } from 'react';
import {
  X,
  FolderPlus,
  Folder,
  FolderOpen,
  File,
  Upload,
  ChevronDown,
  ChevronRight,
  Circle,
  CheckCircle2,
  Crown,
  Shield,
  FileX,
  Loader
} from 'lucide-react';

function ProjectSidebar({
  showSidebar,
  onClose,
  showProjectCreation,
  setShowProjectCreation,
  projectName,
  setProjectName,
  projectDescription,
  setProjectDescription,
  handleCreateProject,
  projects = [],
  selectedProjects = [],
  toggleProject,
  handleFileUpload,
  projectAccessInfo = {},
  loadingProjects = false,
  currentUser,
  projectFiles = {}, // Files state from parent
  expandedProjects = new Set(), // Expansion state from parent
  onToggleExpand, // Handler from parent
}) {
  const [localLoadingFiles, setLocalLoadingFiles] = useState(new Set());

  const getRoleBadge = (role) => {
    switch (role) {
      case 'owner':
        return <Crown className="w-4 h-4 text-yellow-500" title="Owner" />;
      case 'admin':
        return <Shield className="w-4 h-4 text-blue-500" title="Admin" />;
      case 'editor':
        return <CheckCircle2 className="w-4 h-4 text-green-500" title="Editor" />;
      default:
        return <Circle className="w-4 h-4 text-gray-500" title="Viewer" />;
    }
  };

  if (!showSidebar) return null;

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col h-screen overflow-hidden shadow-lg">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50">
        <h2 className="text-lg font-bold text-gray-800 flex items-center">
          <Folder className="w-5 h-5 mr-2 text-blue-600" />
          Projects
        </h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-white text-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Project Creation */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={() => setShowProjectCreation(!showProjectCreation)}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg transition-all shadow-md hover:shadow-lg"
        >
          <FolderPlus className="w-5 h-5" />
          <span className="font-medium">New Project</span>
        </button>

        {showProjectCreation && (
          <div className="mt-4 space-y-3 animate-fadeIn">
            <input
              type="text"
              placeholder="Project name *"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <textarea
              placeholder="Description (optional)"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows="3"
            />
            <div className="flex space-x-2">
              <button
                onClick={handleCreateProject}
                disabled={!projectName.trim()}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                Create
              </button>
              <button
                onClick={() => {
                  setShowProjectCreation(false);
                  setProjectName('');
                  setProjectDescription('');
                }}
                className="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loadingProjects ? (
          <div className="flex flex-col items-center justify-center h-32">
            <Loader className="w-8 h-8 text-blue-500 animate-spin mb-2" />
            <p className="text-sm text-gray-500">Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-8">
            <FolderOpen className="w-16 h-16 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-600 font-medium mb-1">No projects yet</p>
            <p className="text-gray-500 text-sm">Create your first project to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {projects.map((project) => {
              const isExpanded = expandedProjects.has(project.id);
              const isSelected = selectedProjects.includes(project.id);
              const accessInfo = projectAccessInfo[project.id] || {};
              const files = projectFiles[project.id] || [];
              const isLoadingFiles = localLoadingFiles.has(project.id);

              return (
                <div
                  key={project.id}
                  className={`border rounded-lg transition-all ${
                    isSelected ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  {/* Project Header */}
                  <div className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 flex-1 min-w-0">
                        <button
                          onClick={() => onToggleExpand && onToggleExpand(project.id)}
                          className="p-1 hover:bg-gray-100 rounded transition-colors flex-shrink-0"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-600" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-600" />
                          )}
                        </button>
                        
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleProject(project.id)}
                          className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 flex-shrink-0"
                        />
                        
                        {isExpanded ? (
                          <FolderOpen className="w-5 h-5 text-blue-600 flex-shrink-0" />
                        ) : (
                          <Folder className="w-5 h-5 text-blue-600 flex-shrink-0" />
                        )}
                        
                        <span className="text-sm font-medium text-gray-800 truncate">
                          {project.name}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        {getRoleBadge(accessInfo.role)}
                        {accessInfo.canUpload && (
                          <label className="cursor-pointer p-1.5 hover:bg-gray-100 rounded transition-colors" title="Upload files">
                            <Upload className="w-4 h-4 text-gray-600" />
                            <input
                              type="file"
                              multiple
                              onChange={(e) => handleFileUpload(project.id, e)}
                              className="hidden"
                              accept=".pdf,.doc,.docx,.txt,.csv,.xlsx"
                            />
                          </label>
                        )}
                      </div>
                    </div>
                    
                    {project.description && (
                      <p className="text-xs text-gray-500 mt-2 ml-11 line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>

                  {/* Files List */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 bg-gray-50 p-3">
                      {isLoadingFiles ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader className="w-6 h-6 text-blue-500 animate-spin" />
                        </div>
                      ) : files.length === 0 ? (
                        <div className="text-center py-4">
                          <FileX className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-xs text-gray-500 font-medium">No files uploaded</p>
                          <p className="text-xs text-gray-400 mt-1">Click upload to add documents</p>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          {files.map((file) => (
                            <div
                              key={file.id}
                              className="flex items-center space-x-2 p-2 hover:bg-white rounded transition-colors group"
                            >
                              <File className="w-4 h-4 text-gray-500 flex-shrink-0" />
                              <span className="text-xs text-gray-700 truncate flex-1" title={file.name}>
                                {file.name}
                              </span>
                              {file.size && (
                                <span className="text-xs text-gray-400 flex-shrink-0">
                                  {(file.size / 1024).toFixed(1)} KB
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProjectSidebar;
