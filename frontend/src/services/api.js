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

// Helper to determine if we are in Demo Mode
export const isDemoMode = () => {
  const mode = localStorage.getItem("doc_ai_mode");
  if (mode === null) {
    localStorage.setItem("doc_ai_mode", "demo");
    return true;
  }
  return mode === "demo";
};

// Request interceptor - attach JWT token and log requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
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
    console.log(`✅ API Response: ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const method = error.config?.method?.toUpperCase();
    const url = error.config?.url;
    const message = error.response?.data?.detail || error.message;
    
    console.error(`❌ API Error: ${status} ${method} ${url} - ${message}`);
    
    if (status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      console.warn("🔐 Unauthorized: cleared token & user");
      
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

/* ==========================================================================
   MOCK DATA SYSTEM FOR PORTFOLIO DEMO MODE (PERSISTED IN LOCALSTORAGE)
   ========================================================================== */

const MOCK_CHART_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAHgAAAB4CAYAAAA5y+g3AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5AYMDBQoIif+GgAAADtJREFUeN7t0EERAAAIA6BJ/57VwR+OgKGqaTszMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzF4tX3x15r1wAAAAASUVORK5CYII=";

const DEFAULT_USERS = [
  { id: 1, email: "superadmin@docai.com", role: "superadmin", organization_id: null, is_active: true, organization_name: null },
  { id: 2, email: "orgadmin@docai.com", role: "orgadmin", organization_id: 1, is_active: true, organization_name: "Google Doc-AI Org" },
  { id: 3, email: "user@docai.com", role: "user", organization_id: 1, is_active: true, organization_name: "Google Doc-AI Org" },
  { id: 4, email: "john.doe@docai.com", role: "user", organization_id: 1, is_active: true, organization_name: "Google Doc-AI Org" }
];

const DEFAULT_ORGANIZATIONS = [
  { id: 1, name: "Google Doc-AI Org", description: "Google's internal R&D organization for document artificial intelligence.", created_at: "2026-01-10T12:00:00Z" },
  { id: 2, name: "Acme Corporation", description: "Standard manufacturing and global shipping solutions group.", created_at: "2026-02-15T09:30:00Z" },
  { id: 3, name: "HealthTech Systems", description: "State-of-the-art medical billing and analysis operations.", created_at: "2026-03-20T14:45:00Z" }
];

const DEFAULT_PROJECTS = [
  { id: 101, name: "Medical Research AI", description: "AI-powered analysis of medical research papers and clinical trial guidelines.", creator_id: 3, creator_email: "user@docai.com", created_at: "2026-04-01T10:00:00Z", permission_count: 2 },
  { id: 102, name: "Financial Policy Generator", description: "Automatic generation and verification of financial audit compliance policies.", creator_id: 3, creator_email: "user@docai.com", created_at: "2026-04-15T11:30:00Z", permission_count: 1 },
  { id: 103, name: "Corporate Guidelines", description: "Standard corporate HR policies, onboarding documents, and employee handbooks.", creator_id: 2, creator_email: "orgadmin@docai.com", created_at: "2026-05-01T08:15:00Z", permission_count: 4 }
];

const DEFAULT_FILES = {
  101: [
    { file_id: "f1", name: "clinical_trial_protocols.pdf", file_name: "clinical_trial_protocols.pdf", size: 2048576, upload_date: "2026-04-02T12:00:00Z" },
    { file_id: "f2", name: "fda_approvals_2025.docx", file_name: "fda_approvals_2025.docx", size: 512400, upload_date: "2026-04-03T15:30:00Z" },
    { file_id: "f3", name: "medical_ethics_charter.txt", file_name: "medical_ethics_charter.txt", size: 45000, upload_date: "2026-04-04T09:15:00Z" }
  ],
  102: [
    { file_id: "f4", name: "q4_financial_audit.xlsx", file_name: "q4_financial_audit.xlsx", size: 4096000, upload_date: "2026-04-16T10:20:00Z" },
    { file_id: "f5", name: "compliance_framework_v3.pdf", file_name: "compliance_framework_v3.pdf", size: 1548200, upload_date: "2026-04-17T11:45:00Z" }
  ],
  103: [
    { file_id: "f6", name: "employee_handbook_2026.pdf", file_name: "employee_handbook_2026.pdf", size: 3125000, upload_date: "2026-05-02T09:00:00Z" },
    { file_id: "f7", name: "remote_work_policy.docx", file_name: "remote_work_policy.docx", size: 890000, upload_date: "2026-05-03T14:10:00Z" },
    { file_id: "f8", name: "code_of_conduct.txt", file_name: "code_of_conduct.txt", size: 120000, upload_date: "2026-05-04T10:30:00Z" }
  ]
};

const DEFAULT_CHAT_SESSIONS = [
  { id: 201, title: "Clinical Trial Review", project_id: 101, created_at: "2026-04-05T14:00:00Z", updated_at: "2026-04-05T15:30:00Z", message_count: 2 },
  { id: 202, title: "Compliance Q&A", project_id: 102, created_at: "2026-04-18T10:00:00Z", updated_at: "2026-04-18T10:15:00Z", message_count: 2 },
  { id: 203, title: "General FAQ Chat", project_id: null, created_at: "2026-05-05T09:00:00Z", updated_at: "2026-05-05T09:12:00Z", message_count: 2 }
];

const DEFAULT_CHAT_MESSAGES = {
  201: [
    { id: "m1", message_type: "user", content: "What are the primary safety endpoints in the protocols?", created_at: "2026-04-05T14:02:00Z", message_metadata: '{"context_used":false}' },
    { id: "m2", message_type: "ai", content: "According to page 12 of the `clinical_trial_protocols.pdf`, the primary safety endpoints are defined as:\n\n1. **Adverse Events (TEAEs)**: Incidence of Grade 3 or 4 treatment-emergent adverse events within 28 days.\n2. **Liver Indicators**: Lab abnormalities in liver enzyme values exceeding 3x the upper limit of normal (ULN).\n3. **Serious Events**: Any Serious Adverse Event (SAE) leading to study discontinuation.\n\nAll safety indicators will be reviewed weekly by the Data Safety Monitoring Board (DSMB).", created_at: "2026-04-05T14:03:00Z", message_metadata: '{"context_used":true,"sources":["clinical_trial_protocols.pdf"]}' }
  ],
  202: [
    { id: "m3", message_type: "user", content: "Are there any audit triggers in Q4 report?", created_at: "2026-04-18T10:01:00Z", message_metadata: '{"context_used":false}' },
    { id: "m4", message_type: "ai", content: "Based on the `q4_financial_audit.xlsx` and `compliance_framework_v3.pdf`, there are two potential audit triggers detected:\n\n* **Discrepancy in Intercompany Transactions**: A variance of $234,000 between general ledger accounts and foreign entity entries (exceeds the 2% materiality threshold).\n* **Delayed Compliance Reporting**: Documentation for Q4 tax reserves was signed off 4 business days past the internal deadline.\n\nI recommend resolving the transaction variance before the official external auditor review.", created_at: "2026-04-18T10:02:00Z", message_metadata: '{"context_used":true,"sources":["q4_financial_audit.xlsx","compliance_framework_v3.pdf"]}' }
  ],
  203: [
    { id: "m5", message_type: "user", content: "Can you outline a standard remote work policy?", created_at: "2026-05-05T09:02:00Z", message_metadata: '{"context_used":false}' },
    { id: "m6", message_type: "ai", content: "Certainly! A standard remote work policy typically includes:\n\n1. **Eligibility**: Defines which job roles and performance tiers can work remotely.\n2. **Equipment & Stipends**: Outlines company-provided hardware (laptop, monitor) and utility stipends.\n3. **Core Hours & Responsibilities**: Establishes expected availability (e.g. 9 AM - 5 PM) and response times on messaging platforms.\n4. **Data Security**: Mandates VPN usage, zero-trust logins, and safe physical storage of devices.\n\nYou can customize these sections to align with your organization's operational model.", created_at: "2026-05-05T09:03:00Z", message_metadata: '{"context_used":false}' }
  ]
};

// Simulated LocalStorage getters/setters
const getMockList = (key, defaultList) => {
  const data = localStorage.getItem(key);
  if (!data) {
    localStorage.setItem(key, JSON.stringify(defaultList));
    return defaultList;
  }
  try {
    return JSON.parse(data);
  } catch (e) {
    return defaultList;
  }
};

const saveMockList = (key, list) => {
  localStorage.setItem(key, JSON.stringify(list));
};

// Dynamic Chatbot response generation logic for Demo Mode
const generateSmartMockResponse = (query, selectedFiles = [], projectId = null) => {
  const text = String(query).toLowerCase();
  
  // Check if they want a chart/graph
  const needsChart = text.includes("chart") || text.includes("graph") || text.includes("statistics") || text.includes("numbers") || text.includes("metrics") || text.includes("percentage");
  
  let answer = "";
  let sources = selectedFiles.length > 0 ? selectedFiles : ["System AI Knowledge"];
  
  if (text.includes("hello") || text.includes("hi ") || text.includes("hey")) {
    answer = "Hello! I am your Doc-AI Assistant. I can analyze any document uploaded to your projects and extract key answers, tables, or charts for you. How can I assist you today?";
  } 
  else if (text.includes("trial") || text.includes("clinical") || text.includes("fda") || text.includes("medical") || text.includes("doctor")) {
    answer = "Based on the medical protocols and FDA documents, here are the key findings:\n\n* **Patient Recruitment**: Currently at 85% of target enrollment with 120 active participants across three clinical sites.\n* **Efficacy**: The experimental therapeutic cohort demonstrated a statistically significant 18% reduction in target biomarkers compared to the control group.\n* **FDA Compliance Status**: Phase II dossiers are prepared and fully compliant with FDA guidelines, targeting submission next quarter.";
  }
  else if (text.includes("audit") || text.includes("financial") || text.includes("tax") || text.includes("compliance") || text.includes("money") || text.includes("revenue")) {
    answer = "Applying the audit compliance checks to your selected financial sheets, we see:\n\n1. **Materiality Verification**: All items exceeding the $50,000 threshold have been verified with complete invoice match trails.\n2. **Internal Controls**: Highly robust protocols are in place. However, the sign-off delay noted in Section 3 requires remedial attention.\n3. **Tax Reserves**: Configured adequately according to current accounting principles.";
  }
  else if (text.includes("work") || text.includes("employee") || text.includes("conduct") || text.includes("hr") || text.includes("handbook")) {
    answer = "Analyzing the corporate onboarding handbook and employee files:\n\n* **Workplace Ethics**: Standard zero-tolerance rules are detailed on page 8 of the handbook. \n* **Core Scheduling**: Standard hours are 9:00 AM to 5:00 PM in local time zones, with hybrid schedules requiring manager sign-off.\n* **Security Checklist**: All remote team members must use mandatory secure VPN portals and undergo bi-annual data safety training.";
  }
  else {
    // General response
    answer = `I have analyzed the provided query: "${query}" against your selected project files ${JSON.stringify(sources)}.\n\nEverything appears standard and compliant. The documents support normal operating procedures, and no major risk alerts have been triggered. Let me know if you would like me to compile a specific compliance chart or outline particular sections!`;
  }
  
  if (needsChart) {
    return {
      answer: answer + "\n\n📊 I have automatically compiled a visual metrics breakdown below to help you summarize this data efficiently.",
      sources,
      context_used: true,
      message_id: `msg-ai-${Date.now()}`,
      has_chart: true,
      chartBase64: MOCK_CHART_PNG_BASE64,
      chart_type: "bar"
    };
  }
  
  return {
    answer,
    sources,
    context_used: selectedFiles.length > 0,
    message_id: `msg-ai-${Date.now()}`,
    has_chart: false,
    chartBase64: null,
    chart_type: null
  };
};

/* ======================
      AUTHENTICATION
====================== */
export const loginUser = async (credentials) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking loginUser");
    const users = getMockList("mock_users", DEFAULT_USERS);
    const foundUser = users.find(u => u.email === credentials.email) || {
      id: Date.now(),
      email: credentials.email,
      role: "user",
      organization_id: 1,
      is_active: true,
      organization_name: "Google Doc-AI Org"
    };
    
    const mockToken = `mock-jwt-token-${foundUser.role}-${foundUser.email}`;
    localStorage.setItem("token", mockToken);
    localStorage.setItem("user", JSON.stringify(foundUser));
    return { access_token: mockToken, token_type: "bearer" };
  }

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
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking getCurrentUser");
    const userJson = localStorage.getItem("user");
    if (userJson) {
      return JSON.parse(userJson);
    }
    const token = localStorage.getItem("token") || "mock-jwt-token-user-user@docai.com";
    const role = token.split("-")[3] || "user";
    const email = token.split("-")[4] || "user@docai.com";
    const defaultUser = { id: 3, email, role, organization_id: 1, is_active: true, organization_name: "Google Doc-AI Org" };
    localStorage.setItem("user", JSON.stringify(defaultUser));
    return defaultUser;
  }

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
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking registerUser");
    const users = getMockList("mock_users", DEFAULT_USERS);
    const newUser = {
      id: Date.now(),
      email: userData.email,
      role: userData.role || "user",
      organization_id: userData.organization_id || 1,
      is_active: true,
      organization_name: userData.organization_name || "Google Doc-AI Org"
    };
    users.push(newUser);
    saveMockList("mock_users", users);
    return newUser;
  }

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
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking createProject");
    const projects = getMockList("mock_projects", DEFAULT_PROJECTS);
    const newProj = {
      id: Date.now(),
      project_id: Date.now(),
      name: name,
      project_name: name,
      description: description,
      created_at: new Date().toISOString(),
      creator_id: 3,
      creator_email: "user@docai.com",
      permission_count: 0
    };
    projects.push(newProj);
    saveMockList("mock_projects", projects);
    return newProj;
  }

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

export const fetchProjects = async () => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking fetchProjects");
    return getMockList("mock_projects", DEFAULT_PROJECTS);
  }

  try {
    console.log("📋 Making API request to /projects/");
    const response = await api.get("/projects/");
    return response.data;
  } catch (error) {
    console.error("❌ Frontend fetch error:", error);
    throw error;
  }
};

export const listAllProjectsAdmin = async () => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking listAllProjectsAdmin");
    return getMockList("mock_projects", DEFAULT_PROJECTS);
  }

  try {
    const response = await api.get("/projects/");
    return response.data;
  } catch (error) {
    console.error("❌ List admin projects failed:", error);
    throw error;
  }
};

export const uploadFiles = async (projectId, files, options = {}) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking uploadFiles");
    const allFiles = getMockList("mock_project_files", DEFAULT_FILES);
    const projFiles = allFiles[projectId] || [];
    
    // Simulate upload progress steps
    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += 20;
      if (options.onUploadProgress) {
        options.onUploadProgress({ loaded: currentProgress, total: 100 });
      }
      if (currentProgress >= 100) {
        clearInterval(interval);
      }
    }, 150);

    files.forEach((f, idx) => {
      projFiles.push({
        file_id: `mock-f-${Date.now()}-${idx}`,
        name: f.name,
        file_name: f.name,
        size: f.size || 102400,
        upload_date: new Date().toISOString()
      });
    });

    allFiles[projectId] = projFiles;
    saveMockList("mock_project_files", allFiles);

    // Sleep for simulated upload duration
    await new Promise(resolve => setTimeout(resolve, 800));
    return { message: "Files uploaded successfully", project_id: projectId };
  }

  try {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });
    const response = await api.post(`/upload/${projectId}/upload`, formData, {
      onUploadProgress: options.onUploadProgress,
      timeout: 600000,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  } catch (error) {
    console.error("❌ Upload failed:", error);
    throw error;
  }
};

export const fetchProjectFiles = async (projectId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking fetchProjectFiles for project:", projectId);
    const allFiles = getMockList("mock_project_files", DEFAULT_FILES);
    const files = allFiles[projectId] || [];
    return { files };
  }

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
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking searchFiles");
    return [
      { filename: "compliance_framework_v3.pdf", text: "Section 3.2.1: Audit limits mandate 2% materiality calculations on intercompany operations." },
      { filename: "clinical_trial_protocols.pdf", text: "Page 12: Lab values exceeding 3x ULN represent standard adverse markers." }
    ];
  }

  try {
    const response = await api.post("/query/search_files", { query, project_id: projectId });
    return response.data;
  } catch (error) {
    console.error("❌ Search files failed:", error);
    throw error;
  }
};

export const askQuestion = async (question, selectedFiles, projectId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking askQuestion");
    return generateSmartMockResponse(question, selectedFiles, projectId);
  }

  try {
    const filesArray = Array.isArray(selectedFiles)
      ? selectedFiles.map((f) => (typeof f === "string" ? f : f.filename || f.file_name))
      : [];
    const res = await api.post("/query/ask", { query: question, selected_files: filesArray, project_id: projectId });
    const images = res.data.chartUrl ? [`${BACKEND_URL}${res.data.chartUrl}`] : [];
    return { ...res.data, images };
  } catch (error) {
    console.error("❌ Ask question failed:", error);
    throw error;
  }
};

/* ======================
      USERS & ADMIN
====================== */
export const fetchUsers = async (organizationFilter = null) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking fetchUsers");
    const users = getMockList("mock_users", DEFAULT_USERS);
    if (organizationFilter) {
      return users.filter(u => u.organization_name === organizationFilter || String(u.organization_id) === String(organizationFilter));
    }
    return users;
  }

  try {
    const params = organizationFilter ? { organization_filter: organizationFilter } : {};
    const response = await api.get("/users/", { params });
    return response.data;
  } catch (error) {
    console.error("❌ Fetch users failed:", error);
    throw error;
  }
};

export const fetchUsersWithProjects = async (page = 1, limit = 100) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking fetchUsersWithProjects");
    const users = getMockList("mock_users", DEFAULT_USERS);
    return users.map(u => ({
      ...u,
      projects_owned: 1,
      projects_shared: 2
    }));
  }

  try {
    const response = await api.get("/users/with-projects", { params: { page, limit } });
    return response.data;
  } catch (error) {
    console.error("❌ Fetch users with projects failed:", error);
    throw error;
  }
};

export const getUsersOrganizations = async () => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking getUsersOrganizations");
    const orgs = getMockList("mock_organizations", DEFAULT_ORGANIZATIONS);
    return orgs.map(o => o.name);
  }

  try {
    const response = await api.get("/users/organizations");
    return response.data;
  } catch (error) {
    console.error("❌ Fetch user organizations failed:", error);
    throw error;
  }
};

export const toggleUserActive = async (userId, isActive) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking toggleUserActive");
    const users = getMockList("mock_users", DEFAULT_USERS);
    const updated = users.map(u => u.id === userId ? { ...u, is_active: !u.is_active } : u);
    saveMockList("mock_users", updated);
    return { message: "Status updated successfully" };
  }

  try {
    const response = await api.put(`/users/${userId}/activate`);
    return response.data;
  } catch (error) {
    console.error("❌ Toggle user active failed:", error);
    throw error;
  }
};

export const deleteUser = async (userId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking deleteUser");
    const users = getMockList("mock_users", DEFAULT_USERS);
    const filtered = users.filter(u => u.id !== userId);
    saveMockList("mock_users", filtered);
    return { message: "User deleted successfully" };
  }

  try {
    const response = await api.delete(`/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error("❌ Delete user failed:", error);
    throw error;
  }
};

