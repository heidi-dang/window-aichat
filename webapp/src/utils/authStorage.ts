export type AuthStorageMode = 'local' | 'session';

const STORAGE_KEY = 'token';
const MODE_KEY = 'auth_storage_mode';
const CREDENTIALS_KEY = 'auth_credentials';

export function getStorageMode(): AuthStorageMode {
  const mode = localStorage.getItem(MODE_KEY);
  return mode === 'session' ? 'session' : 'local';
}

export function setStorageMode(mode: AuthStorageMode) {
  localStorage.setItem(MODE_KEY, mode);
}

function getStorage(mode: AuthStorageMode): Storage {
  return mode === 'session' ? sessionStorage : localStorage;
}

export function getToken(): string {
  const mode = getStorageMode();
  return getStorage(mode).getItem(STORAGE_KEY) || '';
}

export function setToken(token: string, mode?: AuthStorageMode) {
  const targetMode = mode ?? getStorageMode();
  const storage = getStorage(targetMode);
  const other = targetMode === 'session' ? localStorage : sessionStorage;
  storage.setItem(STORAGE_KEY, token);
  other.removeItem(STORAGE_KEY);
}

export function clearToken() {
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
}

type StoredCredentials = { username: string; password: string };

export function setCredentials(username: string, password: string, mode?: AuthStorageMode) {
  const targetMode = mode ?? getStorageMode();
  const storage = getStorage(targetMode);
  const other = targetMode === 'session' ? localStorage : sessionStorage;
  storage.setItem(CREDENTIALS_KEY, JSON.stringify({ username, password }));
  other.removeItem(CREDENTIALS_KEY);
}

export function getCredentials(): StoredCredentials | null {
  const mode = getStorageMode();
  const raw = getStorage(mode).getItem(CREDENTIALS_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredCredentials;
    if (!parsed.username || !parsed.password) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearCredentials() {
  localStorage.removeItem(CREDENTIALS_KEY);
  sessionStorage.removeItem(CREDENTIALS_KEY);
}
