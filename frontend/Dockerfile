FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
FROM dependencies AS builder
COPY . .
ARG NEXT_PUBLIC_CTEC_API_ORIGIN=http://localhost:8000
ARG NEXT_PUBLIC_OIDC_AUTHORITY=""
ARG NEXT_PUBLIC_OIDC_CLIENT_ID=""
ARG NEXT_PUBLIC_OIDC_REDIRECT_URI=""
ARG NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI=""
ARG NEXT_PUBLIC_OIDC_SCOPE="openid profile supplier-risk:read"
ENV NEXT_PUBLIC_CTEC_API_ORIGIN=$NEXT_PUBLIC_CTEC_API_ORIGIN
ENV NEXT_PUBLIC_OIDC_AUTHORITY=$NEXT_PUBLIC_OIDC_AUTHORITY
ENV NEXT_PUBLIC_OIDC_CLIENT_ID=$NEXT_PUBLIC_OIDC_CLIENT_ID
ENV NEXT_PUBLIC_OIDC_REDIRECT_URI=$NEXT_PUBLIC_OIDC_REDIRECT_URI
ENV NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI=$NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI
ENV NEXT_PUBLIC_OIDC_SCOPE=$NEXT_PUBLIC_OIDC_SCOPE
RUN npm run build
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]

