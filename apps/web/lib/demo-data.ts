interface DemoManifestEntry {
  key: string;
  file: string;
}

export function buildDemoKey(
  method: string,
  path: string,
  params?: Record<string, string>,
): string {
  if (!params || Object.keys(params).length === 0) {
    return `${method} ${path}`;
  }
  const query = Object.keys(params)
    .sort()
    .map((key) => `${key}=${params[key]}`)
    .join("&");
  return `${method} ${path}?${query}`;
}

async function fetchDemoJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function resolveDemoFixture<T>(
  method: string,
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const key = buildDemoKey(method, path, params);
  const manifest = await fetchDemoJson<DemoManifestEntry[]>("/demo/manifest.json");
  const entry = manifest.find((item) => item.key === key);
  if (!entry) {
    throw new Error(`Demo fixture not found for ${key}`);
  }
  return fetchDemoJson<T>(`/demo/${entry.file}`);
}
