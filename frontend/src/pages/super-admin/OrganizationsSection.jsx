import React from "react";
import { toast } from "react-hot-toast";
import { createOrganization } from "../../services/api";

const OrganizationsSection = ({
  organizations,
  loadingOrganizations,
  orgName,
  setOrgName,
  orgDescription,
  setOrgDescription,
  adminEmail,
  setAdminEmail,
  adminPassword,
  setAdminPassword,
  creatingOrg,
  setCreatingOrg,
  loadUsers,
  loadOrganizations
}) => {
  const handleCreateOrganization = async () => {
    if (!orgName || !adminEmail || !adminPassword) {
      toast.error("Organization name, admin email, and password are required");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminEmail)) {
      toast.error("Please enter a valid email address");
      return;
    }
    if (adminPassword.length < 6) {
      toast.error("Password must be at least 6 characters long");
      return;
    }

    setCreatingOrg(true);
    try {
      const res = await createOrganization(orgName, adminEmail, adminPassword, orgDescription);
      toast.success(`Organization '${res.organization.name}' created successfully!`);
      setOrgName("");
      setOrgDescription("");
      setAdminEmail("");
      setAdminPassword("");
      await Promise.all([loadUsers(), loadOrganizations()]);
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Failed to create organization");
    } finally {
      setCreatingOrg(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Create New Organization</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Organization name *"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            className="border border-gray-300 p-3 rounded-md focus:ring-2 focus:ring-blue-500"
            disabled={creatingOrg}
          />
          <input
            type="email"
            placeholder="Admin email *"
            value={adminEmail}
            onChange={(e) => setAdminEmail(e.target.value)}
            className="border border-gray-300 p-3 rounded-md focus:ring-2 focus:ring-blue-500"
            disabled={creatingOrg}
          />
          <input
            type="password"
            placeholder="Admin password *"
            value={adminPassword}
            onChange={(e) => setAdminPassword(e.target.value)}
            className="border border-gray-300 p-3 rounded-md focus:ring-2 focus:ring-blue-500"
            disabled={creatingOrg}
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={orgDescription}
            onChange={(e) => setOrgDescription(e.target.value)}
            className="border border-gray-300 p-3 rounded-md focus:ring-2 focus:ring-blue-500"
            disabled={creatingOrg}
          />
        </div>
        <button
          onClick={handleCreateOrganization}
          disabled={creatingOrg || !orgName || !adminEmail || !adminPassword}
          className="mt-4 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {creatingOrg ? 'Creating...' : 'Create Organization'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800">All Organizations</h3>
        </div>
        {loadingOrganizations ? (
          <div className="p-6 text-center">Loading organizations...</div>
        ) : organizations.length === 0 ? (
          <div className="p-6 text-center text-gray-500">No organizations created yet</div>
        ) : (
          organizations.map((org) => (
            <div key={org.id} className="p-6 border-b border-gray-100 last:border-b-0">
              <h4 className="text-lg font-medium text-gray-900">{org.name}</h4>
              {org.description && <p className="text-sm text-gray-600 mt-1">{org.description}</p>}
              <p className="text-xs text-gray-500 mt-2">Created: {new Date(org.created_at).toLocaleDateString()}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default OrganizationsSection;