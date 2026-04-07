import axios from "axios";

// Environment variables configuration
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

// Debug: Log the backend URL to console
console.log("🔗 API Base URL:", BACKEND_URL);

// Create axios instance
const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 60000, // 60 second timeout
  headers: { 
    "Content-Type": "application/json"
  },
});

// Request interceptor - attach JWT token and log requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Debug: Log outgoing requests
    console.log(`📤 API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    
    return config;
  },
  (error) => {
    console.error("❌ Request Error:", error);
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401 and log responses
api.interceptors.response.use(
  (response) => {
    // Debug: Log successful responses
    console.log(`✅ API Response: ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
    return response;
  },
  (error) => {
    // Log error details
    const status = error.response?.status;
    const method = error.config?.method?.toUpperCase();
    const url = error.config?.url;
    const message = error.response?.data?.detail || error.message;
    
    console.error(`❌ API Error: ${status} ${method} ${url} - ${message}`);
    
    // Handle 401 globally
    if (status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      console.warn("🔐 Unauthorized: cleared token & user");
      
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);



/* ======================
      AUTHENTICATION
====================== */
export const loginUser = async (credentials) => {
  try {
    const res = await api.post("/users/login", credentials);
    const { access_token } = res.data;
    if (access_token) {
      localStorage.setItem("token", access_token);
      console.log("✅ Login successful, token stored");
    }
    return res.data;
  } catch (error) {
    console.error("❌ Login failed:", error);
    throw error;
  }
};

export const getCurrentUser = async () => {
  const token = localStorage.getItem("token");
  if (!token) {
    throw new Error("No token found, user not authenticated");
  }
  
  try {
    const res = await api.get("/users/me");
    return res.data;
  } catch (error) {
    console.error("❌ Get current user failed:", error);
    throw error;
  }
};

export const registerUser = async (userData) => {
  try {
    const res = await api.post("/users/register", userData);
    return res.data;
  } catch (error) {
    console.error("❌ Registration failed:", error);
    throw error;
  }
};




/* ======================
      PROJECTS & FILES
====================== */
export const createProject = async (name, description) => {
  try {
    const formData = new FormData();
    formData.append("project_name", name);
    formData.append("description", description);
    
    const res = await api.post("/projects/create", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  } catch (error) {
    console.error("❌ Create project failed:", error);
    throw error;
  }
};

// ✅ FIXED: Use correct endpoint for fetching projects
export const fetchProjects = async () => {
  try {
    console.log("🔍 DEBUG - Frontend Project Fetch:");
    
    // Check current user in localStorage
    const storedUser = JSON.parse(localStorage.getItem("user") || "null");
    console.log("  👤 Stored User:", storedUser?.email, "ID:", storedUser?.id);
    
    // Check token
    const token = localStorage.getItem("token");
    console.log("  🔐 Token exists:", !!token);
    console.log("  🔐 Token preview:", token?.substring(0, 50) + "...");
    
    console.log("📋 Making API request to /projects/");
    const response = await api.get("/projects/");
    
    console.log("✅ API Response received:");
    console.log("  Status:", response.status);
    console.log("  Data type:", Array.isArray(response.data) ? 'Array' : typeof response.data);
    console.log("  Data length:", response.data?.length || 0);
    console.log("  Raw response:", response.data);
    
    return response.data;
    
  } catch (error) {
    console.error("❌ Frontend fetch error:");
    console.error("  Status:", error.response?.status);
    console.error("  Message:", error.message);
    console.error("  Response data:", error.response?.data);
    throw error;
  }
};

// ✅ FIXED: Use the same endpoint for admin projects (role-based filtering handled by backend)
export const listAllProjectsAdmin = async () => {
  try {
    console.log("📋 Fetching admin projects from /projects/");
    const response = await api.get("/projects/");
    console.log("✅ Admin projects response:", response.data);
    return response.data; // Return data directly, not wrapped in projects property
  } catch (error) {
    console.error("❌ List admin projects failed:", error);
    throw error;
  }
};

// services/api.js
// export const uploadFiles = async (projectId, files, options = {}) => {
//   try {
//     const formData = new FormData();
    
//     // Try multiple common parameter names
//     files.forEach((file) => {
//       formData.append("files", file);  // Current attempt
//     });

//     console.log(`📤 Uploading ${files.length} files to /upload/${projectId}/upload`);
//     console.log('📋 FormData contents:', [...formData.entries()]);
    
//     const response = await api.post(`/upload/${projectId}/upload`, formData, {
//       onUploadProgress: options.onUploadProgress,
//       headers: {
//         'Content-Type': undefined
//       }
//     });
    
//     console.log("✅ Upload successful:", response.data);
//     return response.data;
//   } catch (error) {
//     // ✅ LOG THE DETAILED ERROR RESPONSE
//     console.error("❌ Upload failed - Full error:", error);
//     console.error("❌ Error response data:", error.response?.data);
//     console.error("❌ Error status:", error.response?.status);
//     console.error("❌ Error details:", JSON.stringify(error.response?.data, null, 2));
    
//     throw error;
//   }
// };

export const uploadFiles = async (projectId, files, options = {}) => {
  try {
    const formData = new FormData();
    
    files.forEach((file) => {
      formData.append("files", file);
    });

    console.log(`📤 Uploading ${files.length} files to /upload/${projectId}/upload`);
    console.log('📋 FormData contents:', [...formData.entries()]);
    
    const response = await api.post(`/upload/${projectId}/upload`, formData, {
      onUploadProgress: options.onUploadProgress,
      timeout: 600000,  // ✅ 10 minutes timeout for large files
      headers: {
        'Content-Type': 'multipart/form-data'  // ✅ Explicit content type
      }
    });
    
    console.log("✅ Upload successful:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ Upload failed - Full error:", error);
    console.error("❌ Error response data:", error.response?.data);
    console.error("❌ Error status:", error.response?.status);
    console.error("❌ Error message:", error.message);
    
    // Handle timeout specifically
    if (error.code === 'ECONNABORTED') {
      console.error("⏱️ Upload timeout - file processing took too long");
      throw new Error("Upload timeout. Large files may take several minutes to process.");
    }
    
    throw error;
  }
};

export const fetchProjectFiles = async (projectId) => {
  try {
    const response = await api.get(`/projects/${projectId}/files`);
    return response.data;
  } catch (error) {
    console.error("❌ Fetch project files failed:", error);
    throw error;
  }
};




/* ======================
      CHATBOT
====================== */
export const searchFiles = async (query, projectId) => {
  try {
    const response = await api.post("/query/search_files", { 
      query, 
      project_id: projectId 
    });
    return response.data;
  } catch (error) {
    console.error("❌ Search files failed:", error);
    throw error;
  }
};

export const askQuestion = async (question, selectedFiles, projectId) => {
  console.log('🔍 askQuestion called with:', { question, selectedFiles, projectId });
  
  if (!question || !projectId) {
    throw new Error("Question and project ID are required");
  }
  
  try {
    const filesArray = Array.isArray(selectedFiles)
      ? selectedFiles.map((f) => (typeof f === "string" ? f : f.filename || f.file_name))
      : [];
    
    console.log('📤 Sending request to /query/ask:', { 
      query: question, 
      selected_files: filesArray, 
      project_id: projectId 
    });
    
    const res = await api.post("/query/ask", { 
      query: question, 
      selected_files: filesArray, 
      project_id: projectId 
    });
    
    console.log('✅ Full response received:', res);
    console.log('✅ Response data:', res.data);
    console.log('✅ Response status:', res.status);
    
    // Check if response has expected structure
    if (!res.data || typeof res.data.answer === 'undefined') {
      console.error('❌ Invalid response structure:', res.data);
      throw new Error('Invalid response from server');
    }
    
    // Handle empty or very short answers
    if (!res.data.answer || res.data.answer.trim().length === 0) {
      console.warn('⚠️ Empty answer received');
      return {
        answer: "No answer was generated for your question. Please try rephrasing or check if the document contains relevant information.",
        chartBase64: null,
        chartUrl: null,
        images: []
      };
    }
    
    console.log('✅ Processing successful response with answer length:', res.data.answer.length);
    
    const images = res.data.chartUrl ? [`${BACKEND_URL}${res.data.chartUrl}`] : [];
    return { ...res.data, images };
    
  } catch (error) {
    console.error("❌ Ask question failed:", error);
    console.error("❌ Error response data:", error.response?.data);
    console.error("❌ Error status:", error.response?.status);
    console.error("❌ Error config:", error.config);
    
    // Re-throw with more context
    const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
    throw new Error(`Failed to get answer: ${errorMessage}`);
  }
};



/* ======================
      USERS & ADMIN
====================== */

// ✅ UPDATED: Call correct endpoint with organization data
export const fetchUsers = async (organizationFilter = null) => {
  try {
    const params = organizationFilter ? { organization_filter: organizationFilter } : {};
    const response = await api.get("/users/", { params });
    console.log("✅ Fetched users with organizations:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ Fetch users failed:", error);
    throw error;
  }
};

// ✅ UPDATED: Call correct endpoint for users with projects
export const fetchUsersWithProjects = async (page = 1, limit = 100) => {
  try {
    const response = await api.get("/users/with-projects", { 
      params: { page, limit } 
    });
    console.log("✅ Fetched users with projects and organizations:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ Fetch users with projects failed:", error);
    throw error;
  }
};

// ✅ NEW: Get organizations for filter dropdown
export const getUsersOrganizations = async () => {
  try {
    const response = await api.get("/users/organizations");
    return response.data;
  } catch (error) {
    console.error("❌ Fetch user organizations failed:", error);
    throw error;
  }
};

// ✅ UPDATED: Use correct endpoints for user actions
export const toggleUserActive = async (userId, isActive) => {
  try {
    const response = await api.put(`/users/${userId}/activate`);
    return response.data;
  } catch (error) {
    console.error("❌ Toggle user active failed:", error);
    throw error;
  }
};

export const deleteUser = async (userId) => {
  try {
    const response = await api.delete(`/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error("❌ Delete user failed:", error);
    throw error;
  }
};

// ✅ NEW: Assign user to organization
export const assignUserToOrganization = async (userId, organizationId) => {
  try {
    const response = await api.put(`/users/${userId}/organization`, {
      organization_id: organizationId
    });
    return response.data;
  } catch (error) {
    console.error("❌ Assign user to organization failed:", error);
    throw error;
  }
};

// Keep this for backward compatibility
export const listUsers = fetchUsers;




/* ======================
      ORGANIZATIONS
====================== */
export const listOrganizations = async () => {
  try {
    console.log("📋 Fetching organizations...");
    const response = await api.get("/organizations/");
    console.log("✅ Organizations fetched successfully:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ List organizations failed:", error);
    throw error;
  }
};

export const createOrganization = async (name, adminEmail, adminPassword, description = "") => {
  try {
    console.log("🏢 Creating organization with payload:", {
      name,
      description,
      admin_email: adminEmail,
      // Don't log password
    });
    
    const payload = {
      name: name.trim(),
      description: description.trim(),
      admin_email: adminEmail.trim(),
      admin_password: adminPassword,
    };
    
    // Validate payload before sending
    if (!payload.name) {
      throw new Error("Organization name is required");
    }
    if (!payload.admin_email) {
      throw new Error("Admin email is required");
    }
    if (!payload.admin_password) {
      throw new Error("Admin password is required");
    }
    
    console.log("📤 Sending POST request to /organizations/");
    const response = await api.post("/organizations/", payload);
    console.log("✅ Organization created successfully:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ Create organization failed:", error);
    if (error.response) {
      console.error("Response status:", error.response.status);
      console.error("Response data:", error.response.data);
      console.error("Response headers:", error.response.headers);
    }
    throw error;
  }
};

export const deleteOrganization = async (organizationId) => {
  try {
    const response = await api.delete(`/organizations/${organizationId}/`);
    return response.data;
  } catch (error) {
    console.error("❌ Delete organization failed:", error);
    throw error;
  }
};

export const updateOrganization = async (organizationId, data) => {
  try {
    const response = await api.put(`/organizations/${organizationId}/`, data);
    return response.data;
  } catch (error) {
    console.error("❌ Update organization failed:", error);
    throw error;
  }
};

// Add this to your services/api.js file
export const createOrganizationUser = async (userData) => {
  try {
    console.log("🔒 Creating organization user:", userData.email);
    const response = await api.post("/organizations/users", userData);
    console.log("✅ Organization user created successfully:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ Create organization user failed:", error);
    throw error;
  }
};

export const listOrganizationUsers = async () => {
  try {
    // ✅ FIXED: Use the main users endpoint instead of non-existent /users/organization
    const response = await api.get('/users/');
    console.log("✅ Organization users loaded:", response.data);
    return response.data;
  } catch (error) {
    console.error("❌ List organization users failed:", error);
    throw error;
  }
};

export const enhanceQuery = async (query) => {
  try {
    const res = await api.post("/query/enhance", { query });
    return res.data.enhanced_query;
  } catch (error) {
    console.error("❌ Query enhancement failed:", error);
    throw error;
  }
};




/* ===============================================
    PROJECT PERMISSION & ASSIGNMENT APIs - FINAL VERSION
=============================================== */

// ✅ CRITICAL FIX: Grant access (permissions without ownership change)
export const grantProjectAccess = async (projectId, userId) => {
  try {
    console.log(`🔐 Granting access: Project ${projectId} to User ${userId}`);
    const response = await api.post(`/projects/${projectId}/grant-access`, {
      user_id: userId
    }, {
      headers: { 'Content-Type': 'application/json' } // ✅ Explicit header
    });
    console.log('✅ Access granted successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error granting project access:', error);
    console.error('❌ Error details:', error.response?.data);
    throw error;
  }
};

// ✅ CRITICAL FIX: Assign project (ownership transfer) - SuperAdmin only
export const assignProjectToUser = async (projectId, userId) => {
  try {
    console.log(`🔄 Assigning project: Project ${projectId} to User ${userId}`);
    const response = await api.post(`/projects/${projectId}/assign`, {
      user_id: userId
    }, {
      headers: { 'Content-Type': 'application/json' } // ✅ Explicit header
    });
    console.log('✅ Project assigned successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error assigning project:', error);
    console.error('❌ Error details:', error.response?.data);
    throw error;
  }
};

// ✅ FIXED: Revoke access
export const revokeProjectAccess = async (projectId, userId) => {
  try {
    console.log(`🚫 Revoking access: Project ${projectId} from User ${userId}`);
    const response = await api.delete(`/projects/${projectId}/revoke-access/${userId}`);
    console.log('✅ Access revoked successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error revoking project access:', error);
    throw error;
  }
};

// ✅ Get project permissions (who has access)
export const getProjectPermissions = async (projectId) => {
  try {
    console.log(`📋 Fetching permissions for Project ${projectId}`);
    const response = await api.get(`/projects/${projectId}/permissions`);
    console.log('✅ Permissions fetched:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching project permissions:', error);
    return { permissions: [] }; // Return empty permissions on error
  }
};

// ✅ Get available users to grant access to
export const getAvailableUsersForProject = async (projectId) => {
  try {
    console.log(`👥 Fetching available users for Project ${projectId}`);
    const response = await api.get(`/projects/${projectId}/available-users`);
    console.log('✅ Available users fetched:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching available users:', error);
    return []; // Return empty array on error
  }
};

// ✅ NEW: Get ALL users for SuperAdmin assignment
export const getAllUsersForAssignment = async (projectId) => {
  try {
    console.log(`👥 Fetching ALL users for assignment to Project ${projectId}`);
    const response = await api.get(`/projects/${projectId}/all-users`);
    console.log('✅ All users for assignment fetched:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching all users for assignment:', error);
    console.log('⚠️ Falling back to regular fetchUsers');
    try {
      const users = await fetchUsers();
      return users || [];
    } catch (fallbackError) {
      console.error('❌ Fallback user fetch failed:', fallbackError);
      return [];
    }
  }
};

// ✅ CRITICAL FIX: Get assigned users - properly handles backend endpoint and fallback
export const getAssignedUsers = async (projectId) => {
  try {
    console.log(`📋 Fetching assigned users for Project ${projectId}`);
    
    // Try the dedicated assigned-users endpoint first
    const response = await api.get(`/projects/${projectId}/assigned-users`);
    console.log('✅ Assigned users fetched via dedicated endpoint:', response.data);
    return response.data;
    
  } catch (specificError) {
    console.log('⚠️ Assigned users endpoint failed, using permissions fallback');
    
    try {
      // Fallback to permissions endpoint
      const permissionsResponse = await getProjectPermissions(projectId);
      const assignedUsers = permissionsResponse.permissions || [];
      
      // Transform permissions to assigned users format
      const transformedUsers = assignedUsers.map(perm => ({
        user_id: perm.user_id,
        user_email: perm.user_email,
        user_role: perm.user_role || 'user',
        assigned_at: perm.granted_at,
        assigned_by: perm.granted_by || 'System'
      }));
      
      console.log('✅ Using permissions as assigned users:', transformedUsers);
      
      return {
        project_id: projectId,
        project_name: 'Unknown',
        project_owner: 'Unknown',
        assigned_users: transformedUsers
      };
    } catch (fallbackError) {
      console.error('❌ Fallback permissions fetch failed:', fallbackError);
      return { 
        project_id: projectId,
        assigned_users: [] 
      };
    }
  }
};

// ✅ NEW: Revoke project assignment
export const revokeProjectAssignment = async (projectId, userId) => {
  try {
    console.log(`🚫 Revoking assignment: Project ${projectId} from User ${userId}`);
    
    // Try dedicated revoke assignment endpoint first
    try {
      const response = await api.delete(`/projects/${projectId}/revoke-assignment/${userId}`);
      console.log('✅ Assignment revoked via dedicated endpoint:', response.data);
      return response.data;
    } catch (specificError) {
      console.log('⚠️ Specific revoke endpoint not available, using access revoke');
      // Fallback to regular access revoke
      return await revokeProjectAccess(projectId, userId);
    }
  } catch (error) {
    console.error('❌ Error revoking assignment:', error);
    throw error;
  }
};

// Updated: Get projects (now returns only accessible projects)
export const getProjects = async () => {
  try {
    const response = await api.get('/projects/');
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching projects:', error);
    throw error;
  }
};

export const toggleUserStatus = async (userId) => {
  try {
    const response = await api.put(`/admin/users/${userId}/toggle`);
    return response.data;
  } catch (error) {
    console.error("❌ Toggle user status failed:", error);
    throw error;
  }
};
/* ======================
      CHAT SESSION API
====================== */


// Get all chat sessions for user
export const getChatSessions = async (projectId = null) => {
  try {
    console.log('📋 Getting user chat sessions...');
    const params = projectId ? { project_id: projectId } : {};
    const response = await api.get('/chat/sessions', { params });
    console.log('✅ User chat sessions retrieved:', response.data?.length || 0);
    return response.data;
  } catch (error) {
    console.error('❌ Get chat sessions failed:', error.response?.data || error.message);
    throw error;
  }
};

// ✅ UPDATED: Create new chat session with user association
export const createChatSession = async (projectId, title = 'New Chat') => {
  try {
    const payload = {
      title: title || 'New Chat'
    };
    
    // Only add project_id if it's a valid number
    if (projectId && !isNaN(Number(projectId))) {
      payload.project_id = Number(projectId);
    }
    
    console.log('📤 Creating user chat session with payload:', JSON.stringify(payload, null, 2));
    
    const response = await api.post('/chat/sessions', payload);
    
    console.log('✅ User session created with ID:', response.data.id);
    return response.data;
  } catch (error) {
    console.error('❌ Create session API error:', error.response?.data);
    throw error;
  }
};

// Get session details with messages (user-filtered)
export const getChatSessionDetail = async (sessionId) => {
  try {
    console.log('📋 Getting user session detail for:', sessionId);
    const response = await api.get(`/chat/sessions/${sessionId}`);
    console.log('✅ User session detail retrieved');
    return response.data;
  } catch (error) {
    console.error('❌ Get session detail failed:', error.response?.data || error.message);
    throw error;
  }
};

// Update session (user-owned only)
export const updateChatSession = async (sessionId, updates) => {
  try {
    console.log('✏️ Updating user session:', sessionId, updates);
    const response = await api.put(`/chat/sessions/${sessionId}`, updates);
    console.log('✅ User session updated successfully');
    return response.data;
  } catch (error) {
    console.error('❌ Update chat session failed:', error.response?.data || error.message);
    throw error;
  }
};

// Delete session (user-owned only)
export const deleteChatSession = async (sessionId) => {
  try {
    console.log('🗑️ Deleting user session:', sessionId);
    const response = await api.delete(`/chat/sessions/${sessionId}`);
    console.log('✅ User session deleted successfully');
    return response.data;
  } catch (error) {
    console.error('❌ Delete chat session failed:', error.response?.data || error.message);
    throw error;
  }
};

// 🔥 FIXED: Ask question in user session with PROJECT_ID parameter
// export const askQuestionInSession = async (sessionId, query, useContext = true, selectedFiles = [], projectId = null) => {
//   try {
//     console.log('🔍 ASKING QUESTION IN USER SESSION:');
//     console.log('  Session ID:', sessionId);
//     console.log('  Query:', query);
//     console.log('  Use Context:', useContext);
//     console.log('  Selected Files:', selectedFiles);
//     console.log('  🔥 PROJECT ID:', projectId); // 🔥 NEW DEBUG LOG
    
//     // Validate inputs
//     if (!sessionId || !query?.trim()) {
//       throw new Error('Session ID and query are required');
//     }
    
//     const requestPayload = {
//       query: String(query).trim(),
//       use_context: Boolean(useContext),
//       selected_files: Array.isArray(selectedFiles) ? selectedFiles : []
//     };
    
//     // 🔥 ADD PROJECT_ID TO PAYLOAD
//     if (projectId !== null && !isNaN(Number(projectId))) {
//       requestPayload.project_id = Number(projectId);
//       console.log('🔥 Added project_id to payload:', requestPayload.project_id);
//     }
    
//     console.log('📤 REQUEST PAYLOAD:', JSON.stringify(requestPayload, null, 2));
    
//     const response = await api.post(`/chat/sessions/${sessionId}/ask`, requestPayload);
    
//     console.log('✅ DATABASE RESPONSE:');
//     console.log('  Answer Length:', response.data.answer?.length);
//     console.log('  Message ID:', response.data.message_id);
//     console.log('  User Message ID:', response.data.user_message_id);
//     console.log('  Sources Count:', response.data.sources?.length || 0);
//     console.log('  Context Used:', response.data.context_used);
    
//     return response.data;
//   } catch (error) {
//     console.error('❌ SESSION QUESTION ERROR:', {
//       status: error.response?.status,
//       data: error.response?.data,
//       message: error.message
//     });
    
//     // Handle specific error cases
//     if (error.response?.status === 422) {
//       throw new Error(`Invalid request: ${JSON.stringify(error.response.data.detail)}`);
//     }
    
//     if (error.response?.status === 404) {
//       throw new Error('Chat session not found or you do not have access.');
//     }
    
//     if (error.response?.status === 403) {
//       throw new Error('Access denied to this chat session.');
//     }
    
//     throw error;
//   }
// };

// Get conversation context (user-filtered)
export const getChatContext = async (sessionId) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionId}/context`);
    return response.data;
  } catch (error) {
    console.error('❌ Get chat context failed:', error);
    throw error;
  }
};

// ✅ FALLBACK: General question for non-session queries
export const askGeneralQuestion = async (query) => {
  try {
    console.log('🔍 Asking general question:', query);
    const response = await api.post('/chat/general', {
      query: String(query).trim(),
    });
    console.log('✅ General question answered');
    return response.data;
  } catch (error) {
    console.error('❌ General question failed:', error.response?.data || error.message);
    // Return fallback response
    return {
      answer: "I'm your AI assistant! I can help with general questions. For document analysis, please select a project from the sidebar.",
      sources: [],
      context_used: false,
      message_id: `general-${Date.now()}`
    };
  }
};



/* ======================
   LANGGRAPH INTEGRATION
   ====================== */

// 🔥 NEW: LangGraph-powered session query with streaming support
export const askQuestionInSessionLangGraph = async (
  sessionId, 
  query, 
  useContext = true, 
  selectedFiles = [], 
  projectId = null,
  onStream = null
) => {
  try {
    console.log('🚀 LANGGRAPH SESSION QUERY:');
    console.log('   Session ID:', sessionId);
    console.log('   Query:', query);
    console.log('   Project ID:', projectId);
    console.log('   Streaming:', !!onStream);

    // Validate inputs
    if (!sessionId || !query?.trim()) {
      throw new Error('Session ID and query are required');
    }

    const requestPayload = {
      query: String(query).trim(),
      use_context: Boolean(useContext),
      selected_files: Array.isArray(selectedFiles) ? selectedFiles : []
    };

    // Add project_id to payload if provided
    if (projectId !== null && !isNaN(Number(projectId))) {
      requestPayload.project_id = Number(projectId);
      console.log('   Added project_id to payload:', requestPayload.project_id);
    }

    console.log('📤 LANGGRAPH REQUEST PAYLOAD:', JSON.stringify(requestPayload, null, 2));

    // If streaming callback provided, use streaming endpoint (future enhancement)
    if (onStream) {
      // TODO: Implement Server-Sent Events (SSE) streaming
      // For now, fall back to regular request
      console.log('⚠️ Streaming not yet implemented, using regular request');
    }

    const response = await api.post(`/chat/sessions/${sessionId}/ask`, requestPayload);

    console.log('✅ LANGGRAPH RESPONSE:');
    console.log('   Answer Length:', response.data.answer?.length);
    console.log('   Intent:', response.data.intent);
    console.log('   Documents Retrieved:', response.data.documents_retrieved);
    console.log('   Sources Count:', response.data.sources?.length || 0);
    console.log('   Context Used:', response.data.context_used);
    console.log('   Enhanced Query:', response.data.enhanced_query);
    console.log('   Agent System:', response.data.agent_system || 'standard');

    return response.data;

  } catch (error) {
    console.error('❌ LANGGRAPH SESSION ERROR:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });

    // Handle specific error cases
    if (error.response?.status === 422) {
      throw new Error(`Invalid request: ${JSON.stringify(error.response.data.detail)}`);
    }
    
    if (error.response?.status === 404) {
      throw new Error('Chat session not found or you do not have access.');
    }
    
    if (error.response?.status === 403) {
      throw new Error('Access denied to this chat session.');
    }

    throw error;
  }
};

// 🔥 NEW: Get LangGraph workflow status (for debugging)
export const getLangGraphStatus = async () => {
  try {
    const response = await api.get('/langgraph/status');
    return response.data;
  } catch (error) {
    console.error('❌ Get LangGraph status failed:', error);
    return { available: false, error: error.message };
  }
};

// Update the original function to use LangGraph by default
// export const askQuestionInSessionOriginal = askQuestionInSession; // Backup original

// Override with LangGraph version
export { askQuestionInSessionLangGraph as askQuestionInSession };



export default api;