export const assignUserToOrganization = async (userId, organizationId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking assignUserToOrganization");
    const users = getMockList("mock_users", DEFAULT_USERS);
    const orgs = getMockList("mock_organizations", DEFAULT_ORGANIZATIONS);
    const selectedOrg = orgs.find(o => o.id === organizationId) || { name: "Google Doc-AI Org" };
    
    const updated = users.map(u => u.id === userId ? { ...u, organization_id: organizationId, organization_name: selectedOrg.name } : u);
    saveMockList("mock_users", updated);
    return { message: "User organization assigned successfully" };
  }

  try {
    const response = await api.put(`/users/${userId}/organization`, { organization_id: organizationId });
    return response.data;
  } catch (error) {
    console.error("❌ Assign user to organization failed:", error);
    throw error;
  }
};

export const listUsers = fetchUsers;

/* ======================
      ORGANIZATIONS
====================== */
export const listOrganizations = async () => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking listOrganizations");
    return getMockList("mock_organizations", DEFAULT_ORGANIZATIONS);
  }

  try {
    const response = await api.get("/organizations/");
    return response.data;
  } catch (error) {
    console.error("❌ List organizations failed:", error);
    throw error;
  }
};

export const createOrganization = async (name, adminEmail, adminPassword, description = "") => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking createOrganization");
    const orgs = getMockList("mock_organizations", DEFAULT_ORGANIZATIONS);
    const newOrg = {
      id: Date.now(),
      name,
      description,
      created_at: new Date().toISOString()
    };
    orgs.push(newOrg);
    saveMockList("mock_organizations", orgs);
    return newOrg;
  }

  try {
    const payload = {
      name: name.trim(),
      description: description.trim(),
      admin_email: adminEmail.trim(),
      admin_password: adminPassword,
    };
    const response = await api.post("/organizations/", payload);
    return response.data;
  } catch (error) {
    console.error("❌ Create organization failed:", error);
    throw error;
  }
};

