# syntax=docker/dockerfile:1
# ---------- Stage 1: Hugo build ----------
# Use the actively-maintained hugomods/hugo:exts image (klakegg/hugo is
# abandoned and stopped at 0.111.3, so its :0.148.1-onbuild tag does not
# exist on Docker Hub). hugomods ships the latest Hugo extended build and
# is updated within days of each Hugo release.
#
# The build context is expected to include a pre-built public/ directory
# (see README and docs/). The Hugo stage is a no-op when public/ already
# exists; it only rebuilds from source if public/ is absent, so CI can
# pass --build-arg REBUILD=1 to force a fresh build.
FROM hugomods/hugo:exts AS builder
ARG REBUILD=0
WORKDIR /src
COPY . .

# If public/ is missing OR REBUILD=1, rebuild the site from source.
# The public/ dir shipped in the build context takes precedence — this
# keeps the image small and lets us ship a pre-built site (built with
# the local /opt/data/bin/hugo on the migration host) without needing
# network access to module proxies at build time.
RUN if [ "$REBUILD" = "1" ] || [ ! -d public ] || [ -z "$(ls -A public 2>/dev/null)" ]; then \
      hugo --gc --minify --cleanDestinationDir ; \
    fi

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
