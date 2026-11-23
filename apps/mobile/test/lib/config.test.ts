import { resolveApiBaseUrl } from '@/lib/config';

describe('resolveApiBaseUrl', () => {
  it('falls back to localhost:8000 when unset', () => {
    expect(resolveApiBaseUrl(undefined)).toBe('http://localhost:8000');
    expect(resolveApiBaseUrl('')).toBe('http://localhost:8000');
    expect(resolveApiBaseUrl('   ')).toBe('http://localhost:8000');
  });

  it('trims trailing slashes so concatenation cannot double them', () => {
    expect(resolveApiBaseUrl('http://10.0.2.2:8000/')).toBe('http://10.0.2.2:8000');
    expect(resolveApiBaseUrl('https://api.example.com///')).toBe('https://api.example.com');
  });

  it('keeps a clean URL untouched', () => {
    expect(resolveApiBaseUrl('http://10.0.2.2:8000')).toBe('http://10.0.2.2:8000');
  });
});
