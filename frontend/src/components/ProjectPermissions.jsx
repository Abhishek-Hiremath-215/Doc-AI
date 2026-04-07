import React, { useState, useEffect } from 'react';
import { 
  getProjectPermissions, 
  getAvailableUsersForProject, 
  grantProjectAccess, 
  revokeProjectAccess 
} from '../services/api';

const ProjectPermissions = ({ projectId, onClose, userRole }) => {
  const [permissions, setPermissions] = useState([]);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [loading, setLoading] = useState(true);
  const [isGranting, setIsGranting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [permissionsData, usersData] = await Promise.all([
        getProjectPermissions(projectId),
        getAvailableUsersForProject(projectId)
      ]);
      setPermissions(permissionsData.permissions || []);
      setAvailableUsers(usersData || []);
      setError('');
    } catch (error) {
      console.error('Error fetching permission data:', error);
      setError('Failed to load permission data');
    } finally {
      setLoading(false);
    }
  };

  const handleGrantAccess = async () => {
    if (!selectedUser) return;
    
    try {
      setIsGranting(true);
      await grantProjectAccess(projectId, selectedUser);
      setSelectedUser('');
      await fetchData(); // Refresh data
    } catch (error) {
      console.error('Error granting access:', error);
      setError('Failed to grant access');
    } finally {
      setIsGranting(false);
    }
  };

  const handleRevokeAccess = async (userId) => {
    try {
      await revokeProjectAccess(projectId, userId);
      await fetchData(); // Refresh data
    } catch (error) {
      console.error('Error revoking access:', error);
      setError('Failed to revoke access');
    }
  };

  // Only org admins and project creators can manage permissions
  const canManagePermissions = userRole === 'orgadmin' || userRole === 'superadmin';

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg">
          <div className="text-center">Loading permissions...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Project Permissions</h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Grant Access Section */}
        {canManagePermissions && availableUsers.length > 0 && (
          <div className="mb-6 p-4 border rounded">
            <h3 className="font-semibold mb-2">Grant Access</h3>
            <div className="flex gap-2">
              <select
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                className="flex-1 p-2 border rounded"
              >
                <option value="">Select a user...</option>
                {availableUsers.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.email} ({user.role})
                  </option>
                ))}
              </select>
              <button
                onClick={handleGrantAccess}
                disabled={!selectedUser || isGranting}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
              >
                {isGranting ? 'Granting...' : 'Grant Access'}
              </button>
            </div>
          </div>
        )}

        {/* Current Permissions */}
        <div>
          <h3 className="font-semibold mb-2">Users with Access</h3>
          {permissions.length === 0 ? (
            <p className="text-gray-500">No additional users have access to this project.</p>
          ) : (
            <div className="space-y-2">
              {permissions.map(permission => (
                <div key={permission.user_id} className="flex justify-between items-center p-3 border rounded">
                  <div>
                    <div className="font-medium">{permission.user_email}</div>
                    <div className="text-sm text-gray-500">
                      Granted by {permission.granted_by} on {new Date(permission.granted_at).toLocaleDateString()}
                    </div>
                  </div>
                  {canManagePermissions && (
                    <button
                      onClick={() => handleRevokeAccess(permission.user_id)}
                      className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                    >
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProjectPermissions;