export const deleteOrganization = async (organizationId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking deleteOrganization");
    const orgs = getMockList("mock_organizations", DEFAULT_ORGANIZATIONS);
    const filtered = orgs.filter(o => o.id !== organizationId);
    saveMockList("mock_organizations", filtered);
    return { message: "Organization deleted successfully" };
  }

  try {
    const response = await api.delete(`/organizations/${organizationId}/`);
    return response.data;
  } catch (error) {
    console.error("❌ Delete organization failed:", error);
    throw error;
  }
};

export const updateOrganization = async (organizationId, data) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking updateOrganization");
    const orgs = getMockList("mock_organizations", DEFAULT_ORGANIZATIONS);
    const updated = orgs.map(o => o.id === organizationId ? { ...o, ...data } : o);
    saveMockList("mock_organizations", updated);
    return { message: "Organization updated successfully" };
  }

  try {
    const response = await api.put(`/organizations/${organizationId}/`, data);
    return response.data;
  } catch (error) {
    console.error("❌ Update organization failed:", error);
    throw error;
  }
};

export const createOrganizationUser = async (userData) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking createOrganizationUser");
    return registerUser(userData);
  }

  try {
    const response = await api.post("/organizations/users", userData);
    return response.data;
  } catch (error) {
    console.error("❌ Create organization user failed:", error);
    throw error;
  }
};

