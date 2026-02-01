/**
 * Repository Tree Client
 * Handles repository folder structure for workspace analysis and DevSecOps intelligence
 *
 * COMPLETELY SEPARATE from workflow treeview (github.js ProjectTree methods)
 *
 * Purpose:
 * - Organize repositories in folder structures
 * - Future: Workspace analysis and DevSecOps maturity assessment
 * - Future: AI-powered queries and insights
 * - Future: OWASP DSOMM compliance tracking
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

class RepositoryTreeClient {
	constructor() {
		this.baseUrl = API_BASE_URL;
		console.log('🌲 Repository Tree Client initialized (separate from workflow treeview)');
	}

	/**
	 * Get authentication token from localStorage or sessionStorage
	 */
	getAuthToken() {
		if (typeof window === 'undefined') return null;

		return (
			localStorage.getItem('auth_token') ||
			sessionStorage.getItem('auth_token') ||
			localStorage.getItem('github_token')
		);
	}

	/**
	 * Get repository tree structure for an organization
	 *
	 * @param {string} orgName - Organization name/login
	 * @returns {Promise<{success: boolean, data: Array, metadata: Object, error?: string}>}
	 */
	async getRepositoryTree(orgName) {
		try {
			console.log(`📦 Fetching repository tree for organization: ${orgName}`);

			const response = await fetch(`${this.baseUrl}/api/repository-tree/${orgName}`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${this.getAuthToken()}`
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || errorData.error || 'Failed to get repository tree');
			}

			const data = await response.json();
			console.log(`✅ Repository tree loaded:`, data);

			return {
				success: true,
				data: data.data || [],
				metadata: data.metadata || {}
			};
		} catch (error) {
			console.error('❌ Error getting repository tree:', error);
			return {
				success: false,
				data: [],
				metadata: {},
				error: error.message || 'Failed to get repository tree'
			};
		}
	}

	/**
	 * Save or update repository tree structure
	 *
	 * @param {string} orgName - Organization name/login
	 * @param {Array} treeData - Tree structure with folders and repositories
	 * @param {string} [name] - Optional tree name
	 * @param {string} [description] - Optional description
	 * @returns {Promise<{success: boolean, tree_id?: string, version?: number, message?: string, error?: string}>}
	 */
	async saveRepositoryTree(orgName, treeData, name = 'Repository Structure', description = null) {
		try {
			console.log(`💾 Saving repository tree for organization: ${orgName}`, {
				folders: this._countNodesByType(treeData, 'folder'),
				repositories: this._countNodesByType(treeData, 'repository'),
				workflows: this._countNodesByType(treeData, 'workflow')
			});

			const response = await fetch(`${this.baseUrl}/api/repository-tree/save`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${this.getAuthToken()}`
				},
				body: JSON.stringify({
					organization_login: orgName,
					tree_data: treeData,
					name: name,
					description: description
				})
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || errorData.error || 'Failed to save repository tree');
			}

			const data = await response.json();
			console.log(`✅ Repository tree saved successfully:`, data);

			return {
				success: true,
				tree_id: data.tree_id,
				version: data.version,
				message: data.message || 'Repository tree saved successfully'
			};
		} catch (error) {
			console.error('❌ Error saving repository tree:', error);
			return {
				success: false,
				error: error.message || 'Failed to save repository tree'
			};
		}
	}

	/**
	 * Delete repository tree structure
	 *
	 * @param {string} orgName - Organization name/login
	 * @returns {Promise<{success: boolean, message?: string, error?: string}>}
	 */
	async deleteRepositoryTree(orgName) {
		try {
			console.log(`🗑️ Deleting repository tree for organization: ${orgName}`);

			const response = await fetch(`${this.baseUrl}/api/repository-tree/${orgName}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${this.getAuthToken()}`
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || errorData.error || 'Failed to delete repository tree');
			}

			const data = await response.json();
			console.log(`✅ Repository tree deleted successfully`);

			return {
				success: true,
				message: data.message || 'Repository tree deleted successfully'
			};
		} catch (error) {
			console.error('❌ Error deleting repository tree:', error);
			return {
				success: false,
				error: error.message || 'Failed to delete repository tree'
			};
		}
	}

	/**
	 * Get repository tree statistics
	 *
	 * @param {string} orgName - Organization name/login
	 * @returns {Promise<{success: boolean, statistics?: Object, error?: string}>}
	 */
	async getStatistics(orgName) {
		try {
			console.log(`📊 Fetching repository tree statistics for: ${orgName}`);

			const response = await fetch(`${this.baseUrl}/api/repository-tree/${orgName}/statistics`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${this.getAuthToken()}`
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || errorData.error || 'Failed to get statistics');
			}

			const data = await response.json();
			console.log(`✅ Statistics loaded:`, data.statistics);

			return {
				success: true,
				statistics: data.statistics || {
					total_folders: 0,
					total_repositories: 0,
					total_workflows: 0,
					private_repos: 0,
					public_repos: 0
				}
			};
		} catch (error) {
			console.error('❌ Error getting statistics:', error);
			return {
				success: false,
				statistics: {
					total_folders: 0,
					total_repositories: 0,
					total_workflows: 0,
					private_repos: 0,
					public_repos: 0
				},
				error: error.message || 'Failed to get statistics'
			};
		}
	}

	/**
	 * Helper: Count nodes by type in tree structure
	 * @private
	 */
	_countNodesByType(treeData, type) {
		let count = 0;

		function traverse(nodes) {
			for (const node of nodes) {
				if (node.type === type) {
					count++;
				}
				if (node.children) {
					traverse(node.children);
				}
			}
		}

		traverse(treeData);
		return count;
	}

	/**
	 * Validate tree structure
	 * Ensures all nodes have required fields
	 *
	 * @param {Array} treeData - Tree structure to validate
	 * @returns {boolean} True if valid
	 */
	validateTreeStructure(treeData) {
		if (!Array.isArray(treeData)) {
			console.error('❌ Tree data must be an array');
			return false;
		}

		function validateNode(node, path = 'root') {
			// Required fields
			if (!node.id || !node.name || !node.type) {
				console.error(`❌ Invalid node at ${path}: missing id, name, or type`, node);
				return false;
			}

			// Valid types
			const validTypes = ['folder', 'repository', 'workflow'];
			if (!validTypes.includes(node.type)) {
				console.error(`❌ Invalid node type at ${path}: ${node.type}`, node);
				return false;
			}

			// Validate children recursively
			if (node.children) {
				if (!Array.isArray(node.children)) {
					console.error(`❌ Invalid children at ${path}: must be an array`, node);
					return false;
				}

				for (let i = 0; i < node.children.length; i++) {
					if (!validateNode(node.children[i], `${path}.${node.name}[${i}]`)) {
						return false;
					}
				}
			}

			return true;
		}

		for (let i = 0; i < treeData.length; i++) {
			if (!validateNode(treeData[i], `root[${i}]`)) {
				return false;
			}
		}

		console.log('✅ Tree structure is valid');
		return true;
	}

	/**
	 * Get flattened list of all folders in tree
	 * Useful for folder selection dropdowns
	 *
	 * @param {Array} treeData - Tree structure
	 * @param {number} [depth=0] - Current depth (for indentation)
	 * @returns {Array} Flattened list of folders
	 */
	getFlattenedFolders(treeData, depth = 0) {
		let result = [];

		for (const node of treeData) {
			if (node.type === 'folder') {
				result.push({ ...node, depth });

				if (node.children) {
					result.push(...this.getFlattenedFolders(node.children, depth + 1));
				}
			}
		}

		return result;
	}

	/**
	 * Find a node by ID in tree structure
	 *
	 * @param {Array} treeData - Tree structure
	 * @param {string} nodeId - Node ID to find
	 * @returns {Object|null} Found node or null
	 */
	findNodeById(treeData, nodeId) {
		function search(nodes) {
			for (const node of nodes) {
				if (node.id === nodeId) {
					return node;
				}
				if (node.children) {
					const found = search(node.children);
					if (found) return found;
				}
			}
			return null;
		}

		return search(treeData);
	}

	/**
	 * Count total items in a node (including nested items)
	 *
	 * @param {Object} node - Node to count
	 * @returns {number} Total item count
	 */
	countItemsInNode(node) {
		if (!node || !node.children) return 0;

		let count = 0;
		for (const child of node.children) {
			count++;
			if (child.children) {
				count += this.countItemsInNode(child);
			}
		}
		return count;
	}
}

// Export singleton instance
export const repositoryTreeClient = new RepositoryTreeClient();

// Make available globally for testing and debugging
if (typeof window !== 'undefined') {
	window.repositoryTreeClient = repositoryTreeClient;
	console.log(
		'🧪 Repository Tree client available globally as window.repositoryTreeClient for testing'
	);
}

export default repositoryTreeClient;
