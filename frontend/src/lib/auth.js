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