export const listOrganizationUsers = async () => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking listOrganizationUsers");
    return fetchUsers();
  }

  try {
    const response = await api.get('/users/');
    return response.data;
  } catch (error) {
    console.error("❌ List organization users failed:", error);
    throw error;
  }
};

export const enhanceQuery = async (query) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking enhanceQuery");
    return `Analyze compliance standards, materiality limits, and key operational controls to verify if the following statement is true and fully substantiated in the files: "${query}"`;
  }

  try {
    const res = await api.post("/query/enhance", { query });
    return res.data.enhanced_query;
  } catch (error) {
    console.error("❌ Query enhancement failed:", error);
    throw error;
  }
};

/* ===============================================
    PROJECT PERMISSION & ASSIGNMENT APIs
=============================================== */
export const grantProjectAccess = async (projectId, userId) => {
  if (isDemoMode()) {
    return { message: "Access granted successfully" };
  }
  try {
    const response = await api.post(`/projects/${projectId}/grant-access`, { user_id: userId });
    return response.data;
  } catch (error) {
    console.error('❌ Error granting project access:', error);
    throw error;
  }
};

export const assignProjectToUser = async (projectId, userId) => {
  if (isDemoMode()) {
    return { message: "Project assigned successfully" };
  }
  try {
    const response = await api.post(`/projects/${projectId}/assign`, { user_id: userId });
    return response.data;
  } catch (error) {
    console.error('❌ Error assigning project:', error);
    throw error;
  }
};

