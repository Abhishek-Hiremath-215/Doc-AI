// src/pages/admin/AdminDashboard.jsx
import React, { useEffect, useState } from "react";
import { listOrganizations, listUsers, listAllProjectsAdmin } from "../../services/api";

const Stat = ({ label, value }) => (
  <div className="p-4 rounded border bg-white">
    <div className="text-gray-500 text-sm">{label}</div>
    <div className="text-2xl font-semibold">{value}</div>
  </div>
);

const AdminDashboard = () => {
  const [stats, setStats] = useState({ orgs: 0, users: 0, projects: 0 });

  useEffect(() => {
    (async () => {
      try {
        const [orgRes, userRes, projRes] = await Promise.all([
          listOrganizations({ page: 1, limit: 1 }),
          listUsers({ page: 1, limit: 1 }),
          listAllProjectsAdmin(),
        ]);
        setStats({
          orgs: orgRes.total ?? (orgRes.items?.length || 0),
          users: userRes.total ?? (userRes.users?.length || 0),
          projects: (projRes.all_projects?.length || 0),
        });
      } catch {
        // ignore
      }
    })();
  }, []);

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Admin Dashboard</h1>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Stat label="Organizations" value={stats.orgs} />
        <Stat label="Users" value={stats.users} />
        <Stat label="Projects" value={stats.projects} />
      </div>
    </div>
  );
};

export default AdminDashboard;
