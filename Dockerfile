# syntax=docker/dockerfile:1
# ---------- Stage 1: Hugo build ----------
FROM hugomods/hugo:exts AS builder
ARG REBUILD=0
WORKDIR /src
COPY . .

RUN if [ "$REBUILD" = "1" ] || [ ! -d public ] || [ -z "$(ls -A public 2>/dev/null)" ]; then \
      hugo --gc --minify --cleanDestinationDir ; \
    fi

# ---------- Stage 2: nginx static server ----------
FROM nginx:1.27-alpine

# Copy the rendered site into nginx's default web root.
COPY --from=builder /src/public/ /usr/share/nginx/html/

# Drop our minimal nginx config into the conf.d directory.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Generate a self-signed TLS certificate at build time.
# This avoids needing to mount secrets or manage cert files externally.
RUN mkdir -p /etc/nginx/ssl && \
    apk add --no-cache openssl && \
    openssl req -x509 -nodes -days 3650 \
      -newkey rsa:2048 \
      -keyout /etc/nginx/ssl/selfsigned.key \
      -out /etc/nginx/ssl/selfsigned.crt \
      -subj "/C=US/ST=OR/L=Portland/O=LukeMillerMakes/CN=lukemillermakes.com" && \
    chmod 600 /etc/nginx/ssl/selfsigned.key && \
    apk del openssl

EXPOSE 80 443
