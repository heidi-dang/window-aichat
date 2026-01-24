export type AuthStorageMode = 'local' | 'session';

const STORAGE_KEY = 'token';
const MODE_KEY = 'auth_storage_mode';

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