export const revokeProjectAccess = async (projectId, userId) => {
  if (isDemoMode()) {
    return { message: "Access revoked successfully" };
  }
  try {
    const response = await api.delete(`/projects/${projectId}/revoke-access/${userId}`);
    return response.data;
  } catch (error) {
    console.error('❌ Error revoking project access:', error);
    throw error;
  }
};

export const getProjectPermissions = async (projectId) => {
  if (isDemoMode()) {
    return {
      permissions: [
        { user_id: 4, user_email: "john.doe@docai.com", granted_at: new Date().toISOString() }
      ]
    };
  }
  try {
    const response = await api.get(`/projects/${projectId}/permissions`);
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching project permissions:', error);
    return { permissions: [] };
  }
};

export const getAvailableUsersForProject = async (projectId) => {
  if (isDemoMode()) {
    return [
      { id: 4, email: "john.doe@docai.com" }
    ];
  }
  try {
    const response = await api.get(`/projects/${projectId}/available-users`);
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching available users:', error);
    return [];
  }
};

export const getAllUsersForAssignment = async (projectId) => {
  if (isDemoMode()) {
    return DEFAULT_USERS;
  }
  try {
    const response = await api.get(`/projects/${projectId}/all-users`);
    return response.data;
  } catch (error) {
    try {
      const users = await fetchUsers();
      return users || [];
    } catch {
      return [];
    }
  }
};

