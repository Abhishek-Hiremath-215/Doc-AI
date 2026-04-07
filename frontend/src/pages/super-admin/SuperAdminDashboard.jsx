import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import Header from "../../components/Header";
import {
  fetchUsers,
  fetchProjects,
  createOrganization,
  listOrganizations,
  toggleUserActive,
  deleteUser,
  assignProjectToUser,
} from "../../services/api";
import { toast } from "react-hot-toast";

// Import components
import ProjectManagementModal from "./ProjectManagementModal";
import OverviewSection from "./OverviewSection";
import UsersSection from "./UsersSection";
import OrganizationsSection from "./OrganizationsSection";
import ProjectsSection from "./ProjectsSection";

const SuperAdminDashboard = () => {
  const { user: currentUser } = useAuth();
  const [activeSection, setActiveSection] = useState("overview");
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingOrganizations, setLoadingOrganizations] = useState(true);
  const [orgName, setOrgName] = useState("");
  const [orgDescription, setOrgDescription] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [creatingOrg, setCreatingOrg] = useState(false);
  const [userSearch, setUserSearch] = useState("");
  const [organizationFilter, setOrganizationFilter] = useState("all");
  const [assigning, setAssigning] = useState({});

  // Project access modal state
  const [selectedProjectForAccess, setSelectedProjectForAccess] = useState(null);
  const [showProjectAccessModal, setShowProjectAccessModal] = useState(false);

  useEffect(() => {
    loadUsers();
    loadProjects();
    loadOrganizations();
  }, []);

  const loadUsers = async () => {
    setLoadingUsers(true);
    try {
      const filterValue = (currentUser?.role === 'superadmin' && organizationFilter !== "all") 
        ? organizationFilter : null;
      const users = await fetchUsers(filterValue);
      setUsers(users || []);
    } catch (err) {
      toast.error("Failed to fetch users");
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => {
    if (activeSection === "users" && currentUser?.role === 'superadmin') {
      loadUsers();
    }
  }, [organizationFilter, currentUser?.role]);

  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      const res = await fetchProjects();
      let projectsData = [];
      if (Array.isArray(res)) {
        projectsData = res;
      } else if (res?.projects) {
        projectsData = res.projects;
      } else if (res?.data) {
        projectsData = res.data;
      }
      
      // Enrich projects with organization names
      projectsData = projectsData.map(project => {
        if (project.organization_id && organizations.length > 0) {
          const org = organizations.find(o => o.id === project.organization_id);
          if (org) {
            project.organization_name = org.name;
            if (!project.organization) {
              project.organization = org;
            }
          }
        }
        return project;
      });
      
      setProjects(projectsData);
    } catch (err) {
      toast.error("Failed to fetch projects");
      setProjects([]);
    } finally {
      setLoadingProjects(false);
    }
  };

  const loadOrganizations = async () => {
    setLoadingOrganizations(true);
    try {
      const organizations = await listOrganizations();
      setOrganizations(organizations || []);
      
      // Reload projects after organizations are loaded to populate org names
      if (projects.length > 0) {
        setTimeout(loadProjects, 100);
      }
    } catch (err) {
      toast.error("Failed to fetch organizations");
    } finally {
      setLoadingOrganizations(false);
    }
  };

  const handleAssignProject = async (projectId, userId) => {
    const user = users.find(u => u.id === userId);
    if (!user) {
      toast.error("User not found");
      return;
    }

    try {
      setAssigning(prev => ({ ...prev, [projectId]: true }));
      await assignProjectToUser(projectId, userId);
      toast.success(`Project assigned to ${user.email} successfully`);
      
      await loadProjects();
      
    } catch (error) {
      console.error('Assignment error:', error);
      toast.error(error?.response?.data?.detail || "Failed to assign project");
    } finally {
      setAssigning(prev => ({ ...prev, [projectId]: false }));
    }
  };

  const handleManageProjectAccess = (project) => {
    setSelectedProjectForAccess(project);
    setShowProjectAccessModal(true);
  };

  const closeProjectAccessModal = () => {
    setShowProjectAccessModal(false);
    setSelectedProjectForAccess(null);
  };

  const totalUsers = users.length;
  const activeUsers = users.filter((u) => u.is_active).length;

  const menuItems = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "users", label: "Users", icon: "👥" },
    { id: "organizations", label: "Organizations", icon: "🏢" },
    { id: "projects", label: "Projects", icon: "📁" },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6">
          <h1 className="text-xl font-bold text-gray-800">Super Admin</h1>
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
        <Header title="Super Admin Dashboard" />
        <main className="flex-1 overflow-auto p-6">
          {activeSection === "overview" && (
            <OverviewSection
              totalUsers={totalUsers}
              activeUsers={activeUsers}
              organizations={organizations}
              projects={projects}
            />
          )}
          
          {activeSection === "users" && (
            <UsersSection
              users={users}
              loadingUsers={loadingUsers}
              userSearch={userSearch}
              setUserSearch={setUserSearch}
              organizationFilter={organizationFilter}
              setOrganizationFilter={setOrganizationFilter}
              organizations={organizations}
              loadUsers={loadUsers}
            />
          )}
          
          {activeSection === "organizations" && (
            <OrganizationsSection
              organizations={organizations}
              loadingOrganizations={loadingOrganizations}
              orgName={orgName}
              setOrgName={setOrgName}
              orgDescription={orgDescription}
              setOrgDescription={setOrgDescription}
              adminEmail={adminEmail}
              setAdminEmail={setAdminEmail}
              adminPassword={adminPassword}
              setAdminPassword={setAdminPassword}
              creatingOrg={creatingOrg}
              setCreatingOrg={setCreatingOrg}
              loadUsers={loadUsers}
              loadOrganizations={loadOrganizations}
            />
          )}
          
          {activeSection === "projects" && (
            <ProjectsSection
              projects={projects}
              users={users}
              loadingProjects={loadingProjects}
              loadProjects={loadProjects}
              assigning={assigning}
              handleAssignProject={handleAssignProject}
              handleManageProjectAccess={handleManageProjectAccess}
            />
          )}
        </main>
      </div>

      {/* Project Access Management Modal */}
      {showProjectAccessModal && selectedProjectForAccess && (
        <ProjectManagementModal
          project={selectedProjectForAccess}
          users={users}
          onClose={closeProjectAccessModal}
          onRefresh={loadProjects}
        />
      )}
    </div>
  );
};

export default SuperAdminDashboard;
