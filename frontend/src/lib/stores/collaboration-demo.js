import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

/**
 * Real-time Collaboration Store using localStorage cross-window sync
 * This provides actual multi-user collaboration features across browser windows/tabs
 */

// Global store for cross-window communication
const STORAGE_KEY = 'threat-model-collaboration';
const USER_STORAGE_KEY = 'collaboration-users';

// Room connection state
export const room = writable(null);
export const isConnected = writable(false);
export const connectionError = writable(null);

// Real-time presence of other users
export const others = writable([]);
export const myPresence = writable({
	cursor: null,
	selection: null,
	userInfo: { name: '', avatar: '', color: '#000000' }
});

// Live storage for collaborative data
export const liveElements = writable([]);
export const liveConnections = writable([]);
export const liveThreats = writable([]);
export const liveMetadata = writable({ zoom: 1.0, panX: 0, panY: 0 });
export const liveComments = writable([]);

// Derived store for online users count
export const onlineUsersCount = derived(others, ($others) => $others.length + 1);

// User colors for identification
export const userColors = derived(others, ($others) => {
	const colors = {};
	$others.forEach((user) => {
		if (user.userInfo?.name && user.userInfo?.color) {
			colors[user.userInfo.name] = user.userInfo.color;
		}
	});
	return colors;
});

// Global collaboration state tracker
let currentModelId = null;
let currentUser = null;
let storageListener = null;

/**
 * Initialize real collaboration for a threat model using localStorage sync
 * @param {string} modelId - The threat model ID
 * @param {Object} userInfo - Current user information
 */
export async function initializeCollaboration(modelId, userInfo = {}) {
	try {
		console.log('🤝 Initializing real collaboration for model:', modelId);

		// Skip initialization if not in browser environment
		if (!browser) {
			console.log('Not in browser environment, skipping collaboration');
			return null;
		}

		currentModelId = modelId;
		currentUser = userInfo; // Set up cross-window communication using localStorage
		const collaborationKey = `${STORAGE_KEY}-${modelId}`;
		const usersKey = `${USER_STORAGE_KEY}-${modelId}`;

		// Initialize user presence
		const users = JSON.parse(localStorage.getItem(usersKey) || '[]');
		const existingUserIndex = users.findIndex((u) => u.id === userInfo.id);

		if (existingUserIndex >= 0) {
			users[existingUserIndex] = {
				...userInfo,
				lastSeen: Date.now(),
				online: true
			};
		} else {
			users.push({
				...userInfo,
				lastSeen: Date.now(),
				online: true
			});
		}

		localStorage.setItem(usersKey, JSON.stringify(users));

		// Initialize storage listener for real-time sync
		if (storageListener) {
			window.removeEventListener('storage', storageListener);
		}

		storageListener = (event) => {
			if (event.key === collaborationKey) {
				try {
					const data = JSON.parse(event.newValue || '{}');
					if (data.elements) liveElements.set(data.elements);
					if (data.connections) liveConnections.set(data.connections);
					if (data.threats) liveThreats.set(data.threats);
					if (data.metadata) liveMetadata.set(data.metadata);
					if (data.comments) liveComments.set(data.comments);
					console.log('📡 Received collaboration update from another window');
				} catch (error) {
					console.error('Error parsing collaboration data:', error);
				}
			} else if (event.key === usersKey) {
				try {
					const users = JSON.parse(event.newValue || '[]');
					const otherUsers = users.filter((u) => u.id !== userInfo.id && u.online);
					others.set(
						otherUsers.map((user) => ({
							connectionId: user.id,
							userInfo: user
						}))
					);
					console.log('👥 Updated online users:', otherUsers.length);
				} catch (error) {
					console.error('Error parsing users data:', error);
				}
			}
		};

		window.addEventListener('storage', storageListener);

		// Load existing data
		try {
			const existingData = JSON.parse(localStorage.getItem(collaborationKey) || '{}');
			if (existingData.elements) liveElements.set(existingData.elements);
			if (existingData.connections) liveConnections.set(existingData.connections);
			if (existingData.threats) liveThreats.set(existingData.threats);
			if (existingData.metadata) liveMetadata.set(existingData.metadata);
			if (existingData.comments) liveComments.set(existingData.comments);
		} catch (error) {
			console.log('No existing collaboration data found');
		}

		// Set up periodic presence update
		const presenceInterval = setInterval(() => {
			updateUserPresence(modelId, userInfo);
		}, 5000); // Update every 5 seconds

		// Clean up offline users
		const cleanupInterval = setInterval(() => {
			cleanupOfflineUsers(modelId);
		}, 10000); // Cleanup every 10 seconds

		// Create mock room object
		const mockRoom = {
			id: `threat-model-${modelId}`,
			updatePresence: (presence) => {
				myPresence.update((current) => ({ ...current, ...presence }));
			},
			cleanup: () => {
				clearInterval(presenceInterval);
				clearInterval(cleanupInterval);
				if (storageListener) {
					window.removeEventListener('storage', storageListener);
				}
				// Mark user as offline
				markUserOffline(modelId, userInfo.id);
			}
		};

		// Update connection state
		room.set(mockRoom);
		isConnected.set(true);
		connectionError.set(null);

		// Load other users
		const otherUsers = users.filter((u) => u.id !== userInfo.id && u.online);
		others.set(
			otherUsers.map((user) => ({
				connectionId: user.id,
				userInfo: user
			}))
		);

		console.log('✅ Real collaboration initialized with cross-window sync');
		console.log('👥 Current online users:', otherUsers.length + 1);
		return mockRoom;
	} catch (error) {
		console.error('❌ Failed to initialize collaboration:', error);
		connectionError.set(error.message);
		isConnected.set(false);
		throw error;
	}
}

