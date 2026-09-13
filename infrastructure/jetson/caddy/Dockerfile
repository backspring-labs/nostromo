# Caddy with the Cloudflare DNS module, for the buzz.backspring.xyz certificate.
#
# Built here rather than pulled from a third-party image so the TLS terminator in front of the
# relay is reconstructable from pinned sources, like everything else in docs/source-baseline.md.
# Prebuilt caddy+cloudflare images exist and are maintained; they are also a supply-chain
# dependency for the component that holds the private key, which is the wrong place to save ten
# minutes.
#
# Tailscale Serve cannot issue for a name outside the tailnet, and HTTP-01 would require the
# Jetson to be reachable from the internet. DNS-01 needs neither: the challenge is answered in
# Cloudflare's zone and nothing inbound is ever opened.

FROM caddy:2.11.4-builder-alpine@sha256:1a1689db91cfb390b2d856a1b3774e796852822cd723fa54c475b272f82bb4b7 AS builder
RUN xcaddy build \
      --with github.com/caddy-dns/cloudflare@v0.2.4

FROM caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
