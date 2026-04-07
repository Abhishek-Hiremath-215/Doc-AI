// ✅ FIXED: Match your backend role names exactly
export const ROLES = {
  SUPERADMIN: 'superadmin',
  ORGADMIN: 'orgadmin', 
  USER: 'user'
};

// Role hierarchy (higher number = more permissions)
export const ROLE_HIERARCHY = {
  [ROLES.USER]: 1,
  [ROLES.ORGADMIN]: 2,
  [ROLES.SUPERADMIN]: 3
};

export const validateUserRole = (userRole, allowedRoles) => {
  if (!userRole || !allowedRoles || allowedRoles.length === 0) {
    return false;
  }
  
  return allowedRoles.includes(userRole); // ✅ No need to normalize
};

export const getDefaultRoute = (userRole) => {
  switch (userRole) {
    case "superadmin":
      return "/super-admin/dashboard";
    case "orgadmin":
      return "/org/dashboard";
    case "user":
      return "/home";
    default:
      return "/login";
  }
};

// ✅ ADD: Get dashboard route helper
export const getDashboardRoute = (role) => {
  return getDefaultRoute(role);
};
