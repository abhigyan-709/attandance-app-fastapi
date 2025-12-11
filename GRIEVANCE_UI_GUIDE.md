# Grievance Portal UI Implementation Guide

## 📋 Overview

Complete UI implementation guide for the IT Rules 2021 compliant Grievance Redressal System with role-based access for Public Users, Authors, and Admins.

---

## 🎯 User Roles & Access

### 1. **Public Users** (No Authentication Required)
- ✅ View grievance information (Officer, SRB, Editors)
- ✅ Submit grievance complaints
- ✅ Track complaint status by Complaint ID

### 2. **Authors** (Authenticated - role: "author")
- ✅ View assigned grievances
- ✅ Update grievance status
- ✅ Add resolution notes
- ✅ View grievance statistics (own assignments)

### 3. **Admins** (Authenticated - role: "admin")
- ✅ View all grievances (dashboard)
- ✅ Manage grievance assignments
- ✅ Configure Grievance Officer
- ✅ Configure Self-Regulatory Body
- ✅ Manage News Editors
- ✅ View comprehensive statistics
- ✅ Bulk operations

---

## 🎨 UI Components

### **Component 1: Public Grievance Information Page**

**Route:** `/grievance` or `/grievance/info`

```tsx
// components/GrievanceInfo.tsx
'use client';

import { useEffect, useState } from 'react';

interface GrievanceOfficer {
  name: string;
  designation: string;
  email: string;
  phone: string;
  address: string;
  working_hours: string;
}

interface SelfRegulatoryBody {
  body_name: string;
  membership_number?: string;
  website_url?: string;
  contact_email?: string;
}

interface NewsEditor {
  name: string;
  designation: string;
  email: string;
  phone?: string;
  bio?: string;
  is_chief_editor: boolean;
}

interface GrievanceInfo {
  grievance_officer: GrievanceOfficer | null;
  self_regulatory_body: SelfRegulatoryBody | null;
  news_editors: NewsEditor[];
  complaint_submission_url: string;
}

export default function GrievanceInfoPage() {
  const [info, setInfo] = useState<GrievanceInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGrievanceInfo();
  }, []);

  const fetchGrievanceInfo = async () => {
    try {
      const response = await fetch('https://api.projectdevops.in/grievance/info');
      const data = await response.json();
      setInfo(data);
    } catch (error) {
      console.error('Failed to fetch grievance info:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white rounded-lg p-8">
        <h1 className="text-4xl font-bold mb-4">Grievance Redressal Mechanism</h1>
        <p className="text-lg opacity-90">
          Submit your complaints regarding content accuracy, privacy concerns, or any violations.
          We aim to resolve all complaints within 15 days.
        </p>
      </div>

      {/* Grievance Officer */}
      {info?.grievance_officer && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <svg className="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Grievance Redressal Officer
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Name</p>
              <p className="font-semibold text-lg">{info.grievance_officer.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Designation</p>
              <p className="font-semibold">{info.grievance_officer.designation}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Email</p>
              <a href={`mailto:${info.grievance_officer.email}`} className="text-blue-600 hover:underline font-semibold">
                {info.grievance_officer.email}
              </a>
            </div>
            <div>
              <p className="text-sm text-gray-600">Phone</p>
              <a href={`tel:${info.grievance_officer.phone}`} className="text-blue-600 hover:underline font-semibold">
                {info.grievance_officer.phone}
              </a>
            </div>
            <div className="md:col-span-2">
              <p className="text-sm text-gray-600">Address</p>
              <p className="font-semibold">{info.grievance_officer.address}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-sm text-gray-600">Working Hours</p>
              <p className="font-semibold">{info.grievance_officer.working_hours}</p>
            </div>
          </div>
        </div>
      )}

      {/* Self Regulatory Body */}
      {info?.self_regulatory_body && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <svg className="w-6 h-6 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            Self-Regulatory Body Membership
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Organization</p>
              <p className="font-semibold text-lg">{info.self_regulatory_body.body_name}</p>
            </div>
            {info.self_regulatory_body.membership_number && (
              <div>
                <p className="text-sm text-gray-600">Membership Number</p>
                <p className="font-semibold">{info.self_regulatory_body.membership_number}</p>
              </div>
            )}
            {info.self_regulatory_body.website_url && (
              <div>
                <p className="text-sm text-gray-600">Website</p>
                <a href={info.self_regulatory_body.website_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-semibold">
                  {info.self_regulatory_body.website_url}
                </a>
              </div>
            )}
            {info.self_regulatory_body.contact_email && (
              <div>
                <p className="text-sm text-gray-600">Contact Email</p>
                <a href={`mailto:${info.self_regulatory_body.contact_email}`} className="text-blue-600 hover:underline font-semibold">
                  {info.self_regulatory_body.contact_email}
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* News Editors */}
      {info?.news_editors && info.news_editors.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <svg className="w-6 h-6 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Editorial Team
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {info.news_editors.map((editor, index) => (
              <div key={index} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                {editor.is_chief_editor && (
                  <span className="inline-block bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full mb-2">
                    Chief Editor
                  </span>
                )}
                <h3 className="font-bold text-lg mb-1">{editor.name}</h3>
                <p className="text-gray-600 text-sm mb-2">{editor.designation}</p>
                {editor.bio && <p className="text-sm text-gray-700 mb-2">{editor.bio}</p>}
                <div className="space-y-1">
                  <a href={`mailto:${editor.email}`} className="text-blue-600 hover:underline text-sm flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    {editor.email}
                  </a>
                  {editor.phone && (
                    <a href={`tel:${editor.phone}`} className="text-blue-600 hover:underline text-sm flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                      </svg>
                      {editor.phone}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Call to Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4">
        <a href="/grievance/submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-center py-4 rounded-lg font-semibold text-lg shadow-lg transition-colors">
          Submit a Complaint
        </a>
        <a href="/grievance/track" className="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-center py-4 rounded-lg font-semibold text-lg shadow-lg transition-colors">
          Track Your Complaint
        </a>
      </div>

      {/* Compliance Notice */}
      <div className="bg-blue-50 border-l-4 border-blue-600 p-4 rounded">
        <p className="text-sm text-gray-700">
          <strong>Note:</strong> This grievance redressal mechanism is established in compliance with the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021. We are committed to addressing your concerns promptly and transparently.
        </p>
      </div>
    </div>
  );
}
```

