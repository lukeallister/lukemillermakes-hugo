# syntax=docker/dockerfile:1
# ---------- Stage 1: Hugo build ----------
# Uses the klakegg/hugo image (a popular, well-maintained Hugo image on Docker Hub)
# at the exact version that we know works with the xmin theme (>= 0.146).
FROM klakegg/hugo:0.148.1-onbuild AS builder
WORKDIR /src
COPY . .

# Build the static site. --gc garbage-collects unused cached resources;
# --minify produces compressed HTML/CSS/JS; --cleanDestinationDir ensures
# stale files from previous builds don't linger in /src/public/.
#
# The local /opt/data/bin/hugo path is also tried first so the build works
# on the migration host where a host-installed Hugo is available; on any
# machine pulling klakegg/hugo fresh, the plain `hugo` command resolves to
# the image's binary at /usr/local/bin/hugo.
RUN /opt/data/bin/hugo --gc --minify --cleanDestinationDir || hugo --gc --minify --cleanDestinationDir

# ---------- Stage 2: nginx static server ----------
# nginx:alpine is ~40 MB and has rock-solid static-file performance.
FROM nginx:1.27-alpine

# Copy the rendered site into nginx's default web root.
COPY --from=builder /src/public/ /usr/share/nginx/html/

# Drop our minimal nginx config into the conf.d directory that nginx:alpine
# already includes from its main /etc/nginx/nginx.conf.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# The nginx:alpine base image already defines CMD ["nginx", "-g", "daemon off;"]
# so we don't need to repeat it here.