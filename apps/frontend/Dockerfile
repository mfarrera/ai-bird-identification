FROM node:22-alpine

WORKDIR /app

# Habilitem pnpm (el gestor de paquets que ja fa servir el projecte)
RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json ./
RUN pnpm install

COPY . .

EXPOSE 5173

# Cridem vite directament (no via l'script "dev" de pnpm) perquè el flag
# --host arribi net i el servidor escolti fora del contenidor.
CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]
