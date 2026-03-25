-- The command to run the migration with docker db
-- docker compose --env-file infra/.env -f infra/docker-compose.yml exec -T postgres sh -lc \ 
-- psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < infra/migrations/adding_hash_token.sql
BEGIN;
ALTER TABLE refresh_tokens
ADD COLUMN IF NOT EXISTS token_hash TEXT NOT NULL UNIQUE;
COMMIT;
