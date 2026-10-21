const enc = new TextEncoder();
const dec = new TextDecoder();

function bytesToB64(bytes: Uint8Array): string {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function b64ToBytes(b64: string): Uint8Array {
  const s = atob(b64);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

function copyBytes(bytes: Uint8Array): Uint8Array<ArrayBuffer> {
  const out = new Uint8Array(bytes.byteLength);
  out.set(bytes);
  return out;
}

async function derive(password: string, salt: Uint8Array): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: copyBytes(salt), iterations: 120000, hash: 'SHA-256' },
    base,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

export async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', enc.encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export interface SealedFile {
  format: 'reckongrid-aes';
  salt: string;
  iv: string;
  data: string;
}

export async function sealJson(json: string, password: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await derive(password, salt);
  const cipher = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode(json));
  const payload: SealedFile = {
    format: 'reckongrid-aes',
    salt: bytesToB64(salt),
    iv: bytesToB64(iv),
    data: bytesToB64(new Uint8Array(cipher)),
  };
  return JSON.stringify(payload);
}

export function isSealed(text: string): boolean {
  try {
    const v = JSON.parse(text) as Partial<SealedFile>;
    return v.format === 'reckongrid-aes' && typeof v.data === 'string';
  } catch {
    return false;
  }
}

export async function openSealed(text: string, password: string): Promise<string> {
  const payload = JSON.parse(text) as SealedFile;
  const salt = b64ToBytes(payload.salt);
  const iv = b64ToBytes(payload.iv);
  const key = await derive(password, salt);
  const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: copyBytes(iv) }, key, copyBytes(b64ToBytes(payload.data)));
  return dec.decode(plain);
}
