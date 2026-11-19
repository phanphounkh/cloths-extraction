import adapter from '@sveltejs/adapter-auto';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// SvelteKit 3 is configured here; svelte.config.js is no longer used.
export default defineConfig({
	plugins: [
		sveltekit({
			adapter: adapter()
		})
	]
});
