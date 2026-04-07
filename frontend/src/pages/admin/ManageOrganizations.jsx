// src/pages/admin/ManageOrganizations.jsx
import React, { useEffect, useState } from "react";
import { listOrganizations, createOrganization, updateOrganization, deleteOrganization } from "../../services/api";
import toast from "react-hot-toast";

const ManageOrganizations = () => {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({ name: "", description: "" });
  const [editing, setEditing] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await listOrganizations({ page, limit });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (e) {
      toast.error(e.detail || "Failed to load organizations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await updateOrganization(editing, form);
        toast.success("Organization updated");
      } else {
        await createOrganization(form);
        toast.success("Organization created");
      }
      setForm({ name: "", description: "" });
      setEditing(null);
      load();
    } catch (e) {
      toast.error(e.detail || "Operation failed");
    }
  };

  const onEdit = (org) => {
    setEditing(org.id);
    setForm({ name: org.name, description: org.description || "" });
  };

  const onDelete = async (id) => {
    if (!confirm("Delete this organization?")) return;
    try {
      await deleteOrganization(id);
      toast.success("Organization deleted");
      load();
    } catch (e) {
      toast.error(e.detail || "Delete failed");
    }
  };

  return (
    <div className="p-4 max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Manage Organizations</h1>

      {/* Create / Edit */}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-6">
        <input
          className="border rounded px-3 py-2"
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))}
          required
        />
        <input
          className="border rounded px-3 py-2"
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))}
        />
        <button className="bg-blue-600 text-white rounded px-4">{editing ? "Update" : "Create"}</button>
      </form>

      {/* Table */}
      <div className="border rounded overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">Name</th>
              <th className="text-left p-3">Description</th>
              <th className="text-left p-3">Created</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="p-3" colSpan={4}>Loading...</td></tr>
            ) : items.length === 0 ? (
              <tr><td className="p-3" colSpan={4}>No organizations</td></tr>
            ) : (
              items.map((org) => (
                <tr key={org.id} className="border-t">
                  <td className="p-3">{org.name}</td>
                  <td className="p-3">{org.description || "-"}</td>
                  <td className="p-3">{new Date(org.created_at).toLocaleString()}</td>
                  <td className="p-3 flex gap-2">
                    <button className="px-3 py-1 rounded bg-gray-200" onClick={() => onEdit(org)}>Edit</button>
                    <button className="px-3 py-1 rounded bg-red-600 text-white" onClick={() => onDelete(org.id)}>Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pager */}
      {total > limit && (
        <div className="mt-4 flex items-center gap-3">
          <button
            disabled={page === 1}
            className="px-3 py-1 rounded border disabled:opacity-50"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Prev
          </button>
          <span>Page {page}</span>
          <button
            disabled={page * limit >= total}
            className="px-3 py-1 rounded border disabled:opacity-50"
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default ManageOrganizations;
