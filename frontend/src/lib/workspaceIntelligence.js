/**
 * Workspace Intelligence API Client
 * Handles analysis, maturity scoring, and findings management
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Get authentication token
 */
function getAuthToken() {
	return (
		localStorage.getItem('auth_token') ||
		localStorage.getItem('auth0_token') ||
		localStorage.getItem('github_token')
	);
}

/**
 * Workspace Intelligence API Client
 */
export const workspaceIntelligenceClient = {
	/**
	 * Trigger organization-wide workspace analysis
	 */
	async analyzeWorkspace(organizationName, treeData, repositoryTreeId, fetchGithubData = false) {
		try {
			const token = getAuthToken();
			if (!token) {
				throw new Error('Authentication required');
			}

			const response = await fetch(`${API_BASE_URL}/api/workspace-intelligence/analyze-workspace`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					organization_name: organizationName,
					tree_data: treeData,
					repository_tree_id: repositoryTreeId,
					fetch_github_data: fetchGithubData
				})
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Failed to start workspace analysis');
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to analyze workspace:', error);
			throw error;
		}
	},

	/**
	 * Trigger analysis for a specific project
	 */
	async analyzeProject(
		organizationName,
		repositoryTreeId,
		projectId,
		projectData,
		fetchGithubData = false
	) {
		try {
			const token = getAuthToken();
			if (!token) {
				throw new Error('Authentication required');
			}

			const response = await fetch(`${API_BASE_URL}/api/workspace-intelligence/analyze-project`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					organization_name: organizationName,
					repository_tree_id: repositoryTreeId,
					project_id: projectId,
					project_data: projectData,
					fetch_github_data: fetchGithubData
				})
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Failed to start project analysis');
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to analyze project:', error);
			throw error;
		}
	},

	/**
	 * Get analysis results by ID
	 */
	async getAnalysis(analysisId) {
		try {
			const token = getAuthToken();
			if (!token) {
				throw new Error('Authentication required');
			}

			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/analysis/${analysisId}`,
				{
					method: 'GET',
					headers: {
						Authorization: `Bearer ${token}`
					}
				}
			);

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Failed to get analysis');
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to get analysis:', error);
			throw error;
		}
	},

	/**
	 * Get latest analysis for a project
	 */
	async getLatestProjectAnalysis(projectId) {
		try {
			const token = getAuthToken();
			if (!token) {
				throw new Error('Authentication required');
			}

			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/project/${projectId}/latest`,
				{
					method: 'GET',
					headers: {
						Authorization: `Bearer ${token}`
					}
				}
			);

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Failed to get project analysis');
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to get project analysis:', error);
			throw error;
		}
	},

	/**
	 * Update finding status
	 */
	async updateFindingStatus(findingId, status) {
		try {
			const token = getAuthToken();
			if (!token) {
				throw new Error('Authentication required');
			}

			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/finding/${findingId}?status=${status}`,
				{
					method: 'PATCH',
					headers: {
						Authorization: `Bearer ${token}`
					}
				}
			);

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Failed to update finding');
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to update finding:', error);
			throw error;
		}
	}
};

/**
 * Helper functions for UI
 */
export const workspaceIntelligenceHelpers = {
	/**
	 * Get maturity level from score
	 */
	getMaturityLevel(score) {
		if (score >= 2.5) return 'Optimized';
		if (score >= 1.5) return 'Managed';
		return 'Initial';
	},

	/**
	 * Get color class for maturity score
	 */
	getMaturityColorClass(score) {
		if (score >= 2.5) return 'text-green-600 dark:text-green-400';
		if (score >= 1.5) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	},

	/**
	 * Get badge class for maturity level
	 */
	getMaturityBadgeClass(level) {
		const classes = {
			Optimized:
				'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border-green-200 dark:border-green-700',
			Managed:
				'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-700',
			Initial:
				'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border-red-200 dark:border-red-700'
		};
		return classes[level] || classes['Initial'];
	},

	/**
	 * Get severity badge class
	 */
	getSeverityBadgeClass(severity) {
		const classes = {
			critical: 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200',
			high: 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200',
			medium: 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200',
			low: 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200',
			info: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
		};
		return classes[severity] || classes['info'];
	},

	/**
	 * Get severity icon
	 */
	getSeverityIcon(severity) {
		const icons = {
			critical: '🔴',
			high: '🟠',
			medium: '🟡',
			low: '🔵',
			info: 'ℹ️'
		};
		return icons[severity] || 'ℹ️';
	},

	/**
	 * Format date
	 */
	formatDate(dateString) {
		if (!dateString) return 'N/A';
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	},

	/**
	 * Calculate percentage
	 */
	calculatePercentage(value, total) {
		if (total === 0) return 0;
		return Math.round((value / total) * 100);
	}
};
