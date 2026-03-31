## This is a PostgreSQL schema, marking my ideas down here 

### Users
``` 
id: uuid,
username: string,
email: string,
passwordHash: string,
createdAt: UTC timestamp
```

### Refresh Tokens

```
tokenId: uuid,
userId: uuid (user id),
expirationDate: UTC timestamp,
revokedDate: UTC timestamp,
createdAt: UTC timestamp,
```

This is the table which is going to be used for live matchmaking pairing 


### Matches
```
matchId: uuid,
white: uuid (userid),
black: uuid (userid),
timeControl: string,
increment: int (seconds added per move),
createdAt: UTC timestamp,
status: string, (to keep track of whether the game is still ongoing or not)
```

This is the table which is going to be used to store games after they are done
### Games
```
gameId: uuid,
matchId: uuid (match id),
white: uuid (user id),
black: uuid (user id),
startedAt: UTC timestamp,
endedAt: UTC timestamp (when game finished),
result: string (white_win, black_win, draw, abandoned),
moves: int,
timeControl: string,
pgn: text (the full game notation)
```

###  game_logs 

```
gamelogId: uuid,
gameId: uuid (gameid),
userId: uuid (userid),
eventType: string (resign, draw, white move, black move),
data: JSONB,
metadata: JSONB,
createdAt: UTC timestamp
```

i lowkey don't know if I'm gonna do this, but I figured I should have an idea
just in case
### Audit Logs

```
auditLogId: uuid,
createdAt: UTC timestamp,
user_id: uuid,
game_id: uuid,
match_id: uuid,
category: string (cheating, connection, account_security, platform_abuse, system)
event_type: string (engine_suspected, failed_login_attempts, etc.)
severity: string (info, warning, critical)
details: JSONB (move_sequence, ip_address, accuracy_score, etc.)
flags: JSONB,
source: (cpp server or fastapi?),
```


