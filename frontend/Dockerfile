FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /srv/app
RUN npm install -g serve
COPY --from=build /app/dist ./
ENV FRONTEND_PORT=4173
EXPOSE 4173
CMD ["sh", "-c", "serve -s /srv/app -l tcp://0.0.0.0:${FRONTEND_PORT:-4173}"]
