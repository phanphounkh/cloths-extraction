import { defineEnvVars } from '@sveltejs/kit/env';

// Environment variables, available via `$app/env/public` / `$app/env/private`.
// See https://svelte.dev/docs/kit/environment-variables
export const variables = defineEnvVars({
	PUBLIC_API_URL: {
		public: true,
		description: 'Base URL of the FastAPI backend, as reachable from the browser.',
		schema: (value) => (value || 'http://localhost:8000').replace(/\/+$/, '')
	}
});
