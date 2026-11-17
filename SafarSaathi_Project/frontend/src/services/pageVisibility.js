// Navigation-only switches. Page components and backend routes remain intact.
// Re-enable a page by removing its entry after its content becomes useful.
export const hiddenPages = Object.freeze({
  'officer-login': 'No authentication backend; the old shortcut opened Overview.',
  'disaster-mode': 'Demo exercise only; no emergency backend. Capacity results are available in Simulation Results.',
  notifications: 'No notification feed backend.',
  settings: 'No persisted settings backend.',
  'help-architecture': 'Placeholder health response only; architecture documentation is maintained in the project.',
  'optimization-explanation': 'Duplicates the optimizer tool; formulation and convergence are already available there.',
});

export const isPageVisible = page => !Object.hasOwn(hiddenPages, page);