---

### **Component 2: Submit Grievance Form (Public)**

**Route:** `/grievance/submit`

```tsx
// components/GrievanceSubmitForm.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

const CATEGORIES = [
  { value: 'factual_error', label: 'Factual Error' },
  { value: 'defamation', label: 'Defamation' },
  { value: 'copyright', label: 'Copyright Violation' },
  { value: 'privacy_violation', label: 'Privacy Violation' },
  { value: 'offensive_content', label: 'Offensive Content' },
  { value: 'misinformation', label: 'Misinformation/Fake News' },
  { value: 'other', label: 'Other' }
];

interface FormData {
  complainant_name: string;
  complainant_email: string;
  complainant_phone: string;
  category: string;
  subject: string;
  description: string;
  article_url?: string;
  preferred_resolution?: string;
}

export default function GrievanceSubmitForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [complaintId, setComplaintId] = useState('');
  const [formData, setFormData] = useState<FormData>({
    complainant_name: '',
    complainant_email: '',
    complainant_phone: '',
    category: '',
    subject: '',
    description: '',
    article_url: '',
    preferred_resolution: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('https://api.projectdevops.in/grievance/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        setComplaintId(data.complaint_id);
        setSubmitted(true);
      } else {
        alert('Failed to submit complaint: ' + (data.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error submitting complaint:', error);
      alert('Failed to submit complaint. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold mb-4 text-gray-800">Complaint Submitted Successfully</h2>
          <div className="bg-blue-50 border-l-4 border-blue-600 p-4 mb-6">
            <p className="text-sm text-gray-700 mb-2">Your Complaint ID:</p>
            <p className="text-2xl font-bold text-blue-600">{complaintId}</p>
          </div>
          <p className="text-gray-600 mb-6">
            Please save this Complaint ID for tracking purposes. You will receive an acknowledgment email shortly.
            We aim to resolve your complaint within 15 days.
          </p>
          <div className="flex gap-4">
            <button
              onClick={() => router.push(`/grievance/track?id=${complaintId}`)}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition-colors"
            >
              Track Status
            </button>
            <button
              onClick={() => setSubmitted(false)}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 py-3 rounded-lg font-semibold transition-colors"
            >
              Submit Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Submit Grievance Complaint</h1>
        
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mb-6">
          <p className="text-sm text-gray-700">
            <strong>Important:</strong> All complaints are taken seriously and will be reviewed by our editorial team.
            False or malicious complaints may result in legal action.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Personal Information */}
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="complainant_name"
                value={formData.complainant_name}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your full name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                name="complainant_email"
                value={formData.complainant_email}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="your.email@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                name="complainant_phone"
                value={formData.complainant_phone}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="+91-XXXXXXXXXX"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Complaint Category <span className="text-red-500">*</span>
              </label>
              <select
                name="category"
                value={formData.category}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select a category</option>
                {CATEGORIES.map(cat => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Complaint Details */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subject <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="subject"
              value={formData.subject}
              onChange={handleChange}
              required
              maxLength={200}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Brief summary of your complaint"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Article/Content URL (if applicable)
            </label>
            <input
              type="url"
              name="article_url"
              value={formData.article_url}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="https://..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Detailed Description <span className="text-red-500">*</span>
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              required
              rows={6}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Please provide detailed information about your complaint..."
            />
            <p className="text-sm text-gray-500 mt-1">
              {formData.description.length} / 2000 characters
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preferred Resolution (Optional)
            </label>
            <textarea
              name="preferred_resolution"
              value={formData.preferred_resolution}
              onChange={handleChange}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="How would you like this issue to be resolved?"
            />
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white py-3 rounded-lg font-semibold text-lg transition-colors"
            >
              {loading ? 'Submitting...' : 'Submit Complaint'}
            </button>
            <button
              type="button"
              onClick={() => router.push('/grievance')}
              className="px-8 bg-gray-200 hover:bg-gray-300 text-gray-800 py-3 rounded-lg font-semibold transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

---

### **Component 3: Track Grievance (Public)**

**Route:** `/grievance/track`

```tsx
// components/GrievanceTracker.tsx
'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

