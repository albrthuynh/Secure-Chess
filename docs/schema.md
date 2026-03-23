## This is a PostgreSQL schema, marking my ideas down here 

### Users
``` 
id: uuid,
username: string,
email: string,
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




