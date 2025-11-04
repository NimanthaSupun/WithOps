import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Auth state
export const user = writable(null);
export const loading = writable(false);
export const error = writable(null);

// Theme store
function createThemeStore() {
	const { subscribe, set, update } = writable(false);

	return {
		subscribe,
		// Initialize theme from localStorage
		init: () => {
			if (browser) {
				const savedTheme = localStorage.getItem('theme');
				const isDark = savedTheme === 'dark';
				set(isDark);

				// Apply theme to document root for global theming
				if (isDark) {
					document.documentElement.classList.add('dark');
				} else {
					document.documentElement.classList.remove('dark');
				}
			}
		},
		// Toggle theme and persist to localStorage
		toggle: () => {
			update((isDark) => {
				const newIsDark = !isDark;
				if (browser) {
					localStorage.setItem('theme', newIsDark ? 'dark' : 'light');
					if (newIsDark) {
						document.documentElement.classList.add('dark');
					} else {
						document.documentElement.classList.remove('dark');
					}
				}
				return newIsDark;
			});
		},
		// Set theme directly
		set: (isDark) => {
			set(isDark);
			if (browser) {
				localStorage.setItem('theme', isDark ? 'dark' : 'light');
				if (isDark) {
					document.documentElement.classList.add('dark');
				} else {
					document.documentElement.classList.remove('dark');
				}
			}
		}
	};
}

export const isDarkMode = createThemeStore();

// User-specific GitHub data (SECURE)
export const userOrganizations = writable([]);
export const currentOrganization = writable(null);
export const userInstallations = writable([]);

// App functions
export const appStore = {
	setUser: (userData) => user.set(userData),
	setLoading: (isLoading) => loading.set(isLoading),
	setError: (errorMsg) => error.set(errorMsg),

	clearError: () => error.set(null),
	reset: () => {
		user.set(null);
		loading.set(false);
		error.set(null);
		// Clear user-specific data on reset (logout)
		userOrganizations.set([]);
		currentOrganization.set(null);
		userInstallations.set([]);

		// 🔐 SECURITY FIX: Clear localStorage/sessionStorage
		if (typeof window !== 'undefined') {
			localStorage.removeItem('github_organizations');
			localStorage.removeItem('current_organization');
			localStorage.removeItem('user_installations');
			sessionStorage.clear();
		}

		console.log('🔐 All stores and storage cleared');
	},

	// User-specific GitHub data management (SECURE)
	setUserOrganizations: (orgs) => userOrganizations.set(orgs),
	setCurrentOrganization: (org) => currentOrganization.set(org),
	setUserInstallations: (installations) => userInstallations.set(installations),

	// Security helper - only allows access to user's organizations
	isUserAuthorizedForOrg: (orgName, userOrgsList) => {
		return userOrgsList.some((org) => org.name === orgName && org.can_access);
	}
};