interface StatusHistory {
  status: string;
  timestamp: string;
  notes?: string;
  updated_by?: string;
}

interface ComplaintDetails {
  complaint_id: string;
  status: string;
  submitted_at: string;
  category: string;
  subject: string;
  resolved_at?: string;
  resolution_notes?: string;
  status_history: StatusHistory[];
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  submitted: { label: 'Submitted', color: 'bg-blue-100 text-blue-800' },
  under_review: { label: 'Under Review', color: 'bg-yellow-100 text-yellow-800' },
  in_progress: { label: 'In Progress', color: 'bg-purple-100 text-purple-800' },
  resolved: { label: 'Resolved', color: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800' },
  closed: { label: 'Closed', color: 'bg-gray-100 text-gray-800' }
};

export default function GrievanceTracker() {
  const searchParams = useSearchParams();
  const initialId = searchParams.get('id') || '';

  const [complaintId, setComplaintId] = useState(initialId);
  const [complaint, setComplaint] = useState<ComplaintDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (initialId) {
      trackComplaint(initialId);
    }
  }, [initialId]);

  const trackComplaint = async (id: string) => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`https://api.projectdevops.in/grievance/track/${id}`);
      
      if (response.ok) {
        const data = await response.json();
        setComplaint(data);
      } else {
        setError('Complaint not found. Please check your Complaint ID.');
        setComplaint(null);
      }
    } catch (error) {
      setError('Failed to fetch complaint details. Please try again.');
      setComplaint(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (complaintId.trim()) {
      trackComplaint(complaintId.trim());
    }
  };

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
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Track Your Complaint</h1>

        {/* Search Form */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="flex gap-4">
            <input
              type="text"
              value={complaintId}
              onChange={(e) => setComplaintId(e.target.value)}
              placeholder="Enter your Complaint ID (e.g., GRV-2024-ABCD1234)"
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="px-8 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white py-3 rounded-lg font-semibold transition-colors"
            >
              {loading ? 'Searching...' : 'Track'}
            </button>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Complaint Details */}
        {complaint && (
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-l-4 border-blue-600">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Complaint ID</p>
                  <p className="text-2xl font-bold text-gray-800">{complaint.complaint_id}</p>
                </div>
                <span className={`px-4 py-2 rounded-full text-sm font-semibold ${STATUS_LABELS[complaint.status]?.color || 'bg-gray-100 text-gray-800'}`}>
                  {STATUS_LABELS[complaint.status]?.label || complaint.status}
                </span>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Category</p>
                  <p className="font-semibold capitalize">{complaint.category.replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Submitted On</p>
                  <p className="font-semibold">{formatDate(complaint.submitted_at)}</p>
                </div>
              </div>
            </div>

            {/* Subject */}
            <div className="bg-white border rounded-lg p-6">
              <h3 className="font-semibold text-gray-700 mb-2">Subject</h3>
              <p className="text-gray-800">{complaint.subject}</p>
            </div>

            {/* Resolution (if resolved) */}
            {complaint.status === 'resolved' && complaint.resolution_notes && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <div className="flex items-center mb-3">
                  <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="font-bold text-green-800">Resolution</h3>
                </div>
                <p className="text-gray-700 mb-2">{complaint.resolution_notes}</p>
                {complaint.resolved_at && (
                  <p className="text-sm text-gray-600">Resolved on: {formatDate(complaint.resolved_at)}</p>
                )}
              </div>
            )}

            {/* Status History Timeline */}
            <div className="bg-white border rounded-lg p-6">
              <h3 className="font-bold text-gray-800 mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Status Timeline
              </h3>
              <div className="space-y-4">
                {complaint.status_history?.map((history, index) => (
                  <div key={index} className="flex">
                    <div className="flex flex-col items-center mr-4">
                      <div className={`w-4 h-4 rounded-full ${index === 0 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                      {index < complaint.status_history.length - 1 && (
                        <div className="w-0.5 h-full bg-gray-300 mt-1"></div>
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

            {/* Help Section */}
            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="font-semibold text-gray-800 mb-3">Need Help?</h3>
              <p className="text-sm text-gray-600 mb-4">
                If your complaint is not resolved within 15 days or if you need further assistance, please contact our Grievance Redressal Officer.
              </p>
              <a href="/grievance" className="text-blue-600 hover:underline font-semibold">
                View Contact Information →
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## **Part 2: Author & Admin Dashboard Components** (Continued in next response due to length...)

Would you like me to continue with the Author and Admin dashboard components?
