export function roleHome(role: string): string {
  if (role === 'astronaut') return '/';
  if (role === 'cmo') return '/crew';
  return '/ground';
}
