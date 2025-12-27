-- Migration: Add chat conversations and messages tables
-- Description: Support conversation management for AI chat with analysis context

-- Chat conversations table
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    organization_name TEXT NOT NULL,
    analysis_id UUID NOT NULL,
    analysis_scope TEXT NOT NULL CHECK (analysis_scope IN ('unified', 'folder')),
    project_name TEXT, -- NULL for unified, folder name for folder analysis
    folder_path TEXT, -- Folder path for folder analysis
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    message_count INTEGER DEFAULT 0
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB, -- Store RAG sources for assistant messages
    metadata JSONB, -- Additional metadata (confidence, filters, etc.)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_org ON chat_conversations(user_id, organization_name);
CREATE INDEX IF NOT EXISTS idx_conversations_analysis ON chat_conversations(analysis_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_analysis ON chat_conversations(user_id, analysis_id);
CREATE INDEX IF NOT EXISTS idx_conversations_active ON chat_conversations(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON chat_messages(conversation_id, created_at);

-- Comments
COMMENT ON TABLE chat_conversations IS 'Store chat conversations linked to workspace analysis';
COMMENT ON TABLE chat_messages IS 'Store individual messages within conversations';
COMMENT ON COLUMN chat_conversations.analysis_scope IS 'Type of analysis: unified (all repos) or folder (specific folder)';
COMMENT ON COLUMN chat_messages.sources IS 'RAG sources used to generate assistant responses';
