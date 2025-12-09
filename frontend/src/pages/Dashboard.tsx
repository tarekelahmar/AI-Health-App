import { useEffect, useState } from 'react';
import client from '../api/client';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userRes = await client.get('/users/me');
        setUser(userRes.data);

        const assessmentRes = await client.get(`/assessments/${userRes.data.id}`);
        setAssessment(assessmentRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Health Dashboard</h1>

      {user && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-2">Welcome, {user.name}</h2>
          <p className="text-gray-600">{user.email}</p>
        </div>
      )}

      {assessment && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Detected Issues</h3>
            {assessment.dysfunctions.map((d) => (
              <div key={d.dysfunction_id} className="mb-4 p-4 bg-gray-50 rounded">
                <h4 className="font-semibold">{d.name}</h4>
                <span className={`inline-block mt-2 px-3 py-1 rounded text-white text-sm font-semibold
                  ${d.severity === 'severe' ? 'bg-red-500' : 
                    d.severity === 'moderate' ? 'bg-yellow-500' : 
                    'bg-green-500'}`}>
                  {d.severity.toUpperCase()}
                </span>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
            <button className="w-full bg-blue-600 text-white py-2 rounded mb-2">
              Run Assessment
            </button>
            <button className="w-full bg-blue-600 text-white py-2 rounded mb-2">
              Generate Protocol
            </button>
            <button className="w-full bg-blue-600 text-white py-2 rounded">
              Connect Wearable
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

