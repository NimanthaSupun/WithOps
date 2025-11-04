/**
 * Simple authentication state manager to prevent redirect loops
 */
class AuthStateManager {
	constructor() {
		this.isAuthenticating = false;
		this.lastAuthCheck = 0;
		this.AUTH_CACHE_TIME = 5000; // Cache auth status for 5 seconds
	}

	setAuthenticating(value) {
		this.isAuthenticating = value;
		if (value) {
			sessionStorage.setItem('auth_in_progress', 'true');
		} else {
			sessionStorage.removeItem('auth_in_progress');
		}
	}

	isCurrentlyAuthenticating() {
		return this.isAuthenticating || sessionStorage.getItem('auth_in_progress') === 'true';
	}

	shouldSkipAuthCheck() {
		const now = Date.now();
		if (now - this.lastAuthCheck < this.AUTH_CACHE_TIME) {
			console.log('🔐 Skipping auth check - too recent');
			return true;
		}
		return false;
	}

	markAuthCheckDone() {
		this.lastAuthCheck = Date.now();
	}

	hasValidToken() {
		const token = localStorage.getItem('auth0_token') || localStorage.getItem('auth_token');

		if (!token || token === 'null' || token.length <= 10) {
			return false;
		}

		// Check if token is expired
		try {
			const parts = token.split('.');
			if (parts.length !== 3) return false;

			const payload = JSON.parse(atob(parts[1]));

			// Check expiration (exp is in seconds, Date.now() is in milliseconds)
			if (payload.exp) {
				const now = Math.floor(Date.now() / 1000);
				if (payload.exp < now) {
					console.log('🕐 Token expired, clearing...');
					localStorage.removeItem('auth0_token');
					localStorage.removeItem('auth_token');
					return false;
				}
			}

			return true;
		} catch (error) {
			console.warn('⚠️ Error validating token:', error);
			// Clear potentially corrupted token
			localStorage.removeItem('auth0_token');
			localStorage.removeItem('auth_token');
			return false;
		}
	}

	clearAuthState() {
		this.isAuthenticating = false;
		this.lastAuthCheck = 0;
		sessionStorage.removeItem('auth_in_progress');
	}
}

export const authState = new AuthStateManager();
