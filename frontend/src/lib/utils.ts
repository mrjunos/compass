export function generateSessionId(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  const segments = [3, 4];
  return segments
    .map((len) =>
      Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
    )
    .join('-');
}
