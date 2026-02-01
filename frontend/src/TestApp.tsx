// Simple test component to verify React is working
export default function TestApp() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-2xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          🏦 AI Hedge Fund System
        </h1>
        <p className="text-gray-600 mb-4">
          Frontend is loading successfully!
        </p>
        <div className="space-y-2">
          <p className="text-sm text-gray-500">✅ React: Working</p>
          <p className="text-sm text-gray-500">✅ TypeScript: Working</p>
          <p className="text-sm text-gray-500">✅ Tailwind CSS: Working</p>
          <p className="text-sm text-gray-500">✅ Vite: Working</p>
        </div>
        <div className="mt-6 p-4 bg-blue-50 rounded">
          <p className="text-sm text-blue-800">
            <strong>Next:</strong> Check browser console for any errors
          </p>
        </div>
      </div>
    </div>
  );
}