export const getAssignedUsers = async (projectId) => {
  if (isDemoMode()) {
    return {
      project_id: projectId,
      assigned_users: [
        { user_id: 3, user_email: "user@docai.com", user_role: "user", assigned_at: new Date().toISOString(), assigned_by: "System" }
      ]
    };
  }
  try {
    const response = await api.get(`/projects/${projectId}/assigned-users`);
    return response.data;
  } catch {
    try {
      const permissionsResponse = await getProjectPermissions(projectId);
      const assignedUsers = permissionsResponse.permissions || [];
      const transformedUsers = assignedUsers.map(perm => ({
        user_id: perm.user_id,
        user_email: perm.user_email,
        user_role: perm.user_role || 'user',
        assigned_at: perm.granted_at,
        assigned_by: perm.granted_by || 'System'
      }));
      return {
        project_id: projectId,
        project_name: 'Unknown',
        project_owner: 'Unknown',
        assigned_users: transformedUsers
      };
    } catch {
      return { project_id: projectId, assigned_users: [] };
    }
  }
};

export const revokeProjectAssignment = async (projectId, userId) => {
  if (isDemoMode()) {
    return { message: "Assignment revoked successfully" };
  }
  try {
    const response = await api.delete(`/projects/${projectId}/revoke-assignment/${userId}`);
    return response.data;
  } catch {
    return await revokeProjectAccess(projectId, userId);
  }
};

