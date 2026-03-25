-- future migrations should be done with ALTER
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expiration_date TIMESTAMPTZ NOT NULL,
  revoked_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS games (
  game_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  white_user_id UUID NOT NULL REFERENCES users(user_id),
  black_user_id UUID NOT NULL REFERENCES users(user_id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  moves INT NOT NULL DEFAULT 0,
  time_control TEXT NOT NULL,
  CONSTRAINT games_distinct_players CHECK (white_user_id <> black_user_id),
  CONSTRAINT games_non_negative_moves CHECK (moves >= 0)
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expiration_date ON refresh_tokens(expiration_date);
CREATE INDEX IF NOT EXISTS idx_games_white_user_id ON games(white_user_id);
CREATE INDEX IF NOT EXISTS idx_games_black_user_id ON games(black_user_id);
CREATE INDEX IF NOT EXISTS idx_games_started_at ON games(started_at);
