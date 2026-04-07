import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import {
  getProjectPermissions,
  grantProjectAccess,
  revokeProjectAccess,
  getAvailableUsersForProject,
  getAssignedUsers,
  assignProjectToUser,
} from "../../services/api";

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

      // ✅ CRITICAL: Fetch from BOTH APIs to get complete user access data
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

      // ✅ Add users from permissions API
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

      // ✅ Add users from assigned API (additional source)
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

      // ✅ CRITICAL: Always ensure project owner is included
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

      // ✅ FALLBACK: If no data from APIs, create a manual list based on project info
      if (usersWithAccessMap.size <= 1 && project.permission_count > 0) {
        console.log('⚠️ APIs returned insufficient data, but project shows', project.permission_count, 'users with access');

        // Try to get available users API which might have the data
        try {
          const availableUsersResult = await getAvailableUsersForProject(project.id);
          console.log('📊 Available users result:', availableUsersResult);

          // If we can determine who has access from available users list
          if (availableUsersResult && Array.isArray(availableUsersResult)) {
            const allUserIds = users.map(u => u.id);
            const availableUserIds = availableUsersResult.map(u => u.id);
            const usersWithAccessIds = allUserIds.filter(id => !availableUserIds.includes(id));

            usersWithAccessIds.forEach(userId => {
              if (!usersWithAccessMap.has(userId)) {
                const userInfo = users.find(u => u.id === userId) || {};
                usersWithAccessMap.set(userId, {
                  user_id: userId,
                  user_email: userInfo.email || 'Unknown',
                  user_role: userInfo.role || 'user',
                  organization_name: userInfo.organization?.name || 'No Organization',
                  granted_by: 'System',
                  granted_at: new Date().toISOString(),
                  access_type: userId === project.creator_id ? 'owner' : 'inferred'
                });
              }
            });
          }
        } catch (fallbackError) {
          console.log('⚠️ Fallback method also failed:', fallbackError);
        }
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

      // ✅ Refresh data immediately after granting access
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

export default ProjectManagementModal;