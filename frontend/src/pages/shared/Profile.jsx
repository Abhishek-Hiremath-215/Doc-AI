// src/pages/shared/Profile.jsx
import React, { useEffect, useState } from "react";
import { getCurrentUser } from "../../services/api";

const Profile = () => {
  const [me, setMe] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const u = await getCurrentUser();
        setMe(u);
      } catch {
        // ignore
      }
    })();
  }, []);

  if (!me) return <div className="p-4">Loading...</div>;

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Profile</h1>
      <div className="border rounded p-4 bg-white">
        <div className="mb-2"><span className="text-gray-500 text-sm">Email:</span> <div>{me.email}</div></div>
        <div className="mb-2"><span className="text-gray-500 text-sm">Role:</span> <div>{me.role}</div></div>
        <div className="mb-2"><span className="text-gray-500 text-sm">Organization:</span> <div>{me.organization_id || "-"}</div></div>
        <div className="mb-2"><span className="text-gray-500 text-sm">User ID:</span> <div>{me.id}</div></div>
      </div>
    </div>
  );
};

export default Profile;
