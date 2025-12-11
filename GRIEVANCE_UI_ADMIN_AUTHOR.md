# Grievance Portal UI - Author & Admin Dashboards

## 🎯 Part 2: Author & Admin Components

---

### **Component 4: Author Dashboard**

**Route:** `/author/grievances` (Protected - role: "author")

```tsx
// components/AuthorGrievanceDashboard.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface Complaint {
  _id: string;
  complaint_id: string;
  complainant_name: string;
  category: string;
  subject: string;
  status: string;
  submitted_at: string;
  assigned_to?: string;
}

const STATUS_OPTIONS = [
  { value: 'under_review', label: 'Under Review' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'rejected', label: 'Rejected' }
];

export default function AuthorGrievanceDashboard() {
  const router = useRouter();
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [stats, setStats] = useState({ total: 0, pending: 0, resolved: 0 });

  useEffect(() => {
    fetchComplaints();
  }, [filter]);

  const fetchComplaints = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const url = filter === 'all' 
        ? 'https://api.projectdevops.in/grievance/complaints'
        : `https://api.projectdevops.in/grievance/complaints?status=${filter}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setComplaints(data.complaints || []);
        
        // Calculate stats
        const total = data.total || 0;
        const pending = data.complaints.filter((c: Complaint) => 
          ['submitted', 'under_review', 'in_progress'].includes(c.status)
        ).length;
        const resolved = data.complaints.filter((c: Complaint) => c.status === 'resolved').length;
        
        setStats({ total, pending, resolved });
      } else if (response.status === 403) {
        alert('Access denied. Author role required.');
        router.push('/');
      }
    } catch (error) {
      console.error('Failed to fetch complaints:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      submitted: 'bg-blue-100 text-blue-800',
      under_review: 'bg-yellow-100 text-yellow-800',
      in_progress: 'bg-purple-100 text-purple-800',
      resolved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      closed: 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">My Assigned Grievances</h1>
        <p className="text-gray-600">Manage and resolve complaints assigned to you</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-1">Total Assigned</p>
              <p className="text-3xl font-bold text-gray-800">{stats.total}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-1">Pending</p>
              <p className="text-3xl font-bold text-yellow-600">{stats.pending}</p>
            </div>
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm mb-1">Resolved</p>
              <p className="text-3xl font-bold text-green-600">{stats.resolved}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-2 overflow-x-auto">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('submitted')}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              filter === 'submitted' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            New
          </button>
          <button
            onClick={() => setFilter('under_review')}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              filter === 'under_review' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Under Review
          </button>
          <button
            onClick={() => setFilter('in_progress')}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              filter === 'in_progress' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            In Progress
          </button>
          <button
            onClick={() => setFilter('resolved')}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              filter === 'resolved' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Resolved
          </button>
        </div>
      </div>

      {/* Complaints List */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : complaints.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="text-gray-600 text-lg">No complaints found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Complaint ID
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Complainant
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Subject
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {complaints.map((complaint) => (
                <tr key={complaint._id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="font-mono text-sm text-blue-600">{complaint.complaint_id}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-900">{complaint.complainant_name}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600 capitalize">
                      {complaint.category.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-900 line-clamp-2">{complaint.subject}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(complaint.status)}`}>
                      {complaint.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600">{formatDate(complaint.submitted_at)}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => router.push(`/author/grievances/${complaint._id}`)}
                      className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

---

### **Component 5: Author Complaint Detail Page**

**Route:** `/author/grievances/[id]`

```tsx
// components/AuthorComplaintDetail.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface ComplaintDetails {
  _id: string;
  complaint_id: string;
  complainant_name: string;
  complainant_email: string;
  complainant_phone: string;
  category: string;
  subject: string;
  description: string;
  article_url?: string;
  preferred_resolution?: string;
  status: string;
  submitted_at: string;
  assigned_to?: string;
  resolution_notes?: string;
  resolved_at?: string;
  status_history: Array<{
    status: string;
    timestamp: string;
    notes?: string;
    updated_by?: string;
  }>;
}

const STATUS_OPTIONS = [
  { value: 'under_review', label: 'Under Review', color: 'bg-yellow-500' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-purple-500' },
  { value: 'resolved', label: 'Resolved', color: 'bg-green-500' },
  { value: 'rejected', label: 'Rejected', color: 'bg-red-500' }
];

export default function AuthorComplaintDetail() {
  const params = useParams();
  const router = useRouter();
  const complaintId = params.id as string;

  const [complaint, setComplaint] = useState<ComplaintDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [newStatus, setNewStatus] = useState('');
  const [statusNotes, setStatusNotes] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');

  useEffect(() => {
    fetchComplaintDetails();
  }, [complaintId]);

  const fetchComplaintDetails = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(
        `https://api.projectdevops.in/grievance/complaints/${complaintId}`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setComplaint(data);
        setNewStatus(data.status);
        setResolutionNotes(data.resolution_notes || '');
      } else {
        alert('Failed to fetch complaint details');
        router.push('/author/grievances');
      }
    } catch (error) {
      console.error('Error fetching complaint:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!newStatus) {
      alert('Please select a status');
      return;
    }

    setUpdating(true);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(
        `https://api.projectdevops.in/grievance/complaints/${complaintId}`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            status: newStatus,
            notes: statusNotes,
            resolution_notes: newStatus === 'resolved' ? resolutionNotes : undefined
          })
        }
      );

      if (response.ok) {
        alert('Status updated successfully');
        setStatusNotes('');
        fetchComplaintDetails();
      } else {
        alert('Failed to update status');
      }
    } catch (error) {
      console.error('Error updating status:', error);
      alert('Failed to update status');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!complaint) {
    return null;
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push('/author/grievances')}
          className="text-blue-600 hover:text-blue-800 mb-4 flex items-center"
        >
          <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Grievances
        </button>
        <h1 className="text-3xl font-bold text-gray-800">Complaint Details</h1>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Complaint Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Complaint Info Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Complaint ID</p>
                <p className="text-2xl font-bold text-gray-800 font-mono">{complaint.complaint_id}</p>
              </div>
              <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                STATUS_OPTIONS.find(s => s.value === complaint.status)?.color || 'bg-gray-500'
              } text-white`}>
                {complaint.status.replace('_', ' ').toUpperCase()}
              </span>
            </div>

            <div className="grid md:grid-cols-2 gap-4 mb-6">
              <div>
                <p className="text-sm text-gray-600">Category</p>
                <p className="font-semibold capitalize">{complaint.category.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Submitted On</p>
                <p className="font-semibold">{formatDate(complaint.submitted_at)}</p>
              </div>
            </div>

            <div className="border-t pt-4">
              <h3 className="font-semibold text-gray-700 mb-2">Subject</h3>
              <p className="text-gray-800 mb-4">{complaint.subject}</p>

              <h3 className="font-semibold text-gray-700 mb-2">Description</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{complaint.description}</p>

              {complaint.article_url && (
                <>
                  <h3 className="font-semibold text-gray-700 mb-2 mt-4">Related Article URL</h3>
                  <a
                    href={complaint.article_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline break-all"
                  >
                    {complaint.article_url}
                  </a>
                </>
              )}

              {complaint.preferred_resolution && (
                <>
                  <h3 className="font-semibold text-gray-700 mb-2 mt-4">Preferred Resolution</h3>
                  <p className="text-gray-700">{complaint.preferred_resolution}</p>
                </>
              )}
            </div>
          </div>

          {/* Complainant Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold text-gray-800 mb-4">Complainant Information</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Name</p>
                <p className="font-semibold">{complaint.complainant_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Email</p>
                <a href={`mailto:${complaint.complainant_email}`} className="text-blue-600 hover:underline font-semibold">
                  {complaint.complainant_email}
                </a>
              </div>
              <div>
                <p className="text-sm text-gray-600">Phone</p>
                <a href={`tel:${complaint.complainant_phone}`} className="text-blue-600 hover:underline font-semibold">
                  {complaint.complainant_phone}
                </a>
              </div>
            </div>
          </div>

          {/* Status History */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold text-gray-800 mb-4">Status Timeline</h3>
            <div className="space-y-4">
              {complaint.status_history?.map((history, index) => (
                <div key={index} className="flex">
                  <div className="flex flex-col items-center mr-4">
                    <div className={`w-4 h-4 rounded-full ${index === 0 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                    {index < complaint.status_history.length - 1 && (
                      <div className="w-0.5 flex-1 bg-gray-300 mt-1"></div>
                    )}
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="flex justify-between items-start mb-1">
                      <span className={`font-semibold capitalize ${index === 0 ? 'text-blue-600' : 'text-gray-700'}`}>
                        {history.status.replace('_', ' ')}
                      </span>
                      <span className="text-sm text-gray-500">{formatDate(history.timestamp)}</span>
                    </div>
                    {history.notes && <p className="text-sm text-gray-600">{history.notes}</p>}
                    {history.updated_by && <p className="text-xs text-gray-500 mt-1">by {history.updated_by}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column - Update Status */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow p-6 sticky top-6">
            <h3 className="font-bold text-gray-800 mb-4">Update Status</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  New Status <span className="text-red-500">*</span>
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Status Update Notes
                </label>
                <textarea
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Add any notes about this status update..."
                />
              </div>

              {newStatus === 'resolved' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Resolution Notes <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    rows={5}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Describe how the complaint was resolved..."
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    This will be visible to the complainant
                  </p>
                </div>
              )}

              {newStatus === 'rejected' && (
                <div className="bg-yellow-50 border-l-4 border-yellow-500 p-3">
                  <p className="text-sm text-yellow-800">
                    <strong>Note:</strong> Please provide detailed reasoning in the status notes for rejecting this complaint.
                  </p>
                </div>
              )}

              <button
                onClick={handleUpdateStatus}
                disabled={updating || (newStatus === 'resolved' && !resolutionNotes.trim())}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white py-3 rounded-lg font-semibold transition-colors"
              >
                {updating ? 'Updating...' : 'Update Status'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## **Part 3: Admin Dashboard Components** (Continued...)

Would you like me to continue with the full Admin dashboard and configuration components?
