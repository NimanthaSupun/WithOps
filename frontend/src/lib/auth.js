import { createAuth0Client } from '@auth0/auth0-spa-js';

let client;

export async function getAuthClient() {
	if (!client) {
		// Use environment variable for callback URL, but fall back to dynamic origin + /callback
		const callbackUrl =
			import.meta.env.VITE_AUTH0_CALLBACK_URL ||
			(typeof window !== 'undefined'
				? `${window.location.origin}/callback`
				: 'http://localhost:5173/callback');

		console.log('🔐 Creating Auth0 client with:', {
			domain: import.meta.env.VITE_AUTH0_DOMAIN,
			clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
			callbackUrl,
			audience: import.meta.env.VITE_AUTH0_AUDIENCE
		});

		client = await createAuth0Client({
			domain: import.meta.env.VITE_AUTH0_DOMAIN,
			clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
			authorizationParams: {
				redirect_uri: callbackUrl,
				audience: import.meta.env.VITE_AUTH0_AUDIENCE // Add this for API access
			},
			cacheLocation: 'localstorage' // This helps with state management
		});
	}
	return client;
}

// Clear the cached client (call this after logout)
export function clearAuthClient() {
	console.log('🔓 Clearing Auth0 client cache');
	client = null;
}
