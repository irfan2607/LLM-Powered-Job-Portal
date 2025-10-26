import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = 'http://localhost:5001/api';

function App() {
  const [jobs, setJobs] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [resumeData, setResumeData] = useState(null);
  const [activeTab, setActiveTab] = useState('jobs');

  useEffect(() => {
    fetchJobs();
    // Seed jobs on initial load
    axios.post(`${API_BASE}/jobs/seed`);
  }, []);

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (locationFilter) params.append('location', locationFilter);

      const response = await axios.get(`${API_BASE}/jobs?${params}`);
      setJobs(response.data);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('resume', file);

    try {
      const response = await axios.post(`${API_BASE}/upload-resume`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResumeData(response.data);

      // Get recommendations
      const recsResponse = await axios.get(`${API_BASE}/recommendations/${response.data.candidate_id}`);
      setRecommendations(recsResponse.data);
      setActiveTab('recommendations');
    } catch (error) {
      console.error('Error uploading resume:', error);
      alert('Error processing resume. Please try again.');
    }
  };

  const getMatchColor = (score) => {
    if (score >= 80) return 'bg-green-100 text-green-800';
    if (score >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">AI Job Portal</h1>
          <p className="text-gray-600">LLM-powered job matching</p>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('jobs')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'jobs'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Job Listings
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'upload'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Upload Resume
            </button>
            <button
              onClick={() => setActiveTab('recommendations')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'recommendations'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Recommendations
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Job Search */}
        {activeTab === 'jobs' && (
          <div>
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Search Jobs
                  </label>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Job title or company..."
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Location
                  </label>
                  <input
                    type="text"
                    value={locationFilter}
                    onChange={(e) => setLocationFilter(e.target.value)}
                    placeholder="City, state..."
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>
              <button
                onClick={fetchJobs}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
              >
                Search Jobs
              </button>
            </div>

            <div className="space-y-4">
              {jobs.map(job => (
                <div key={job.id} className="bg-white rounded-lg shadow p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{job.title}</h3>
                      <p className="text-gray-600">{job.company} • {job.location}</p>
                      <p className="text-sm text-gray-500 mt-2">
                        {job.description.substring(0, 200)}...
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">
                        Posted: {new Date(job.posted_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Resume Upload */}
        {activeTab === 'upload' && (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="max-w-md mx-auto">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Upload Your Resume
              </h2>
              <p className="text-gray-600 mb-6">
                Upload your PDF resume to get AI-powered job recommendations
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="resume-upload"
                />
                <label
                  htmlFor="resume-upload"
                  className="cursor-pointer bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 inline-block"
                >
                  Choose PDF File
                </label>
              </div>

              {resumeData && (
                <div className="mt-6 text-left">
                  <h3 className="font-semibold text-gray-900 mb-2">Extracted Information:</h3>
                  <div className="bg-gray-50 p-4 rounded-md">
                    <p className="text-sm text-gray-600">
                      <strong>Skills Found:</strong> {resumeData.skills?.join(', ')}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {activeTab === 'recommendations' && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              AI-Powered Job Recommendations
            </h2>
            
            <div className="space-y-6">
              {recommendations.map((rec, index) => (
                <div key={rec.job_id} className="bg-white rounded-lg shadow p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {rec.job_title}
                      </h3>
                      <p className="text-gray-600">{rec.company} • {rec.location}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getMatchColor(rec.match_score)}`}>
                      {rec.match_score}% Match
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">Matching Skills</h4>
                      <div className="flex flex-wrap gap-1">
                        {rec.matching_skills.map(skill => (
                          <span key={skill} className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">Skills to Learn</h4>
                      <div className="flex flex-wrap gap-1">
                        {rec.missing_skills.map(skill => (
                          <span key={skill} className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <p className="text-gray-600 text-sm">{rec.explanation}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;