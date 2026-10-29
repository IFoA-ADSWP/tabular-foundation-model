# Vast API capabilities the lease and transport decisions wait on

Research for [#246](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/246).
Settled against the provider's own documentation and the installed CLI, not against what
this repository assumes.

- **Date:** 2026-10-29
- **CLI measured:** `vastai 1.7.0` (`vastai --version`)
- **Docs snapshot:** `docs.vast.ai` as served on 2026-10-29; index at
  <https://docs.vast.ai/llms.txt>
- **Spend:** zero. Only free, read-only calls were made (`search offers`, `show instances`,
  `--help`). No instance was created, so nothing here is confirmed by a completed paid run.
- **Scope:** the four questions in the ticket. Each section states the answer, the citation
  (URL + the statement relied on), what the repo currently assumes, and whether they agree.

## Summary

| # | Question | Provider says | Repo assumes | Agree? |
|---|---|---|---|---|
| 1 | Adopt an instance created without an id echo | `new_contract` on 200; **no** client-token/idempotency field exists; `label` **is** server-side filterable | Leak is unrecoverable; candidate 3 proposes an `adopt()` | **Partly** — adopt is possible, but only via a per-run-unique label, which the repo does not set |
| 2 | `execute` exit codes / stdout / truncation | `execute` runs **only `ls`, `rm`, `du`**; command ≤ 512 chars; output via a `result_url`; **no** remote exit status anywhere | `execute` is not a shell (correct); transport is `--onstart` + `logs` | **Yes** for the constraint; **no** for exit codes — they cannot be propagated at all |
| 3 | Payload a single call can carry back | No documented byte ceiling on any result path; `copy` (rsync) is the documented bulk channel | 440-char lines under a 500-char cap, 16 KB guard, `--tail 20000` | **Unresolved by docs** — the cap the repo fights is undocumented, and was measured, not specified |
| 4 | Pin an offer for a rerun | "Each offer ID can only be used to create one instance"; offers 404/410 when gone | "Never hardcode an offer ID"; "offer IDs are not searchable" | **Yes**, and the durable handle is `machine_id`, not the offer id |

---

## 1. Can an instance created without an id echo be found again and adopted?

**Answer: yes — by label — but only if the label is unique per run. There is no client
token or idempotency key to fall back on, and the docs give no handle for a create that
fails after the offer was accepted.**

### What the provider says

Creating an instance returns the id in the response body, on success:

> `Return value: Returns a json reporting the instance ID of the newly created instance:
> {'success': True, 'new_contract': 7835610}`
>
> — <https://docs.vast.ai/cli/reference/create-instance.md>

and the OpenAPI schema for `PUT /api/v0/asks/{id}` documents exactly one success field:

> `new_contract` — integer — "ID of the newly created instance contract" — example `1234568`
>
> — <https://docs.vast.ai/api-reference/instances/create-instance.md>

The API's own "Key Quirks" block repeats the trap that matters here:

> "`POST /api/v0/asks/{id}/` (create instance) returns `new_contract` as the instance ID,
> not `id`"
>
> — same page

The create request body has **no** idempotency token. Its documented properties are
`image`, `template_hash_id`, `label`, `disk`, `runtype`, `target_state`, `price`, `env`,
`cancel_unavail`, `vm`, `onstart`, `args`, `args_str`, `use_jupyter_lab`, `jupyter_dir`,
`python_utf8`, `lang_utf8`, `force`, `user`, `image_login`, `volume_info`. There is no
`client_token`, no request-id, no dedupe key. The only caller-supplied identity is `label`:

> `label` — string — "Custom name for the instance"
>
> — <https://docs.vast.ai/api-reference/instances/create-instance.md>

And `label` is a **server-side filter** on instance listing. `GET /api/v1/instances` takes:

> `select_filters` — "JSON object of column filters. Supported operators: `eq`, `neq`, `gt`,
> `gte`, `lt`, `lte`, `in`, `notin`. Filterable columns: `actual_status`, `gpu_name`,
> `verification`, `id`, **`label`**, and other columns stored directly on the contract record."
>
> — <https://docs.vast.ai/api-reference/instances/show-instances.md>

That response also returns `label_counts` ("Count of instances grouped by label. Unlabelled
instances are keyed by empty string"), so a duplicate or leaked instance under the same label
is visible rather than silent. The installed CLI exposes it directly:

```
 --label LABEL [LABEL ...]  filter by instance label; pass empty string '' for unlabeled
 -q, --quiet                only display numeric ids
 --raw                      Output machine-readable json
```

— `vastai show instances --help` (CLI 1.7.0). Observed: `vastai show instances --label '' --raw`
was accepted and returned `[]` (the account currently has no live instances) — the filter is a
real parameter, not a script-side convenience.

There is also a post-hoc setter, `vastai label instance <id> <label>`
(<https://docs.vast.ai/cli/reference/label-instance.md>), but it needs the id, so it cannot
rescue an id-less create.

**What is not documented:** whether `new_contract` is guaranteed on any non-200 path, and
whether a create can leave a live instance behind. The documented failure bodies are
`400 invalid_args`, `403` (own-machine), `404 no_such_ask` ("Instance type by id … is not
available"), and `410 no_such_ask` ("Offer no longer available"). The 404/410 bodies carry
`ask_id` (the *offer* id) and no contract id. Whether Vast bills a contract in the 410 case is
unanswered by the docs — see UNCONFIRMED.

### What the repo assumes

`scripts/gpu_helpers/vast_run.sh:564-577` parses `new_contract` out of the create response with
a regex + `json.loads`, and treats an empty result as terminal:

```bash
[ -z "$INSTANCE_ID" ] && { echo "FATAL: no instance id in the create response." >&2; exit 2; }
```

Issue #227, candidate 3, calls this out as "a create path that can leak with no id at all"
and proposes `Lease.adopt()` for it. The script does set a label, but a constant one:

```bash
--label "tabpfn-pilot" --raw          # vast_run.sh:567
```

So today the repo cannot distinguish *its* leaked instance from a previous run's leak, or from
a concurrent run's live instance, even though the API would let it.

### Agreement

**Partly.** The capability exists and the repo does not use it:

- Adopting by label is a documented, server-side query (`show instances --label …`,
  `select_filters: {"label": …}`) and needs no id.
- But a *constant* label is not an identity. To adopt unambiguously the label must be unique
  per run — `TFM_RUN_STAMP` already exists in `vast_run.sh` for exactly this kind of join key
  and could be folded into the label (`tabpfn-pilot-$RUN_STAMP`).
- There is no idempotency token, so **create cannot be made exactly-once**. A retry after an
  ambiguous failure can always produce two instances; `label_counts` is the documented way to
  detect that, not a way to prevent it.
- The proposed `adopt()` should therefore be specified as "find candidates by unique label
  and require exactly one; on zero or >1, refuse and report" — the API supports the first half
  and leaves the uniqueness argument to the caller.

---

## 2. How does `vastai execute` propagate exit codes and stdout, and where is output truncated?

**Answer: it does not propagate exit codes at all, and it cannot run a general command.
`execute` accepts three commands (`ls`, `rm`, `du`), takes a command string of at most 512
characters, and returns a *reference* to output (`result_url`) rather than the output on
stdout. The remote command's exit status never appears in any documented response.**

### What the provider says

The command whitelist is explicit:

> Available commands:
> | `ls` | List directory contents |
> | `rm` | Remove files or directories |
> | `du` | Summarize device usage for a set of files |
>
> "Returns the output of the command executed on the instance. May take a few seconds to
> retrieve results."
>
> — <https://docs.vast.ai/cli/reference/execute.md>

The underlying endpoint is `PUT /api/v0/instances/command/{id}`, and its request body caps the
command:

> `command` — string — "Command to execute on the instance" — example `ls -l` — **`maxLength: 512`**
>
> — <https://docs.vast.ai/api-reference/instances/execute.md>

The 200 response is a *queueing* acknowledgement, not a result:

> `success: true`, `writeable_path: /workspace`, `result_url: https://s3.amazonaws.com/vast.ai/instance_logs/abc123.log`,
> `msg: "Command is executing, wait a few seconds and then view the result_url"`
>
> — same page

The 400 body names the rejection the repo hit:

> `error: invalid_args`, `msg: "Invalid command given."`
>
> — same page

There is no exit-status field anywhere in the schema: no `returncode`, no `exit_code`, no
`status`. The CLI's own exit code reflects only whether the *API call* succeeded:

> "When a CLI command fails, it prints the error message from the API and exits with a
> non-zero status code."
>
> — <https://docs.vast.ai/cli/rate-limits.md>

That is a statement about API errors, not about the remote command. `execute` also accepts
`--schedule {HOURLY,DAILY,WEEKLY}`, confirming it is an asynchronous job, not a synchronous
exec (`vastai execute --help`).

**A documentation conflict worth recording.** Vast's own agent-facing `SKILL.md` shows:

```bash
vastai execute <id> "nvidia-smi"                         # Run command on instance
```

— <https://raw.githubusercontent.com/vast-ai/vast-cli/master/vastai/SKILL.md>

That contradicts the CLI reference above and the observed `400: Invalid command given`. The
reference plus the 400 is authoritative; the `SKILL.md` example is wrong. This matters because
it is the kind of first-party page a future reader would trust.

**Truncation.** No `execute`-result size limit and no `logs` line-length or total-size limit is
documented. The only documented `logs` knob is:

> `--tail` — "Number of lines to show from the end of the logs (default '1000')"
>
> — <https://docs.vast.ai/cli/reference/logs.md>

So the provider documents *line count* on `logs` and says nothing about per-line width or
per-response bytes. Anything about a 500-character line cap or a large `--tail` returning
nothing is measured behaviour, not specification — see UNCONFIRMED.

### What the repo assumes

The repo already knows the headline fact and records it in the runbook:

> "**`vastai execute` is NOT a remote shell — it runs only `ls`, `rm`, `du`.** This supersedes
> the earlier advice to use `--transport execute` for running commands."
>
> — `docs/REPRODUCIBILITY_RUNBOOK.md` §C.3

and mirrors it in the test double (`scripts/gpu_helpers/mock_vastai.sh:128-137`) so a mock
cannot validate a transport that cannot exist. The shipped default is `TRANSPORT="onstart"`
(`vast_run.sh:80`), with the bootstrap launched by `--onstart` and results read from
`vastai logs --tail 20000` (`vast_run.sh:689`), folded into `__ART__` lines of 440 chars
(`emit_artifacts.sh:26`), reassembled and verified against a self-declared line count and
sha256 (`verify_artifacts.py:100-122`).

Three stale statements remain, all saying `execute` is the default:

- `vast_run.sh:19` — `--transport T    execute | ssh                   (default: execute)`
- `vast_run.sh:22-30` — "WHY `execute` AND NOT SSH" plus "`vastai execute <id> '<cmd>'` runs
  commands over the API, so it needs no registered key at all"
- `docs/REPRODUCIBILITY_RUNBOOK.md` §C.10 troubleshooting row — "Use the default
  `--transport execute`"

On exit codes the repo has effectively already conceded the point: the box signals completion
with a `BOOTSTRAP FINISHED` marker parsed out of the log (`vast_run.sh:700-704`), because there
is no return code to read.

### Agreement

**Yes on the constraint, and more strongly than the repo states.** `execute` is not merely
"not a shell" — it is a three-command file-maintenance API. Consequences the lease design
should encode:

- **Exit codes cannot be propagated through `execute`.** Any design that expects a remote
  status back through this call is unimplementable, not just unimplemented. Completion and
  failure must be signalled in-band (log markers) or out-of-band (`copy` of a result file).
- **stdout is not a stream.** It lands in an S3 object behind `result_url`, after a delay.
  Reading it is a second, separate fetch.
- **512 characters is the ceiling on the command**, which rules out inline payloads entirely
  and is three orders of magnitude below what the artifact transport needs.
- The stale `(default: execute)` comments and the §C.10 row should be corrected; they are the
  exact contradiction the runbook's own §C.3 was written to end.

---

## 3. What payload size can a single call carry back, against the payload a real run returns?

**Answer: the provider documents no byte ceiling on any result path, so "how much can one call
carry back" has no documented number. What it does document is an *alternative channel* —
`vastai copy` (rsync) — for bulk data, plus a hard 512-character ceiling on the `execute`
command and a small ceiling on the start script. The 500-char-per-line trimming the repo
designs around is real but undocumented.**

### What the provider says

Three return paths, three different documented limits:

1. **`execute`** — the command is capped, not the output: `maxLength: 512`
   (<https://docs.vast.ai/api-reference/instances/execute.md>). Output is an S3 object at
   `result_url` with **no documented size limit**.
2. **`logs`** — `--tail` counts *lines*, default 1000
   (<https://docs.vast.ai/cli/reference/logs.md>). No documented per-line or total-byte limit.
   The endpoint and its response (`result_url` to an S3-hosted `.log`) are documented at
   <https://docs.vast.ai/api-reference/instances/show-logs.md>. The page says nothing about
   line truncation.
3. **`copy`** — the documented bulk channel:

   > "The copy command uses rsync and is generally fast and efficient, subject to single link
   > upload/download constraints."
   >
   > — <https://docs.vast.ai/guides/instances/storage/data-movement.md>

   with no size cap stated, and a comparative note that scp over the *proxy* is for
   "smaller transfers (less than 1 GB)" while direct ssh or cloud sync is recommended above
   that. `vastai copy C.<id>:/workspace/results/ local:./results/` is the documented
   instance→local form (<https://docs.vast.ai/cli/reference/copy.md>).

Two **conflicting** documented numbers exist for the start script, and neither matches the
repo's observed one:

> "`--onstart-cmd` is limited to **16KB**." — <https://docs.vast.ai/cli/hello-world.md>
>
> "`onstart` field is limited to 4048 characters -- gzip+base64 for longer scripts"
> — the "Key Quirks" block of every API reference page, e.g.
> <https://docs.vast.ai/api-reference/instances/create-instance.md>

### What the repo actually returns, measured

The committed pilot artifact tree (`outputs/finetune/pilot`, 3 datasets × 3 arms) through the
repo's own emitter:

```
__ARTIFACTS_INFO__ bytes=194400 sha256=6e… lines=590 files=28
```

and the full emitted log text for that payload is **264,081 bytes** (`emit_artifacts.sh |
wc -c`). So the real, committed payload is ~190 KB of tar.gz rendered as ~264 KB of
base64-in-log — about 590 lines at 440 characters each.

Per-arm, for the shape the fine-tuning run returns (`predictions.npy` + `ground_truth.npy` +
`meta.json`), the committed files are `8128 B` (`float64`, 1000 test rows) and `4128 B`
(`int32` labels). A 3-seed × 5-fold run multiplies one arm by 15:

| Quantity | Committed tree (measured) | 3 seeds × 5 folds (arithmetic) |
|---|---|---|
| tar.gz bytes | 194,400 | ~1.0 MB |
| base64 chars at 440/line | 590 lines | ~3,000 lines |
| **log text to transfer** | **264 KB** | **~1.3 MB** |

The repo's own estimate (~3,800 lines for 3×5, `vast_run.sh:680-686`) is the same order, so
the arithmetic and the measurement agree. At `--tail 20000` and a 20-second poll over a
40-minute ceiling, that is up to ~120 fetches of a ~1.3 MB tail — a real, if secondary, cost
and timeout exposure.

### Agreement

**The docs do not settle the number; they remove the need for one.** Read carefully, the
provider's position is not "the log can carry N bytes" but "use `copy` for files":

- No documented ceiling exists for `execute` output or `logs` output, so the repo's 500-char
  finding is not contradicted — it is simply **outside the documented contract**. Designing to
  it is prudent and unfalsifiable from the docs.
- The **measured** payload (194 KB / 590 lines; ~1 MB / ~3,000 lines at 3×5) is comfortably
  inside `--tail 20000` and inside any plausible log-object size. The transport's risk is not
  volume; it is line-width trimming, which is why the receiver's self-declared line count and
  sha256 (`verify_artifacts.py`) is the right defensive move.
- **`copy` is the capability the repo is not using.** It is the documented answer to "what can
  one call carry back", and it is a *pull to local*, so it also removes the tail-window,
  line-cap and mid-flight-truncation hazards in one step. The catch is in the same docs: copy
  "uses ssh authentication" (the warning against copying to `/root`/`/` says so), and this
  account's team context blocks SSH keys — see UNCONFIRMED 5. `cloud copy` (S3/Dropbox/Drive)
  needs a configured cloud connection and does not need SSH, which makes it the candidate
  worth testing before either the log transport or SSH is ruled in.
- The 16 KB guard at `vast_run.sh:533-538` measures `$ONSTART_FILE` from **inside** the
  `{ … } > "$ONSTART_FILE"` block that is still writing it, so it under-counts by the trailing
  lines (the bootstrap decode and `bash /tmp/tfm-bootstrap.sh`). It is a guard that measures
  itself — #227 "Found in passing" — and its threshold (16000) is defensible against the
  observed `len(args) > 16384` but not against the documented 4048. Do not "fix" the number
  until which field is capped is settled (UNCONFIRMED 6).

---

## 4. Can an offer be pinned so a rerun selects the same machine class?

**Answer: not by offer id. An offer id is single-use, expires, and — despite being listed as a
search field — does not match when queried. What *is* pinnable is `machine_id`, which is a
working filter and survives the offer that pointed at it.**

### What the provider says

The decisive sentence is in the create-instance reference:

> "Creates an instance from an offer ID (which is returned from "search offers"). **Each offer
> ID can only be used to create one instance.**"
>
> — <https://docs.vast.ai/cli/reference/create-instance.md>

Expiry is documented as first-class error behaviour on the same endpoint:

> `404` — "Offer not found or not available" — `error 404/3603: no_such_ask Instance type by id
> 1234567 is not available.`
>
> `410` — "Offer no longer available (when cancel_unavail is true and instance cannot start)"
> — `error 410/3907: no_such_ask Instance type 1234567 is no longer available.`
>
> — <https://docs.vast.ai/api-reference/instances/create-instance.md>

So an offer id identifies a *rentable moment on a machine*, not a durable SKU.

The documented `search offers` field table lists `id` as queryable:

> `id` | int | instance unique ID
>
> — <https://docs.vast.ai/cli/reference/search-offers.md>

but `machine_id` also:

> `machine_id` | int | machine id of instance

### What I observed (free, read-only, CLI 1.7.0)

| Query | Result |
|---|---|
| `search offers 'num_gpus=1 gpu_ram>=23 dph<0.40' -o 'dph+'` | rows returned; first row `id=47185200`, `machine_id=31186` |
| `search offers 'id==47185200'` | **0 rows** |
| `search offers 'id==47185196'` | **0 rows** (second attempt, different row) |
| `search offers 'id==47185200 rentable=any' -n` | **0 rows** |
| `search offers 'ask_id==47185200'` | `Failed with error 400: ask_id is not a valid search key` |
| `search offers 'machine_id==31186'` | **2 rows** |

Two independent attempts, including with `-n` (defaults disabled) and `rentable=any`, confirm
the repo's operational note. Note the *raw* offer object has both `id` and `ask_contract_id`
(equal in the row I inspected: `47185200`), and no `ask_id` key; the field the docs call `id`
is present, but querying it does not match its own value. The `search offers` and
`search instances` doc pages are also copies of one another — `vastai search instances --help`
prints `usage: vastai search offers …` and lists offer fields — so Vast currently ships **no**
separate instance-search command in this CLI version; `show instances` with filters is the
instance path.

### What the repo assumes

`docs/REPRODUCIBILITY_RUNBOOK.md` §C.3:

> "**Never hardcode an offer ID.** The marketplace turns over within minutes — an offer
> recommended half an hour earlier had already vanished, and prices for the same card class
> span $0.15–2.14/hr in a single session. Pass `--query` and let it select at run time."
>
> "**Offer IDs are not searchable.** `id == <n>` returns zero rows; re-running the original
> query and matching on `id` is the only way to check whether an offer still exists."

The launcher supports `--offer-id` (`vast_run.sh:13`) which skips selection — an escape hatch
that the runbook's own prohibition argues against.

### Agreement

**Yes on both claims, and the docs' field table is the thing that is wrong.** But the repo's
conclusion ("re-running the original query and matching on `id` is the only way") is not the
best available answer:

- An offer id is **not durable** — documented single-use, documented 404/410 expiry — so
  `--offer-id` can never be a reproduction mechanism, only a one-shot override.
- `machine_id` **is** a working, documented filter and outlives the offer. A rerun that must
  land on the same machine class should pin `machine_id` (or a small set of them) and let
  offer selection re-rank that machine's *current* offers. That preserves the runbook's
  "never hardcode an offer" while making "same machine class" reproducible — and the repo
  already tracks `machine_id` for retry exclusion (`vast_run.sh:614`, `EXCLUDE_MACHINES`), so
  the handle is in hand.
- Pinning a machine is not pinning a *price*: the same machine can reprice between runs. A
  reproducibility claim must therefore record machine, GPU, and paid `dph_total` (the run
  record already does), and state that the machine class was pinned, not the offer.

---

## UNCONFIRMED

Not settled by a primary source. Each is a real gap in the provider's documentation, not a
gap in the search.

1. **The 500-character log line cap.** No Vast page documents trimming of `logs` output by
   width. The cap is real in this repo's experience (`docs/REPRODUCIBILITY_RUNBOOK.md` §C.3:
   "a base64 artifact payload came back at exactly 500 chars while the next-longest line in the
   whole log was 363"), but it is a measurement, not a specification. Treat 440-char folding
   as defence-in-depth against an undocumented behaviour.
2. **What a large `--tail` does.** `--tail 200000` "silently returns NOTHING" per
   `vast_run.sh:680-686`; the docs describe only `--tail` as a line count with default 1000.
   No documented maximum, no documented failure mode.
3. **The maximum size of a single `execute` `result_url` object, and of one `logs` response.**
   Neither is bounded in any page, so the question "what can one call carry back" has no
   documented answer — only the recommendation to use `copy` for files.
4. **Whether a create that fails with 404/410 (or whose response is lost) can leave a billable
   instance behind.** The documented failure bodies carry `ask_id`, not `new_contract`, and do
   not say whether a contract was created. This is exactly the leak that motivates `adopt()`,
   and it needs a live test (create with a deliberately stale offer and then list instances by
   label) to settle.
5. **Whether `vastai copy` works on this team-context account.** `copy` is documented as using
   ssh authentication and the team context refuses account-level SSH keys
   (`docs/REPRODUCIBILITY_RUNBOOK.md` §C.3). Since `copy` is the documented bulk channel, this
   is the highest-value open item in this note: if it works, the log transport is avoidable
   entirely. `cloud copy` (S3/Dropbox/Drive) is the fallback and needs a configured connection.
6. **Which `onstart` field is capped, and at what.** The docs give **16 KB** for `--onstart-cmd`
   (hello-world) and **4048 characters** for the `onstart` field (API "Key Quirks"), while the
   repo observed `400/3471: len(args) > 16384`. Three numbers for what may be two different
   fields. The repo's 16000 guard cannot be validated until this is resolved.
7. **Whether `label` is unique per create.** Nothing documents label uniqueness, length limits,
   or what `select_filters: {"label": …}` does with duplicates. `label_counts` implies
   duplicates are tolerated. Any `adopt()` built on labels must therefore treat >1 match as an
   error rather than assuming uniqueness.

---

## Appendix: what was run

Free and read-only; nothing created, nothing billed.

```bash
vastai --version                                    # 1.7.0
vastai execute --help
vastai search instances --help                      # prints `usage: vastai search offers …`
vastai show instances --help
vastai show instances --label '' --raw              # -> []
vastai search offers 'num_gpus=1 gpu_ram>=23 dph<0.40' -o 'dph+'
vastai search offers '<id from above>' …            # id==, ask_id==, machine_id== probes
bash scripts/gpu_helpers/emit_artifacts.sh outputs/finetune/pilot | wc -c   # 264081
```

Documentation read (all under <https://docs.vast.ai>): `cli/reference/{create-instance,
execute, logs, copy, search-offers, search-instances, label-instance}.md`,
`api-reference/instances/{create-instance, execute, show-logs, show-instances}.md`,
`guides/concepts.md`, `guides/instances/storage/data-movement.md`, `cli/rate-limits.md`,
`cli/hello-world.md`, and `vast-ai/vast-cli` `vastai/SKILL.md` from GitHub.