function updateUserPresence(modelId, userInfo) {
	if (!browser) return;

	const usersKey = `${USER_STORAGE_KEY}-${modelId}`;
	try {
		const users = JSON.parse(localStorage.getItem(usersKey) || '[]');
		const userIndex = users.findIndex((u) => u.id === userInfo.id);

		if (userIndex >= 0) {
			users[userIndex].lastSeen = Date.now();
			users[userIndex].online = true;
		} else {
			users.push({
				...userInfo,
				lastSeen: Date.now(),
				online: true
			});
		}

		localStorage.setItem(usersKey, JSON.stringify(users));
	} catch (error) {
		console.error('Error updating user presence:', error);
	}
}

function cleanupOfflineUsers(modelId) {
	if (!browser) return;

	const usersKey = `${USER_STORAGE_KEY}-${modelId}`;
	try {
		const users = JSON.parse(localStorage.getItem(usersKey) || '[]');
		const now = Date.now();

		// Mark users as offline instead of removing them
		const updatedUsers = users.map((user) => ({
			...user,
			online: now - user.lastSeen < 30000 // 30 seconds timeout
		}));

		localStorage.setItem(usersKey, JSON.stringify(updatedUsers));

		// Update others store with only online users
		if (currentUser) {
			const otherUsers = updatedUsers.filter((u) => u.id !== currentUser.id && u.online);
			others.set(
				otherUsers.map((user) => ({
					connectionId: user.id,
					userInfo: user
				}))
			);
		}
	} catch (error) {
		console.error('Error cleaning up offline users:', error);
	}
}

function markUserOffline(modelId, userId) {
	if (!browser) return;

	const usersKey = `${USER_STORAGE_KEY}-${modelId}`;
	try {
		const users = JSON.parse(localStorage.getItem(usersKey) || '[]');
		const userIndex = users.findIndex((u) => u.id === userId);

		if (userIndex >= 0) {
			users[userIndex].online = false;
			users[userIndex].lastSeen = Date.now();
			localStorage.setItem(usersKey, JSON.stringify(users));
		}
	} catch (error) {
		console.error('Error marking user offline:', error);
	}
}

/**
 * Sync collaboration data to localStorage for cross-window sharing
 */
function syncCollaborationData(modelId, data) {
	if (!browser) return;

	const collaborationKey = `${STORAGE_KEY}-${modelId}`;
	try {
		const currentData = JSON.parse(localStorage.getItem(collaborationKey) || '{}');
		const updatedData = { ...currentData, ...data, lastModified: Date.now() };
		localStorage.setItem(collaborationKey, JSON.stringify(updatedData));
		console.log('� Synced collaboration data to localStorage');
	} catch (error) {
		console.error('Error syncing collaboration data:', error);
	}
}

