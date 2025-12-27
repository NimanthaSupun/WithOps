/**
 * RAG API Client
 * Handles communication with AI RAG Service for conversational queries
 */

// Use Kong gateway for API calls (same as other services)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const RAG_API_URL = `${API_BASE_URL}/api/rag`;

/**
 * Get Authorization header with JWT token
 */
function getAuthHeader(token) {
	if (!token) {
		throw new Error('Authentication required. Please log in.');
	}
	return {
		'Content-Type': 'application/json',
		Authorization: `Bearer ${token}`
	};
}

/**
 * Send a chat message to the AI assistant
 */
export async function chat({
	question,
	org_name,
	repo_name = null,
	conversation_id = null,
	filters = null,
	project_name = null,
	folder_path = null,
	analysis_scope = 'unified',
	analysis_id = null,
	token = null
}) {
	const response = await fetch(`${RAG_API_URL}/chat`, {
		method: 'POST',
		headers: getAuthHeader(token),
		body: JSON.stringify({
			question,
			org_name,
			repo_name,
			conversation_id,
			filters,
			project_name,
			folder_path,
			analysis_scope,
			analysis_id
		})
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || `Failed to get AI response: ${response.statusText}`);
	}

	return await response.json();
}

/**
 * Get conversation history
 */
export async function getConversation(conversationId, token) {
	const response = await fetch(`${RAG_API_URL}/chat/${conversationId}`, {
		method: 'GET',
		headers: getAuthHeader(token)
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		throw new Error('Failed to fetch conversation');
	}

	return await response.json();
}

/**
 * Clear a conversation
 */
export async function clearConversation(conversationId, token) {
	const response = await fetch(`${RAG_API_URL}/chat/${conversationId}`, {
		method: 'DELETE',
		headers: getAuthHeader(token)
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		throw new Error('Failed to clear conversation');
	}

	return await response.json();
}

/**
 * List all active conversations
 */
export async function listConversations(token) {
	const response = await fetch(`${RAG_API_URL}/chat/conversations`, {
		method: 'GET',
		headers: getAuthHeader(token)
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		throw new Error('Failed to list conversations');
	}

	return await response.json();
}

/**
 * Index workflows for an organization
 */
export async function indexWorkflows({ org_name, repo_name = null, token = null }) {
	const response = await fetch(`${RAG_API_URL}/index/workflows`, {
		method: 'POST',
		headers: getAuthHeader(token),
		body: JSON.stringify({
			org_name,
			repo_name
		})
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		throw new Error('Failed to index workflows');
	}

	return await response.json();
}

/**
 * Index analysis results
 */
export async function indexAnalysis({ org_name, tree_id, token = null }) {
	const response = await fetch(`${RAG_API_URL}/index/analysis`, {
		method: 'POST',
		headers: getAuthHeader(token),
		body: JSON.stringify({
			org_name,
			tree_id
		})
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		throw new Error('Failed to index analysis');
	}

	return await response.json();
}

/**
 * Get indexing status
 */
export async function getIndexStatus(orgName, token) {
	const response = await fetch(`${RAG_API_URL}/index/status/${orgName}`, {
		method: 'GET',
		headers: getAuthHeader(token)
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('Authentication failed. Please log in again.');
		}
		throw new Error('Failed to get index status');
	}

	return await response.json();
}

export const ragAPI = {
	chat,
	getConversation,
	clearConversation,
	listConversations,
	indexWorkflows,
	indexAnalysis,
	getIndexStatus
};
