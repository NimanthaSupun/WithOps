import { writable, derived, get } from 'svelte/store';
import { createCollaborationRoom, storageConfig } from './liveblocks.js';

/**
 * Collaboration Store - Manages real-time collaboration state
 */

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
		if (user.presence?.userInfo?.name && user.presence?.userInfo?.color) {
			colors[user.presence.userInfo.name] = user.presence.userInfo.color;
		}
	});
	return colors;
});

/**
 * Initialize collaboration for a threat model
 * @param {string} modelId - The threat model ID
 * @param {Object} userInfo - Current user information
 */
export async function initializeCollaboration(modelId, userInfo = {}) {
	try {
		console.log('🤝 Initializing collaboration for model:', modelId);

		// Create or join the collaboration room
		const roomInstance = createCollaborationRoom(modelId, userInfo);

		// Set up room event listeners
		roomInstance.subscribe('my-presence', (presence) => {
			myPresence.set(presence);
		});

		roomInstance.subscribe('others', (othersArray) => {
			others.set(othersArray);
			console.log('👥 Other users in room:', othersArray.length);
		});

		roomInstance.subscribe('error', (error) => {
			console.error('❌ Room error:', error);
			connectionError.set(error.message);
			isConnected.set(false);
		});

		// Wait for room to be ready
		await roomInstance.waitForReady();

		// Set up live storage
		const { root } = roomInstance.getStorageSnapshot();

		// Initialize live data stores
		if (root) {
			// Elements
			const elements = root.get('elements');
			if (elements) {
				liveElements.set(elements.toArray());
				elements.subscribe(() => {
					liveElements.set(elements.toArray());
				});
			}

			// Connections
			const connections = root.get('connections');
			if (connections) {
				liveConnections.set(connections.toArray());
				connections.subscribe(() => {
					liveConnections.set(connections.toArray());
				});
			}

			// Threats
			const threats = root.get('threats');
			if (threats) {
				liveThreats.set(threats.toArray());
				threats.subscribe(() => {
					liveThreats.set(threats.toArray());
				});
			}

			// Metadata
			const metadata = root.get('metadata');
			if (metadata) {
				liveMetadata.set(metadata.toObject());
				metadata.subscribe(() => {
					liveMetadata.set(metadata.toObject());
				});
			}

			// Comments
			const comments = root.get('comments');
			if (comments) {
				liveComments.set(comments.toArray());
				comments.subscribe(() => {
					liveComments.set(comments.toArray());
				});
			}
		}

		// Update connection state
		room.set(roomInstance);
		isConnected.set(true);
		connectionError.set(null);

		console.log('✅ Collaboration initialized successfully');
		return roomInstance;
	} catch (error) {
		console.error('❌ Failed to initialize collaboration:', error);
		connectionError.set(error.message);
		isConnected.set(false);
		throw error;
	}
}

/**
 * Update user presence (cursor position, selection, etc.)
 * @param {Object} presenceUpdate - Partial presence update
 */
export function updatePresence(presenceUpdate) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.updatePresence(presenceUpdate);
	}
}

/**
 * Add or update an element in live storage
 * @param {Object} element - The element to add/update
 */
export function updateLiveElement(element) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.updateStorage((root) => {
			const elements = root.get('elements');
			const existingIndex = elements.findIndex((el) => el.id === element.id);

			if (existingIndex >= 0) {
				elements.set(existingIndex, element);
			} else {
				elements.push(element);
			}
		});
	}
}

/**
 * Remove an element from live storage
 * @param {string} elementId - The element ID to remove
 */
export function removeLiveElement(elementId) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.updateStorage((root) => {
			const elements = root.get('elements');
			const index = elements.findIndex((el) => el.id === elementId);
			if (index >= 0) {
				elements.delete(index);
			}
		});
	}
}

/**
 * Add or update a connection in live storage
 * @param {Object} connection - The connection to add/update
 */
export function updateLiveConnection(connection) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.updateStorage((root) => {
			const connections = root.get('connections');
			const existingIndex = connections.findIndex((conn) => conn.id === connection.id);

			if (existingIndex >= 0) {
				connections.set(existingIndex, connection);
			} else {
				connections.push(connection);
			}
		});
	}
}

/**
 * Add a comment to the threat model
 * @param {Object} comment - The comment to add
 */
export function addComment(comment) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.updateStorage((root) => {
			const comments = root.get('comments');
			comments.push({
				...comment,
				id: `comment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
				timestamp: Date.now()
			});
		});
	}
}

/**
 * Update canvas metadata (zoom, pan, etc.)
 * @param {Object} metadataUpdate - Partial metadata update
 */
export function updateLiveMetadata(metadataUpdate) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.updateStorage((root) => {
			const metadata = root.get('metadata');
			Object.keys(metadataUpdate).forEach((key) => {
				metadata.set(key, metadataUpdate[key]);
			});
			metadata.set('lastModified', Date.now());
		});
	}
}

/**
 * Disconnect from collaboration
 */
export function disconnectCollaboration() {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.leave();
		room.set(null);
		isConnected.set(false);
		others.set([]);
		console.log('👋 Disconnected from collaboration');
	}
}

/**
 * Broadcast a custom event to all users
 * @param {Object} event - The event to broadcast
 */
export function broadcastEvent(event) {
	const currentRoom = get(room);
	if (currentRoom) {
		currentRoom.broadcastEvent(event);
	}
}