/**
 * Update user presence (cursor position, selection, etc.)
 * @param {Object} presenceUpdate - Partial presence update
 */
export function updatePresence(presenceUpdate) {
	if (!browser) return;

	const currentRoom = get(room);
	if (currentRoom && currentRoom.updatePresence) {
		currentRoom.updatePresence(presenceUpdate);
		console.log('👤 Updated presence:', presenceUpdate);
	}
}

/**
 * Add or update an element in live storage
 * @param {Object} element - The element to add/update
 */
export function updateLiveElement(element) {
	liveElements.update((elements) => {
		const existingIndex = elements.findIndex((el) => el.id === element.id);
		if (existingIndex >= 0) {
			elements[existingIndex] = element;
		} else {
			elements.push(element);
		}

		// Sync to localStorage for other windows
		if (currentModelId) {
			syncCollaborationData(currentModelId, { elements });
		}

		return elements;
	});
	console.log('📝 Updated live element:', element.id);
}

/**
 * Remove an element from live storage
 * @param {string} elementId - The element ID to remove
 */
export function removeLiveElement(elementId) {
	liveElements.update((elements) => {
		const filtered = elements.filter((el) => el.id !== elementId);

		// Sync to localStorage for other windows
		if (currentModelId) {
			syncCollaborationData(currentModelId, { elements: filtered });
		}

		return filtered;
	});
	console.log('🗑️ Removed live element:', elementId);
}

/**
 * Add or update a connection in live storage
 * @param {Object} connection - The connection to add/update
 */
export function updateLiveConnection(connection) {
	liveConnections.update((connections) => {
		const existingIndex = connections.findIndex((conn) => conn.id === connection.id);
		if (existingIndex >= 0) {
			connections[existingIndex] = connection;
		} else {
			connections.push(connection);
		}

		// Sync to localStorage for other windows
		if (currentModelId) {
			syncCollaborationData(currentModelId, { connections });
		}

		return connections;
	});
	console.log('🔗 Updated live connection:', connection.id);
}

/**
 * Add a comment to the threat model
 * @param {Object} comment - The comment to add
 */
export function addComment(comment) {
	const newComment = {
		...comment,
		id: `comment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
		timestamp: Date.now()
	};

	liveComments.update((comments) => {
		const updated = [...comments, newComment];

		// Sync to localStorage for other windows
		if (currentModelId) {
			syncCollaborationData(currentModelId, { comments: updated });
		}

		return updated;
	});
	console.log('💬 Added comment:', newComment);
}

/**
 * Update canvas metadata (zoom, pan, etc.)
 * @param {Object} metadataUpdate - Partial metadata update
 */
export function updateLiveMetadata(metadataUpdate) {
	liveMetadata.update((current) => {
		const updated = {
			...current,
			...metadataUpdate,
			lastModified: Date.now()
		};

		// Sync to localStorage for other windows
		if (currentModelId) {
			syncCollaborationData(currentModelId, { metadata: updated });
		}

		return updated;
	});
	console.log('📊 Updated metadata:', metadataUpdate);
}

/**
 * Disconnect from collaboration
 */
export function disconnectCollaboration() {
	if (!browser) return;

	const currentRoom = get(room);
	if (currentRoom && currentRoom.cleanup) {
		currentRoom.cleanup();
	}
	room.set(null);
	isConnected.set(false);
	others.set([]);
	console.log('👋 Disconnected from collaboration');
}

/**
 * Broadcast a custom event to all users
 * @param {Object} event - The event to broadcast
 */
export function broadcastEvent(event) {
	console.log('📡 Broadcasting event:', event);
	// For localStorage sync, this could trigger a custom storage event
	if (browser && currentModelId) {
		const eventKey = `${STORAGE_KEY}-events-${currentModelId}`;
		const eventData = {
			...event,
			timestamp: Date.now(),
			userId: currentUser?.id
		};
		localStorage.setItem(eventKey, JSON.stringify(eventData));
	}
}
