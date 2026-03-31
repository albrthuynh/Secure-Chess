-- Migration: Add matches and game_logs tables, update games table
BEGIN;

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

-- indexes for matches 
CREATE INDEX IF NOT EXISTS idx_matches_white_user_id ON matches(white_user_id);
CREATE INDEX IF NOT EXISTS idx_matches_black_user_id ON matches(black_user_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at);

CREATE TABLE IF NOT EXISTS game_logs (
  game_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id),
  event_type TEXT NOT NULL,
  data JSONB,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- indexes for game_logs
CREATE INDEX IF NOT EXISTS idx_game_logs_game_id ON game_logs(game_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_user_id ON game_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_event_type ON game_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_game_logs_created_at ON game_logs(created_at);

-- Alter games table to add missing columns
ALTER TABLE games
  ADD COLUMN IF NOT EXISTS match_id UUID REFERENCES matches(match_id),
  ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS result TEXT,
  ADD COLUMN IF NOT EXISTS pgn TEXT;

-- Add index for games match_id
CREATE INDEX IF NOT EXISTS idx_games_match_id ON games(match_id);

COMMIT;
