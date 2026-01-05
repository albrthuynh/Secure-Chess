FROM node:25.2.1

WORKDIR /client

# install application dependencies
COPY package.json ./
RUN npm install

# copy everything in this directory
COPY . .
EXPOSE 3000

# creates a new user named client in the container
RUN useradd client

RUN chown -R client:client /client

USER client

CMD ["npm", "run", "dev"]