import React, { useEffect, useState } from 'react';

// Define props type for type safety
interface LoginPageProps {
  onLoginSuccess: (token: string) => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    // Check for token in URL params (callback from backend redirect)
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    
    if (token) {
      // Save token to storage
      localStorage.setItem('token', token);
      
      // Clean URL history
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // Notify parent component
      if (onLoginSuccess) {
        onLoginSuccess(token);
      }
    }
  }, [onLoginSuccess]);

  const handleLogin = async (provider: 'google' | 'github' | 'apple') => {
    setLoading(true);
    setError('');
    try {
      // Call backend to get the OAuth URL
      const response = await fetch(`/api/auth/login/${provider}`);
      
      if (!response.ok) {
        setError(`Failed to connect to ${provider}`);
        setLoading(false);
        return;
      }

      const data = await response.json();
      
      if (data.url) {
        // Redirect browser to the provider's OAuth page
        window.location.href = data.url;
      } else {
        setError('No redirect URL returned');
        setLoading(false);
      }
    } catch (err: any) {
      console.error("Login error:", err);
      setError(err.message || 'Login failed. Please try again.');
      setLoading(false);
    }
  };

  // Type the styles object for better editor support
  const styles: { [key: string]: React.CSSProperties } = {
    container: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#1e1e1e', color: '#ffffff', fontFamily: 'Segoe UI, sans-serif' },
    card: { backgroundColor: '#252526', padding: '2.5rem', borderRadius: '12px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', width: '100%', maxWidth: '400px', textAlign: 'center' },
    title: { marginBottom: '0.5rem', fontSize: '1.75rem', fontWeight: '600' },
    subtitle: { color: '#a0a0a0', marginBottom: '2rem' },
    error: { color: '#ff6b6b', marginBottom: '1rem', fontSize: '0.9rem', padding: '0.5rem', backgroundColor: 'rgba(255,107,107,0.1)', borderRadius: '4px' },
    buttonGroup: { display: 'flex', flexDirection: 'column', gap: '1rem' },
    button: { padding: '0.8rem', borderRadius: '6px', border: 'none', fontSize: '1rem', cursor: 'pointer', transition: 'transform 0.1s, opacity 0.2s', fontWeight: '500', display: 'flex', alignItems: 'center', justifyContent: 'center' },
    googleBtn: { backgroundColor: '#ffffff', color: '#333333' },
    githubBtn: { backgroundColor: '#24292e', color: '#ffffff' },
    appleBtn: { backgroundColor: '#000000', color: '#ffffff' }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>AI Workspace</h1>
        <p style={styles.subtitle}>Sign in to sync your chats and files</p>
        
        {error && <div style={styles.error}>{error}</div>}

        <div style={styles.buttonGroup}>
          <button onClick={() => handleLogin('google')} style={{...styles.button, ...styles.googleBtn}} disabled={loading}>
            {loading ? 'Connecting...' : 'Continue with Google'}
          </button>
          
          <button onClick={() => handleLogin('github')} style={{...styles.button, ...styles.githubBtn}} disabled={loading}>
            {loading ? 'Connecting...' : 'Continue with GitHub'}
          </button>
          
          <button onClick={() => handleLogin('apple')} style={{...styles.button, ...styles.appleBtn}} disabled={loading}>
            {loading ? 'Connecting...' : 'Continue with Apple'}
          </button>
        </div>
      </div>
    </div>
  );
}