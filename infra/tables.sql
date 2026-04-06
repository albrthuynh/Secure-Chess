-- Initial schema for secure-chess database (I appended this up to adding_tables.sql)
-- Future changes should be done with migrations in migrations/ folder
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Refresh tokens for authentication
CREATE TABLE IF NOT EXISTS refresh_tokens (
  token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expiration_date TIMESTAMPTZ NOT NULL,
  revoked_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Matches table for matchmaking pairing
CREATE TABLE IF NOT EXISTS matches (
  match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  white_user_id UUID NOT NULL REFERENCES users(user_id),
  black_user_id UUID NOT NULL REFERENCES users(user_id),
  time_control TEXT NOT NULL,
  increment INT NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT matches_distinct_players CHECK (white_user_id <> black_user_id),
  CONSTRAINT matches_valid_increment CHECK (increment >= 0)
);

-- Games table for completed games
CREATE TABLE IF NOT EXISTS games (
  game_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id UUID REFERENCES matches(match_id),
  white_user_id UUID NOT NULL REFERENCES users(user_id),
  black_user_id UUID NOT NULL REFERENCES users(user_id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  result TEXT,
  moves INT NOT NULL DEFAULT 0,
  time_control TEXT NOT NULL,
  pgn TEXT,
  CONSTRAINT games_distinct_players CHECK (white_user_id <> black_user_id),
  CONSTRAINT games_non_negative_moves CHECK (moves >= 0)
);

-- Game logs for event tracking (optional)
CREATE TABLE IF NOT EXISTS game_logs (
  game_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id),
  event_type TEXT NOT NULL,
  data JSONB,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for refresh_tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expiration_date ON refresh_tokens(expiration_date);

-- Indexes for matches
CREATE INDEX IF NOT EXISTS idx_matches_white_user_id ON matches(white_user_id);
CREATE INDEX IF NOT EXISTS idx_matches_black_user_id ON matches(black_user_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at);

-- Indexes for games
CREATE INDEX IF NOT EXISTS idx_games_match_id ON games(match_id);
CREATE INDEX IF NOT EXISTS idx_games_white_user_id ON games(white_user_id);
CREATE INDEX IF NOT EXISTS idx_games_black_user_id ON games(black_user_id);
CREATE INDEX IF NOT EXISTS idx_games_started_at ON games(started_at);

-- Indexes for game_logs
CREATE INDEX IF NOT EXISTS idx_game_logs_game_id ON game_logs(game_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_user_id ON game_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_event_type ON game_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_game_logs_created_at ON game_logs(created_at);
