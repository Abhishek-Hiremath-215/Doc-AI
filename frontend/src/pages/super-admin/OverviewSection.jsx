import React from "react";

const OverviewSection = ({ 
  totalUsers, 
  activeUsers, 
  organizations, 
  projects 
}) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600 mr-4">
              <span className="text-2xl">👥</span>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Users</p>
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
              <p className="text-sm text-gray-600">Organizations</p>
              <p className="text-3xl font-bold text-gray-800">{organizations.length}</p>
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
        <h3 className="text-lg font-semibold mb-4">SuperAdmin Access</h3>
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-xl">ℹ️</span>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>SuperAdmin Access:</strong> You can assign projects to users, grant access permissions, and revoke assignments across the entire system.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewSection;