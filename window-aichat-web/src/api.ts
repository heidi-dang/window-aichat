export const authenticatedFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = localStorage.getItem('token');
  
  // Use Headers class for easier manipulation
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Automatically handle token expiration by logging the user out
    localStorage.removeItem('token');
    window.location.href = '/login';
  }

  return response;
};