export const getProjects = async () => {
  if (isDemoMode()) {
    return fetchProjects();
  }
  try {
    const response = await api.get('/projects/');
    return response.data;
  } catch (error) {
    console.error('❌ Error fetching projects:', error);
    throw error;
  }
};

export const toggleUserStatus = async (userId) => {
  if (isDemoMode()) {
    return toggleUserActive(userId, null);
  }
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
export const getChatSessions = async (projectId = null) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking getChatSessions");
    const sessions = getMockList("mock_chat_sessions", DEFAULT_CHAT_SESSIONS);
    if (projectId) {
      return sessions.filter(s => s.project_id === Number(projectId) || s.project_id === String(projectId));
    }
    return sessions;
  }

  try {
    const params = projectId ? { project_id: projectId } : {};
    const response = await api.get('/chat/sessions', { params });
    return response.data;
  } catch (error) {
    console.error('❌ Get chat sessions failed:', error);
    throw error;
  }
};

export const createChatSession = async (projectId, title = 'New Chat') => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking createChatSession");
    const sessions = getMockList("mock_chat_sessions", DEFAULT_CHAT_SESSIONS);
    const newSession = {
      id: Date.now(),
      title,
      project_id: projectId ? Number(projectId) : null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0
    };
    sessions.unshift(newSession);
    saveMockList("mock_chat_sessions", sessions);
    return newSession;
  }

  try {
    const payload = { title: title || 'New Chat' };
    if (projectId && !isNaN(Number(projectId))) {
      payload.project_id = Number(projectId);
    }
    const response = await api.post('/chat/sessions', payload);
    return response.data;
  } catch (error) {
    console.error('❌ Create session API error:', error);
    throw error;
  }
};

export const getChatSessionDetail = async (sessionId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking getChatSessionDetail");
    const sessions = getMockList("mock_chat_sessions", DEFAULT_CHAT_SESSIONS);
    const session = sessions.find(s => s.id === Number(sessionId) || s.id === String(sessionId));
    
    const allMessages = getMockList("mock_chat_messages", DEFAULT_CHAT_MESSAGES);
    const messages = allMessages[sessionId] || [];
    
    return {
      ...session,
      messages
    };
  }

  try {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('❌ Get session detail failed:', error);
    throw error;
  }
};

export const updateChatSession = async (sessionId, updates) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking updateChatSession");
    const sessions = getMockList("mock_chat_sessions", DEFAULT_CHAT_SESSIONS);
    const updated = sessions.map(s => (s.id === Number(sessionId) || s.id === String(sessionId)) ? { ...s, ...updates, updated_at: new Date().toISOString() } : s);
    saveMockList("mock_chat_sessions", updated);
    return { message: "Session updated successfully" };
  }

  try {
    const response = await api.put(`/chat/sessions/${sessionId}`, updates);
    return response.data;
  } catch (error) {
    console.error('❌ Update chat session failed:', error);
    throw error;
  }
};

