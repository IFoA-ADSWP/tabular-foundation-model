# Resolving a Docker Hub manifest digest for the image pin

> **Status:** current as of 2026-11-10. A measurement of an external service, not a result. It is the
> evidence behind the digest check that the paid-run supply policy (#253) relies on, and it will be
> cited by the spec that implements it.

**Ticket:** [#366](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/366) — *Confirm the
digest call the image pin depends on*. Branch `research/vast-image-digests`, never merged.

**Question.** The supply policy decided on #253 pins every image tier with a declared digest. Does the
call that resolves a digest exist, can it be made without a stored credential, what does it cost, what
are the four values, and what do the failure modes look like — so the adapter can tell `refused` from
`indeterminate` rather than collapsing both into a timeout?

**Answer in five lines.**

1. **Yes, anonymously, in two HTTP calls.** An anonymous pull token from `auth.docker.io`, then a
   `HEAD`/`GET` of the manifest from `registry-1.docker.io`. No stored credential, no Docker Hub account.
2. **All four tier tags exist** and are **single-platform `linux/amd64` image manifests**, so for these
   four tags the tag digest *is* the platform image digest. The digests are in §3.
3. **`pytorch/pytorch` is not pull-rate limited.** It returns no `ratelimit-*` headers at all, and kept
   answering `200` while the same IP's anonymous quota for `library/ubuntu` was at `0/100`. The general
   anonymous limit, measured on a repo that is limited, is **100 per 3600 s** (§2).
4. **Declare the top-level `Docker-Content-Digest` of the tag** (§4) — it is what the tag resolves to and
   what a by-tag pull verifies. On a multi-arch tag that is the *index* digest, and it embeds every
   platform child digest, so it is a strictly stronger pin than a platform digest, not a weaker one.
5. **The check proves what the tag pointed at, not what the host pulled.** `vast_run.sh` passes a tag to
   Vast (`--image "$IMAGE"`), so the pin is only closed if the pull is by digest or the host verifies
   the image it got. This is the one place where the mechanism can be made meaningless (§4.4).

All measurements below were taken **2026-11-10, 12:20–12:26 UTC**, from one IPv4 address
(`docker-ratelimit-source: 86.25.221.152`), with `curl` 8.x on macOS.

---

## 1. The endpoint — two calls, anonymously

The chain is the standard Docker Registry v2 bearer flow. **Two calls, not one.** The registry answers
`401` and names its own token service, so the realm is discoverable rather than hardcoded.

### 1.1 Bootstrap: what the registry says when you arrive with no credential

```console
$ curl -sS -D - -o body.json \
    "https://registry-1.docker.io/v2/pytorch/pytorch/manifests/2.7.0-cuda12.8-cudnn9-runtime"
```

```
HTTP/2 401
content-type: application/json
www-authenticate: Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:pytorch/pytorch:pull"
```

```json
{"errors":[{"code":"UNAUTHORIZED","message":"authentication required","detail":[{"Type":"repository","Class":"","Name":"pytorch/pytorch","Action":"pull"}]}]}
```

`GET https://registry-1.docker.io/v2/` alone returns the same `401` with
`www-authenticate: Bearer realm="https://auth.docker.io/token",service="registry.docker.io"` (no scope),
body `{"errors":[{"code":"UNAUTHORIZED","message":"authentication required","detail":null}]}`. So the
adapter can discover the realm and service, but it still has to build the `scope=` string itself from
the repository it is about to ask about.

### 1.2 Call 1 — the anonymous pull token

```console
$ curl -sS -D - -o token.json \
    "https://auth.docker.io/token?service=registry.docker.io&scope=repository:pytorch/pytorch:pull"
```

```
HTTP/2 200
content-type: application/json
x-ratelimit-limit: 3000, 3000;w=60
x-ratelimit-remaining: 2999
x-ratelimit-reset: 52
```

Body keys: `access_token`, `expires_in`, `issued_at`, `token` (JWT elided below — the token is a
2,700-character RS256 JWT, not a short opaque string).

```json
{"token":"<JWT, 2700 chars, elided>",
 "access_token":"<the same JWT>",
 "expires_in":300,
 "issued_at":"2026-11-10T12:20:08.725764231Z"}
```

Three facts the adapter can rely on:

- **No credential is required.** The token is anonymous; nothing about it identifies an account.
- **It lives 300 seconds.** `expires_in: 300`. One token per run is enough; no refresh loop is needed.
- **One token covers all four tier tags** — they are the same repository, so the same `scope=` string.
  Four digests therefore cost **five HTTP calls** (1 token + 4 manifests), not eight.
- The `3000, 3000;w=60` headers belong to the **auth service**, not the registry pull limit. Do not read
  them as the pull budget.

### 1.3 Call 2 — the manifest, and the headers that matter

```console
$ TOKEN=$(jq -r .token token.json)
$ curl -sS -I -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
    -H "Accept: application/vnd.oci.image.index.v1+json" \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    -H "Accept: application/vnd.oci.image.manifest.v1+json" \
    "https://registry-1.docker.io/v2/pytorch/pytorch/manifests/2.7.0-cuda12.8-cudnn9-runtime"
```

```
HTTP/2 200
content-type: application/vnd.docker.distribution.manifest.v2+json
content-length: 1366
docker-content-digest: sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80
docker-distribution-api-version: registry/2.0
etag: "sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80"
docker-ratelimit-source: 86.25.221.152
strict-transport-security: max-age=31536000
```

**`docker-content-digest` is the answer.** It is the sha256 of the manifest bytes, it is present on both
`HEAD` and `GET`, and it equals the `etag` (unquoted). The `content-type` tells you which *kind* of
manifest it is — `…manifest.v2+json` here means a single-platform image, not a list.

The four `Accept` headers are still worth sending: they make the adapter correct if a tag ever becomes
multi-arch. On Docker Hub they do **not** change the answer — see §4.3.

**Use `HEAD`, not `GET`.** Docker documents that a `GET` emulates a real pull and counts toward the
limit while a `HEAD` does not. `HEAD` returns `docker-content-digest` and the `ratelimit-*` headers
identically (verified on `library/ubuntu` and `ratelimitpreview/test`).

### 1.4 A one-call alternative that also works

The Docker Hub web API answers the same question with no token and no `Accept` negotiation:

```console
$ curl -sS https://hub.docker.com/v2/repositories/pytorch/pytorch/tags/2.7.0-cuda12.8-cudnn9-runtime
```

```json
{"name":"2.7.0-cuda12.8-cudnn9-runtime",
 "digest":"sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80",
 "media_type":"application/vnd.docker.container.image.v1+json",
 "images":[{"architecture":"amd64","os":"linux",
            "digest":"sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80"}],
 "tag_last_pushed":"2025-04-23T19:56:45.06117Z"}
```

It agreed with the registry on **all four** tags (§3). It is a different service with a different
availability story and no documented contract for this use, so it is a fallback, not the primary path.
The registry is authoritative because it is the thing the pull talks to.

---

## 2. The rate limit

### 2.1 What limit applies

Docker's published table ([docs.docker.com/docker-hub/usage/pulls](https://docs.docker.com/docker-hub/usage/pulls/)):

| User type | Pull rate limit |
| --- | --- |
| Unauthenticated | **100 per IPv4 address, or IPv6 /64 subnet, per 6 hours** |
| Personal (authenticated) | 200 per 6 hours |
| Pro / Team / Business (authenticated) | unlimited |

**Measured, and it differs from the documentation in two ways.**

First, the **window is 3600 s, not 21600 s**. Every limited repo returned `w=3600`:

```console
$ curl -sS -I -H "Authorization: Bearer $TOKEN" \
    "https://registry-1.docker.io/v2/library/ubuntu/manifests/24.04"
```
```
HTTP/2 200
docker-content-digest: sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
docker-ratelimit-source: 86.25.221.152
ratelimit-limit: 100;w=3600
ratelimit-remaining: 99;w=3600
```

The same `100;w=3600` came back from Docker's own probe repo
`ratelimitpreview/test` — the repo the docs tell you to use for exactly this check. **Do not hardcode
21600.** Read the window out of the header.

Second, and the fact that actually matters here: **`pytorch/pytorch` is not rate limited at all.**

```console
$ curl -sS -I -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    "https://registry-1.docker.io/v2/pytorch/pytorch/manifests/2.7.0-cuda12.8-cudnn9-runtime"
```
```
HTTP/2 200
docker-content-digest: sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80
docker-ratelimit-source: 86.25.221.152
```

There is **no `ratelimit-limit` and no `ratelimit-remaining`** — only the source address. Docker's docs
cover this case: *"If you don't see any `ratelimit` header, it could be because the image or your IP is
unlimited in partnership with a publisher, provider, or an open source organization."* The repo is a
verified publisher, so the anonymous pull limit does not apply to it.

This was confirmed the hard way. After exhausting the IP's anonymous quota on `library/ubuntu` (§2.2),
with `ratelimit-remaining: 0;w=3600` in hand:

| Request | Result |
| --- | --- |
| `library/ubuntu:24.04` | `429` `TOOMANYREQUESTS` |
| `pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime` | **`200`**, digest unchanged |

So the four digest resolutions are, today, free of pull-rate cost. The adapter must still handle `429`:
the exemption is a property of the repository and the caller's identity, not of the protocol, and a
future tier image from a non-exempt publisher would hit the limit immediately.

### 2.2 What a limited response looks like — captured, not inferred

Captured by driving `ratelimitpreview/test` to exhaustion with `GET` (the repo exists for this):

```
HTTP/2 429
date: Tue, 10 Nov 2026 12:25:38 GMT
content-type: application/json
content-length: 149
docker-ratelimit-source: 86.25.221.152
x-ratelimit-limit: 100;w=3600
ratelimit-limit: 100;w=3600
x-ratelimit-remaining: 0;w=3600
ratelimit-remaining: 0;w=3600
strict-transport-security: max-age=31536000
```

```json
{"errors":[{"code":"TOOMANYREQUESTS","message":"You have reached your unauthenticated pull rate limit. https://www.docker.com/increase-rate-limit"}]}
```

Four things to build against:

- **Status `429`, error code `TOOMANYREQUESTS`.** Not `403`, not `503`.
- **`ratelimit-remaining: 0;w=3600`** is the positive statement that this is quota and not a change. The
  `w=` value is the window; the remaining time is *not* in the header, so the reset moment is not
  directly observable.
- **There is no `Retry-After` header.** Backoff cannot be read off the response; use a fixed wait or
  re-probe after the `w=` interval.
- **There is no `docker-content-digest` on a `429`.** An adapter that treats "no digest header" as
  "digest changed" would report a throttle as a supply change. That is the specific bug this section
  exists to prevent.

Note the docs show the `429` body as plain text. That is the Docker CLI's rendering; the wire body is
the JSON above.

---

## 3. The four digests

Resolved with the §1.3 command, `HEAD`, all four `Accept` headers, one token. All four tags exist. Each
was re-resolved by `GET` and by the Hub API (§1.4) and all three paths agreed, so these are not a
transcription of a single call.

| Tier (host `cuda_max_good`) | Tag | `Docker-Content-Digest` |
| --- | --- | --- |
| 12.8 | `pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime` | `sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80` |
| 12.6 | `pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime` | `sha256:f894dae26e1ee8557c544f9cfdb9dc011b1552bf3c1e656b422f2e221d380e40` |
| 12.4 | `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` | `sha256:c8268a92a69bd500f8be0e665b2630ee006dadaf7bfbc24249141b15ff622755` |
| 12.1 | `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime` | `sha256:831247999fbf7e08f61b3e39f6d77ee434f38f6f07f769d00db451e853878067` |

Verbatim from the wire, one `docker-content-digest` line each:

```
2.7.0-cuda12.8-cudnn9-runtime   docker-content-digest: sha256:7db0e1bf4b1ac274ea09cf6358ab516f8a5c7d3d0e02311bed445f7e236a5d80
2.6.0-cuda12.6-cudnn9-runtime   docker-content-digest: sha256:f894dae26e1ee8557c544f9cfdb9dc011b1552bf3c1e656b422f2e221d380e40
2.5.1-cuda12.4-cudnn9-runtime   docker-content-digest: sha256:c8268a92a69bd500f8be0e665b2630ee006dadaf7bfbc24249141b15ff622755
2.5.1-cuda12.1-cudnn9-runtime   docker-content-digest: sha256:831247999fbf7e08f61b3e39f6d77ee434f38f6f07f769d00db451e853878067
```

Each is `content-type: application/vnd.docker.distribution.manifest.v2+json` — a **single-platform
image manifest**, not a manifest list. Each config blob reports `architecture: amd64, os: linux`. The
Hub API's `images` array has exactly one entry per tag, and its digest equals the tag digest.

Push dates (Hub API), for the record — none of these tags has moved since it was published:

| Tag | `tag_last_pushed` |
| --- | --- |
| `2.7.0-cuda12.8-cudnn9-runtime` | 2025-04-23T19:56:45Z |
| `2.6.0-cuda12.6-cudnn9-runtime` | 2025-01-29T22:06:05Z |
| `2.5.1-cuda12.4-cudnn9-runtime` | 2024-10-29T22:42:38Z |
| `2.5.1-cuda12.1-cudnn9-runtime` | 2024-10-29T21:46:54Z |

**The tags are mutable.** `GET https://hub.docker.com/v2/namespaces/pytorch/repositories/pytorch/`
returns `"immutable_tags_settings": {"enabled": false, "rules": [".*"]}`. Nothing at Docker Hub stops
`pytorch` from re-pushing any of these four tags to different bytes. The digest is therefore the only
thing that can detect it, which is why the check is not ceremony.

**Any future tier must be resolved, never guessed.** A tag that does not exist answers `404`
`MANIFEST_UNKNOWN` (§5), so a tier table extended with an unpublished tag fails loudly at the first
resolution rather than at pull time on a paid host.

---

## 4. Manifest list vs platform manifest

### 4.1 For these four tags there is no split

All four are single-platform `linux/amd64` image manifests, so `Docker-Content-Digest` **is** the
platform image digest. The question in the ticket does not bite for the tiers as they stand. It bites
the moment a tag is republished as multi-arch, or a tier is added from a publisher who does that.

### 4.2 The split, measured on tags that have it

Two controls, both multi-arch, both resolved with the §1.3 Accept set:

```console
$ curl -sS -D - -o idx.json -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.oci.image.index.v1+json" \
    -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
    "https://registry-1.docker.io/v2/library/ubuntu/manifests/24.04"
```
```
HTTP/2 200
content-type: application/vnd.oci.image.index.v1+json
docker-content-digest: sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
```

`index.json` lists `linux/amd64` at `sha256:78d4744ead1f5b19b04d0df558ab182a5300903900755e515b2ca4d10eb2044d`
— a **different digest** from the tag's. Same shape on a Docker-format list:

| Reference | Tag digest | `linux/amd64` child digest |
| --- | --- | --- |
| `library/ubuntu:24.04` (OCI index) | `sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852` | `sha256:78d4744ead1f5b19b04d0df558ab182a5300903900755e515b2ca4d10eb2044d` |
| `grafana/grafana:latest` (docker manifest list) | `sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205` | `sha256:6e5d306338670f381a942f1c50d3c266bf71531e5ddd9ee4fc1a133dac5ce63d` |

The other `grafana` children, for completeness — `linux/arm64` at
`sha256:868b6ae6642ec09a71a1273d4c0eb952856c1f421137b33e26038e629ee3c208` and `linux/arm` at
`sha256:0ee356465692489b83e4b7f7fec3f5e2b8a0ccae8f8e202dbada42240e08a66d`.

Both `mediaType`s appear in the wild (`application/vnd.oci.image.index.v1+json` and
`application/vnd.docker.distribution.manifest.list.v2+json`), which is why the adapter sends both
`Accept` values and branches on `content-type` rather than assuming one.

### 4.3 Which digest the policy should declare

**Declare the top-level `Docker-Content-Digest` of the tag** — the value the registry returns for the
tag under the full `Accept` set. Reasons, in order of weight:

1. **It is the only value the tag itself resolves to.** A platform digest is not reachable from the tag
   without parsing a list, which means the adapter has to know the architecture in advance and fails
   opaquely when it guesses wrong.
2. **It is what a by-tag pull verifies.** Docker verifies the manifest bytes it fetched against the
   digest the registry advertised in `Docker-Content-Digest`. A pin that is not that value is checking
   something the pull never checked.
3. **It is a strictly stronger pin than a platform digest.** An index *embeds* its children's digests
   as fields in its own JSON, so any change to any platform child changes the index bytes and therefore
   the index digest. The index digest can change while our `amd64` image is unchanged (a false positive,
   which refuses spend — safe); it cannot stay the same while our `amd64` image changed. A platform
   digest has the opposite, unsafe, failure mode.

**Correction to the ticket's premise.** The ticket asks whether "the list digest is stable while
platform digests change". It is not, and cannot be: the list digest is a hash *of* the list, and the
list contains the platform digests. Change a child, the parent changes. That is what makes the list
digest the better declaration rather than a lossy one.

**Content negotiation does not change the answer on Docker Hub.** Requesting a multi-arch tag with only
the single-manifest `Accept` still returns the list, with the same digest:

```console
$ curl -sS -D - -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    "https://registry-1.docker.io/v2/grafana/grafana/manifests/latest"
```
```
HTTP/2 200
content-type: application/vnd.docker.distribution.manifest.list.v2+json
docker-content-digest: sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205
```

So an adapter that forgets the index `Accept` cannot silently record a platform digest instead. That is
a relief, not a licence to omit the headers: it is a behaviour of this registry, not of the spec.

### 4.4 Where the check can be made meaningless — the pull, not the resolution

The digest check runs where the launcher runs. The pull runs on the Vast host. `vast_run.sh` passes a
**tag**, not a digest:

```
scripts/gpu_helpers/vast_run.sh:595:  IMAGE="$(python3 "$REPO_DIR/scripts/gpu_helpers/pick_image.py" "${CUDA:-12.4}")"
scripts/gpu_helpers/vast_run.sh:747:    --image "$IMAGE" --disk "$DISK" \
```

So the check proves *"the tag pointed at digest X when the launcher looked"*. It does not prove the host
pulled X. A tag re-pushed between the check and the pull — or a host pulling from a cached, older tag —
satisfies the check and runs different bytes. Two ways to close it, both for the spec to choose between:

- **Pull by digest:** pass `pytorch/pytorch@sha256:…` to Vast instead of `:tag`. This is the only form
  that makes the pin load-bearing. **Unconfirmed** — whether Vast's `image` field accepts a
  `repo@sha256:…` reference was not tested here and needs a live instance to establish.
- **Verify on the host:** after the pull, assert the running image's `RepoDigests` matches the declared
  digest before any work starts, and fail the run if not. This costs nothing and closes the window
  without depending on Vast's parsing.

Until one of those exists, the check is a *supply drift alarm*, not an *image guarantee*, and the spec
should say so rather than implying more.

---

## 5. Failure shapes

The distinction the adapter needs is **`refused`** (the registry made a positive statement about this
name, and the name is not what we pinned) versus **`indeterminate`** (no statement was obtained — retry,
never spend). Every shape below was produced, not imagined, except where marked.

| Situation | Wire response | Positive statement? | Verdict |
| --- | --- | --- | --- |
| **Match** | `200`, `docker-content-digest: sha256:<declared>` | yes — tag resolves to the pinned bytes | `pass` |
| **Mismatch** | `200`, `docker-content-digest: sha256:<other>` | yes — tag resolves, to different bytes | `refused` (drift) |
| **Tag withdrawn** | `404`, `{"errors":[{"code":"MANIFEST_UNKNOWN","message":"manifest unknown","detail":"unknown tag=<tag>"}]}`, no digest header | yes — the tag is not there | `refused` (tag gone) |
| **Tag typo** | byte-identical to the above, `detail` naming the typo | yes — the tag is not there | `refused` — **indistinguishable from withdrawn** |
| **Repo name typo** | token mint still `200`; manifest `401` `UNAUTHORIZED`, `detail[0].Name` = the wrong repo, `www-authenticate` **without** `error="invalid_token"` | yes — that name is not anonymously pullable | `refused` (name wrong, or went private) |
| **Token expired / invalid** | `401` `UNAUTHORIZED` **with** `www-authenticate: … error="invalid_token"` | no — the credential failed, not the name | `indeterminate` → re-mint once, then retry |
| **Throttled** | `429` `TOOMANYREQUESTS`, `ratelimit-remaining: 0;w=3600`, no `Retry-After`, no digest header | no — quota, nothing about the tag | `indeterminate` |
| **Registry unreachable (DNS)** | curl exit `6`, `http=000`, `Could not resolve host` | no | `indeterminate` |
| **Registry unreachable (timeout/refused)** | curl exit `28`, `http=000`, `Connection timeout` | no | `indeterminate` |
| **Registry 5xx** | not observed today | no | `indeterminate` |

Raw bodies for the three that carry a decision:

```json
// tag withdrawn / tag typo — 404, identical shape
{"errors":[{"code":"MANIFEST_UNKNOWN","message":"manifest unknown","detail":"unknown tag=2.7.0-cuda12.8-cudnn9-runtime-NOPE"}]}

// repo name typo — 401, note there is no error="invalid_token" in www-authenticate
{"errors":[{"code":"UNAUTHORIZED","message":"authentication required","detail":[{"Type":"repository","Class":"","Name":"pytorch/pytorch-does-not-exist-xyz","Action":"pull"}]}]}

// token invalid — 401, and www-authenticate carries error="invalid_token"
www-authenticate: Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:pytorch/pytorch:pull",error="invalid_token"
{"errors":[{"code":"UNAUTHORIZED","message":"authentication required","detail":[{"Type":"repository","Class":"","Name":"pytorch/pytorch","Action":"pull"}]}]}
```

Four consequences for the adapter:

1. **The `401` bodies are identical.** The only discriminator between "wrong repo name" and "bad token"
   is `error="invalid_token"` in `WWW-Authenticate`. Read that header, not just the status. An adapter
   that maps all `401`s to `refused` will report a transient token problem as a supply refusal and skip
   a legitimate run; one that maps all `401`s to `indeterminate` will retry a typo forever.
2. **A missing `Docker-Content-Digest` is never a mismatch.** It appears on `200` only. `404`, `429` and
   `401` have no digest header at all. The check is `status == 200 && header == declared`.
3. **"Tag withdrawn" and "tag typo" cannot be told apart.** Both are `404 MANIFEST_UNKNOWN`. Do not try
   to word the error as one or the other; say "tag did not resolve" and print the tag. The *mismatch*
   case is the only one where the tag resolved and moved.
4. **The token step never validates the name.** `auth.docker.io` returned `200` with a usable token for
   `pytorch/pytorch-does-not-exist-xyz`. A typo is therefore detected at the manifest call, not at the
   token call — so the token call succeeding proves nothing about the repository.

---

## What could not be confirmed

- **Whether Vast accepts `repo@sha256:…`** in its `image` field. This is the one fact that decides
  whether the pin can be made load-bearing (§4.4). It needs a live instance, which is out of scope for a
  research ticket and costs money.
- **The rate-limit window's stability.** `w=3600` was measured on one IP on one day; Docker's docs still
  say 6 hours (`w=21600`). The adapter should read the header rather than trust either number, and
  nobody should assume the exemption on `pytorch/pytorch` is permanent — it is a publisher arrangement,
  not a protocol rule.
- **Whether the exemption follows the caller's identity or the repository.** The measurement shows the
  repo answered while the IP was at zero, which is consistent with a per-repository exemption, but a
  second IP was not available to separate the two.
- **5xx behaviour.** Not observed, so it is listed as `indeterminate` on the general principle that no
  statement about the tag was made, not on a captured response.

## Reproduce

```bash
TOKEN=$(curl -sS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:pytorch/pytorch:pull" | jq -r .token)
for TAG in 2.7.0-cuda12.8-cudnn9-runtime 2.6.0-cuda12.6-cudnn9-runtime \
           2.5.1-cuda12.4-cudnn9-runtime 2.5.1-cuda12.1-cudnn9-runtime; do
  printf '%-40s ' "$TAG"
  curl -sS -I -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
    -H "Accept: application/vnd.oci.image.index.v1+json" \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    "https://registry-1.docker.io/v2/pytorch/pytorch/manifests/$TAG" \
    | grep -i '^docker-content-digest:'
done
```

Run it on the machine that will spend the money, not on CI: the rate limit is per source IP, and the
exemption observed here is a property of this network's requests.

## What this settles for the spec

- The mechanism exists, needs no credential, and costs two calls for the first tag and one per tag after
  that.
- The four declarations are the digests in §3, and they are single-platform `amd64` manifests today.
- The declaration is the tag's top-level `Docker-Content-Digest`, which is also the index digest when a
  tag is multi-arch — one rule, no branch on architecture.
- `refused` and `indeterminate` are separable by exactly three signals: `404 MANIFEST_UNKNOWN`,
  `error="invalid_token"` in `WWW-Authenticate`, and `ratelimit-remaining: 0`. Everything else that is
  not a `200` with a digest is `indeterminate`.
- The pin does not yet constrain what the host runs, because the host pulls by tag (§4.4). The spec
  should either pull by digest or verify on the host, and should not describe the check as an image
  guarantee until it does.
