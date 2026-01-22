import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './components/LoginPage'; // Adjust path if your file is elsewhere
import { jwtDecode } from 'jwt-decode'; // Import jwtDecode
 
// Define props for MainWorkspace
interface MainWorkspaceProps {
  onLogout: () => void;
  currentUserEmail: string | null;
}

// Placeholder for your main Chat/Workspace component. This will eventually be your main application UI.
// Replace this with your actual import, e.g.: import ChatInterface from './ChatInterface';
const MainWorkspace = ({ onLogout }: MainWorkspaceProps) => {
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#1e1e1e', color: 'white' }}>
      <header style={{ padding: '1rem', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>AI Workspace</h2>
        <button 
          onClick={onLogout} 
          style={{ padding: '8px 16px', background: '#333', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Logout
        </button>
      </header>
      <main style={{ flex: 1, padding: '2rem' }}>
        {/* Your actual chat interface component will go here */}
        <p>Welcome! You are logged in.</p>
      </main>
    </div>
  );
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [currentUserEmail, setCurrentUserEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Check for token in localStorage on app load
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decodedToken: { sub: string } = jwtDecode(token);
        setCurrentUserEmail(decodedToken.sub);
        setIsAuthenticated(true);
      } catch (error) {
        console.error("Error decoding token:", error);
        localStorage.removeItem('token'); // Remove invalid token
        setIsAuthenticated(false);
        setCurrentUserEmail(null);
      }
    }
    setIsLoading(false);
  }, []);

  const handleLoginSuccess = (token: string) => {
    setIsAuthenticated(true);
    try {
      const decodedToken: { sub: string } = jwtDecode(token);
      setCurrentUserEmail(decodedToken.sub);
    } catch (error) {
      console.error("Error decoding token on login success:", error);
      setCurrentUserEmail(null);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setCurrentUserEmail(null);
  };

  if (isLoading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#1e1e1e', color: '#888' }}>Loading...</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Login Route: Redirects to Home if already logged in */}
        <Route 
          path="/login" 
          element={
            !isAuthenticated ? (
              <LoginPage onLoginSuccess={handleLoginSuccess} />
            ) : (
              <Navigate to="/" replace />
            )
          } 
        />
        
        {/* Protected Home Route: Redirects to Login if not logged in */}
        <Route 
          path="/" 
          element={
            isAuthenticated ? (
              <MainWorkspace onLogout={handleLogout} currentUserEmail={currentUserEmail} />
            ) : (
              <Navigate to="/login" replace />
            )
          } 
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App