export const deleteChatSession = async (sessionId) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking deleteChatSession");
    const sessions = getMockList("mock_chat_sessions", DEFAULT_CHAT_SESSIONS);
    const filtered = sessions.filter(s => s.id !== Number(sessionId) && s.id !== String(sessionId));
    saveMockList("mock_chat_sessions", filtered);
    return { message: "Session deleted successfully" };
  }

  try {
    const response = await api.delete(`/chat/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('❌ Delete chat session failed:', error);
    throw error;
  }
};

export const askQuestionInSessionLangGraph = async (
  sessionId, 
  query, 
  useContext = true, 
  selectedFiles = [], 
  projectId = null,
  onStream = null
) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking askQuestionInSessionLangGraph");
    const allMessages = getMockList("mock_chat_messages", DEFAULT_CHAT_MESSAGES);
    const messages = allMessages[sessionId] || [];
    
    // Add user message
    const userMsgId = `m-user-${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      message_type: "user",
      content: query,
      created_at: new Date().toISOString(),
      message_metadata: JSON.stringify({ context_used: false, sources: [] })
    };
    messages.push(userMsg);

    // Generate AI response
    const mockReply = generateSmartMockResponse(query, selectedFiles, projectId);
    
    const aiMsgId = `m-ai-${Date.now()}`;
    const aiMsg = {
      id: aiMsgId,
      message_type: "ai",
      content: mockReply.answer,
      created_at: new Date(Date.now() + 500).toISOString(),
      message_metadata: JSON.stringify({
        context_used: mockReply.context_used,
        sources: mockReply.sources,
        has_chart: mockReply.has_chart,
        chart_base64: mockReply.chartBase64,
        chart_type: mockReply.chart_type
      })
    };
    messages.push(aiMsg);
    
    allMessages[sessionId] = messages;
    saveMockList("mock_chat_messages", allMessages);

    // Update session message count & updated_at
    const sessions = getMockList("mock_chat_sessions", DEFAULT_CHAT_SESSIONS);
    const updatedSessions = sessions.map(s => {
      if (s.id === Number(sessionId) || s.id === String(sessionId)) {
        return {
          ...s,
          message_count: messages.length,
          updated_at: new Date().toISOString()
        };
      }
      return s;
    });
    saveMockList("mock_chat_sessions", updatedSessions);

    // Sleep for simulated analysis typing delay
    await new Promise(resolve => setTimeout(resolve, 800));

    return {
      answer: mockReply.answer,
      message_id: aiMsgId,
      user_message_id: userMsgId,
      sources: mockReply.sources,
      context_used: mockReply.context_used,
      has_chart: mockReply.has_chart,
      chartBase64: mockReply.chartBase64,
      chart_type: mockReply.chart_type,
      intent: "query_document",
      agent_system: "document_analysis"
    };
  }

  try {
    const requestPayload = {
      query: String(query).trim(),
      use_context: Boolean(useContext),
      selected_files: Array.isArray(selectedFiles) ? selectedFiles : []
    };
    if (projectId !== null && !isNaN(Number(projectId))) {
      requestPayload.project_id = Number(projectId);
    }
    const response = await api.post(`/chat/sessions/${sessionId}/ask`, requestPayload);
    return response.data;
  } catch (error) {
    console.error('❌ LANGGRAPH SESSION ERROR:', error);
    throw error;
  }
};

export const getChatContext = async (sessionId) => {
  if (isDemoMode()) {
    return [
      { text: "Demo document context chunk 1", score: 0.92 },
      { text: "Demo document context chunk 2", score: 0.85 }
    ];
  }
  try {
    const response = await api.get(`/chat/sessions/${sessionId}/context`);
    return response.data;
  } catch (error) {
    console.error('❌ Get chat context failed:', error);
    throw error;
  }
};

export const askGeneralQuestion = async (query) => {
  if (isDemoMode()) {
    console.log("🎨 DEMO MODE ACTIVE - mocking askGeneralQuestion");
    const mockReply = generateSmartMockResponse(query, [], null);
    return {
      answer: mockReply.answer,
      sources: [],
      context_used: false,
      message_id: `general-${Date.now()}`
    };
  }

  try {
    const response = await api.post('/chat/general', { query: String(query).trim() });
    return response.data;
  } catch (error) {
    return {
      answer: "I'm your AI assistant! I can help with general questions. For document analysis, please select a project from the sidebar.",
      sources: [],
      context_used: false,
      message_id: `general-${Date.now()}`
    };
  }
};

export const getLangGraphStatus = async () => {
  if (isDemoMode()) {
    return { available: true, status: "healthy", version: "0.2.1" };
  }
  try {
    const response = await api.get('/langgraph/status');
    return response.data;
  } catch (error) {
    return { available: false, error: error.message };
  }
};

// Override with LangGraph version
export { askQuestionInSessionLangGraph as askQuestionInSession };

export default api;
