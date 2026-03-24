## This is a PostgreSQL schema, marking my ideas down here 

### Users
``` 
id: uuid,
username: string,
email: string,
passwordHash: string,
createdAt: UTC timestamp,
refreshToken: (refresh token id)
```

### Refresh Tokens

```
tokenId: uuid,
userId: uuid (user id),
expirationDate: UTC timestamp,
revokedDate: UTC timestamp,
createdAt: UTC timestamp,

```


### Games

```
gameid: uuid,
white: uuid (user id),
black: uuid (user id),
startedAt: UTC timestamp,
moves: int,
timeControl: string,
```




