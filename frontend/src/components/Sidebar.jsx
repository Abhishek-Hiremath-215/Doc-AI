import React, { useState, useEffect } from "react";
import { 
  FolderPlus, 
  Plus, 
  FileText, 
  File, 
  Upload, 
  ChevronDown, 
  ChevronRight,
  User,
  Crown,
  Shield,
  CheckCircle2,
  Circle,
  Folder,
  FolderOpen,
  FileX
} from "lucide-react";

function Sidebar({
  showSidebar,
  showProjectCreation,
  setShowProjectCreation,
  projectName,
  setProjectName,
  projectDescription,
  setProjectDescription,
  handleCreateProject,
  projects = [],
  selectedProjects,
  toggleProject,
  toggleSelectAllProjects,
  handleFileUpload,
  files = [], // Files for currently selected project
  selectedFiles,
  toggleFile,
  toggleSelectAllFiles,
  projectAccessInfo = {},
  loadingProjects = false,
  currentUser,
  fetchProjectFiles // New prop to fetch files for specific project
}) {
  const [expandedProjects, setExpandedProjects] = useState(new Set());
  const [projectFiles, setProjectFiles] = useState({}); // Store files per project
  const [loadingFiles, setLoadingFiles] = useState(new Set());
  
  if (!showSidebar) return null;

  const getFileIcon = (fileName) => {
    const ext = fileName.split(".").pop()?.toLowerCase();
    const iconClass = "w-4 h-4";
    
    switch (ext) {
      case "pdf":
        return <FileText className={`${iconClass} text-red-500`} />;
      case "doc":
      case "docx":
        return <FileText className={`${iconClass} text-blue-500`} />;
      case "xls":
      case "xlsx":
      case "csv":
        return <FileText className={`${iconClass} text-green-500`} />;
      case "ppt":
      case "pptx":
        return <FileText className={`${iconClass} text-orange-500`} />;
      case "txt":
        return <FileText className={`${iconClass} text-slate-500`} />;
      default:
        return <File className={`${iconClass} text-slate-400`} />;
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'superadmin':
        return <Crown className="w-3 h-3 text-red-600" />;
      case 'orgadmin':
        return <Shield className="w-3 h-3 text-blue-600" />;
      default:
        return <User className="w-3 h-3 text-slate-600" />;
    }
  };

  const getRoleBadge = (role) => {
    const baseClasses = "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium";
    switch (role) {
      case 'superadmin':
        return `${baseClasses} bg-red-100 text-red-800`;
      case 'orgadmin':
        return `${baseClasses} bg-blue-100 text-blue-800`;
      default:
        return `${baseClasses} bg-slate-100 text-slate-800`;
    }
  };

  // ✅ NEW: Toggle project expansion and load files
  const toggleProjectExpansion = async (projectId) => {
    const newExpanded = new Set(expandedProjects);
    
    if (newExpanded.has(projectId)) {
      newExpanded.delete(projectId);
    } else {
      newExpanded.add(projectId);
      
      // Load files for this project if not already loaded
      if (!projectFiles[projectId]) {
        setLoadingFiles(prev => new Set([...prev, projectId]));
        try {
          const data = await fetchProjectFiles(projectId);
          const files = Array.isArray(data.files) ? data.files : [];
          setProjectFiles(prev => ({
            ...prev,
            [projectId]: files
          }));
        } catch (error) {
          console.error('Failed to fetch project files:', error);
          setProjectFiles(prev => ({
            ...prev,
            [projectId]: []
          }));
        } finally {
          setLoadingFiles(prev => {
            const newSet = new Set(prev);
            newSet.delete(projectId);
            return newSet;
          });
        }
      }
    }
    
    setExpandedProjects(newExpanded);
  };

  const handleFileInputChange = (e, projectId) => {
    const selectedFilesToUpload = e.target.files;
    if (!selectedFilesToUpload?.length) return;
    
    // Upload files to specific project
    handleFileUpload(Array.from(selectedFilesToUpload), projectId).then(() => {
      // Refresh files for this project
      fetchProjectFiles(projectId).then(data => {
        const files = Array.isArray(data.files) ? data.files : [];
        setProjectFiles(prev => ({
          ...prev,
          [projectId]: files
        }));
      });
    });
    e.target.value = "";
  };

  const getProjectFiles = (projectId) => {
    return projectFiles[projectId] || [];
  };

  const isProjectExpanded = (projectId) => {
    return expandedProjects.has(projectId);
  };

  return (
    <div className="h-full bg-white border-r border-slate-200 flex flex-col shadow-lg">
      
      {/* Modern User Header */}
      <div className="p-6 bg-gradient-to-r from-slate-50 to-blue-50 border-b border-slate-200">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-sm">
            <User className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-slate-800 truncate text-sm">
              {currentUser?.email || 'User'}
            </div>
            <div className="flex items-center space-x-2 mt-1">
              {currentUser && (
                <span className={getRoleBadge(currentUser.role)}>
                  <span className="flex items-center space-x-1">
                    {getRoleIcon(currentUser.role)}
                    <span>{currentUser.role}</span>
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-y-auto">
        
        {/* Projects Section Header */}
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-sm uppercase tracking-wide text-slate-700">Projects & Files</span>
            </div>
            
            <button
              onClick={() => setShowProjectCreation(!showProjectCreation)}
              className="p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors shadow-sm"
              title="Create new project"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Project Creation Form */}
          {showProjectCreation && (
            <div className="mb-4 p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Enter project name..."
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
              <textarea
                value={projectDescription}
                onChange={(e) => setProjectDescription(e.target.value)}
                placeholder="Enter project description..."
                rows={3}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleCreateProject}
                disabled={!projectName.trim() || !projectDescription.trim()}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Create Project
              </button>
            </div>
          )}

          {/* Projects List with Integrated Files */}
          <div className="space-y-2">
            {loadingProjects ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-8">
                <Folder className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p className="text-sm text-slate-600 mb-2">No projects yet</p>
                <p className="text-xs text-slate-500">Create your first project to get started</p>
              </div>
            ) : (
              <div className="space-y-1">
                {/* Select All Projects */}
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <label className="flex items-center space-x-2 cursor-pointer flex-1">
                    <input
                      type="checkbox"
                      checked={projects.length > 0 && selectedProjects.length === projects.length}
                      onChange={toggleSelectAllProjects}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                    />
                    <span className="text-sm font-medium text-slate-700">
                      Select All Projects
                    </span>
                  </label>
                  <span className="text-xs text-slate-500 bg-white px-2 py-1 rounded-full">
                    {selectedProjects.length}/{projects.length}
                  </span>
                </div>
                
                {/* Individual Projects with Files */}
                {projects.map((proj) => {
                  const projectId = proj.project_id || proj.id;
                  const name = proj.project_name || proj.name || "Unnamed Project";
                  const isSelected = selectedProjects.includes(projectId);
                  const isExpanded = isProjectExpanded(projectId);
                  const accessInfo = projectAccessInfo[projectId];
                  const projectFilesData = getProjectFiles(projectId);
                  const isLoadingProjectFiles = loadingFiles.has(projectId);
                  
                  return (
                    <div key={projectId} className="border border-slate-200 rounded-lg bg-white">
                      {/* Project Header */}
                      <div className="p-3">
                        <div className="flex items-center space-x-3">
                          {/* Expand/Collapse Button */}
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
                          
                          {/* Project Selection Checkbox */}
                          <label className="flex items-center space-x-3 cursor-pointer flex-1">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleProject(projectId)}
                              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
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
                              <div className="flex items-center space-x-2 mt-1">
                                <span className="text-xs text-slate-500">ID: {projectId}</span>
                                {accessInfo && (
                                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                                    accessInfo.isOwner 
                                      ? 'bg-green-100 text-green-700' 
                                      : 'bg-blue-100 text-blue-700'
                                  }`}>
                                    {accessInfo.isOwner ? 'Owner' : 'Shared'}
                                  </span>
                                )}
                              </div>
                            </div>
                          </label>
                        </div>
                      </div>

                      {/* Files Section - Show when expanded */}
                      {isExpanded && (
                        <div className="border-t border-slate-200 bg-slate-50 p-3">
                          {/* File Upload Area */}
                          <div className="mb-3">
                            <div className="p-3 border-2 border-dashed border-slate-300 rounded-lg hover:border-slate-400 transition-colors">
                              <div className="text-center">
                                <Upload className="mx-auto h-6 w-6 text-slate-400 mb-1" />
                                <div className="flex text-xs">
                                  <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                                    <span>Upload files</span>
                                    <input
                                      type="file"
                                      multiple
                                      onChange={(e) => handleFileInputChange(e, projectId)}
                                      className="sr-only"
                                    />
                                  </label>
                                  <span className="text-slate-500 ml-1">to this project</span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Files List */}
                          {isLoadingProjectFiles ? (
                            <div className="flex items-center justify-center py-4">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                              <span className="ml-2 text-xs text-slate-500">Loading files...</span>
                            </div>
                          ) : projectFilesData.length === 0 ? (
                            <div className="text-center py-4">
                              <FileX className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                              <p className="text-xs text-slate-600 mb-1">No files uploaded</p>
                              <p className="text-xs text-slate-500">Upload files to analyze</p>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              {/* Select All Files for This Project */}
                              <div className="flex items-center justify-between p-2 bg-white rounded border">
                                <label className="flex items-center space-x-2 cursor-pointer flex-1">
                                  <input
                                    type="checkbox"
                                    checked={projectFilesData.length > 0 && 
                                      projectFilesData.every(file => 
                                        selectedFiles.includes(file.name || file.file_name)
                                      )}
                                    onChange={() => {
                                      const allProjectFileNames = projectFilesData.map(f => f.name || f.file_name);
                                      const allSelected = allProjectFileNames.every(name => selectedFiles.includes(name));
                                      
                                      if (allSelected) {
                                        // Deselect all files from this project
                                        allProjectFileNames.forEach(name => {
                                          if (selectedFiles.includes(name)) {
                                            toggleFile(name);
                                          }
                                        });
                                      } else {
                                        // Select all files from this project
                                        allProjectFileNames.forEach(name => {
                                          if (!selectedFiles.includes(name)) {
                                            toggleFile(name);
                                          }
                                        });
                                      }
                                    }}
                                    className="w-3 h-3 text-blue-600"
                                  />
                                  <span className="text-xs font-medium text-slate-600">
                                    Select All Files
                                  </span>
                                </label>
                                <span className="text-xs text-slate-500">
                                  {projectFilesData.filter(file => 
                                    selectedFiles.includes(file.name || file.file_name)
                                  ).length}/{projectFilesData.length}
                                </span>
                              </div>
                              
                              {/* Individual Files */}
                              <div className="max-h-32 overflow-y-auto space-y-1">
                                {projectFilesData.map((file, index) => {
                                  const fileName = file.name || file.file_name || `File ${index + 1}`;
                                  const isFileSelected = selectedFiles.includes(fileName);
                                  
                                  return (
                                    <div key={file.file_id || fileName} className="group">
                                      <label className="flex items-center space-x-2 p-2 rounded hover:bg-white cursor-pointer transition-colors">
                                        <input
                                          type="checkbox"
                                          checked={isFileSelected}
                                          onChange={() => toggleFile(fileName)}
                                          className="w-3 h-3 text-blue-600"
                                        />
                                        
                                        {getFileIcon(fileName)}
                                        
                                        <div className="flex-1 min-w-0">
                                          <div className="text-xs font-medium text-slate-700 truncate" title={fileName}>
                                            {fileName}
                                          </div>
                                          <div className="text-xs text-slate-500">
                                            {fileName.split('.').pop()?.toUpperCase()} file
                                          </div>
                                        </div>
                                      </label>
                                    </div>
                                  );
                                })}
                              </div>
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
      </div>

      {/* Bottom Summary */}
      <div className="p-6 bg-slate-50 border-t border-slate-200">
        {selectedProjects.length > 0 ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">Ready to Chat</span>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span className="text-xs text-green-600">Active</span>
              </div>
            </div>
            <div className="text-xs text-slate-600 space-y-1">
              <div>• {selectedProjects.length} project{selectedProjects.length !== 1 ? 's' : ''} selected</div>
              <div>• {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected</div>
              <div className="text-slate-500 mt-2 p-2 bg-white rounded border">
                💡 Ask questions about your documents in the main chat
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center">
            <div className="text-sm font-medium text-slate-700 mb-2">Get Started</div>
            <div className="text-xs text-slate-500 space-y-1">
              <div>1. Select a project above</div>
              <div>2. Expand to view & select files</div>
              <div>3. Start chatting!</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Sidebar;
