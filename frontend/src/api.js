export const API_BASE = "http://localhost:8000/api";

async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed: ${response.status}`);
  }
  return response.json();
}

export function getHealth() {
  return getJson("/health");
}

export async function getThreads() {
  const data = await getJson("/threads");
  return data.threads;
}