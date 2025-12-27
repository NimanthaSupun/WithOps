/**
 * Conversations API Client
 * Manages chat conversations with CRUD operations
 */

const BASE_URL = 'http://localhost:9108/api';

export const conversationsAPI = {
	/**
	 * Create a new conversation
	 */
	async createConversation(data, token) {
		const response = await fetch(`${BASE_URL}/conversations`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		});

		if (!response.ok) {
			throw new Error(`Failed to create conversation: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * List conversations for a user
	 */
	async listConversations({ analysisId, organizationName, limit = 50, token }) {
		const params = new URLSearchParams();
		if (analysisId) params.append('analysis_id', analysisId);
		if (organizationName) params.append('organization_name', organizationName);
		params.append('limit', limit);

		const response = await fetch(`${BASE_URL}/conversations?${params}`, {
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		if (!response.ok) {
			throw new Error(`Failed to list conversations: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Get a specific conversation
	 */
	async getConversation(conversationId, token) {
		const response = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		if (!response.ok) {
			throw new Error(`Failed to get conversation: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Get conversation with messages
	 */
	async getConversationWithMessages(conversationId, token, limit = 100) {
		const response = await fetch(
			`${BASE_URL}/conversations/${conversationId}/messages?limit=${limit}`,
			{
				headers: {
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!response.ok) {
			throw new Error(`Failed to get conversation messages: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Update conversation (rename)
	 */
	async updateConversation(conversationId, data, token) {
		const response = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		});

		if (!response.ok) {
			throw new Error(`Failed to update conversation: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Delete conversation (soft delete)
	 */
	async deleteConversation(conversationId, token) {
		const response = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
			method: 'DELETE',
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		if (!response.ok) {
			throw new Error(`Failed to delete conversation: ${response.statusText}`);
		}

		return response.json();
	}
};
