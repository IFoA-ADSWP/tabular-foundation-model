# What the licences permit: does a student inherit TabPFN's terms

Research note for wayfinder ticket [#371](https://github.com/IFoA-ADSWP/tabular-foundation-model/issues/371). Branch `research/distill-licence`, never merged.

**Status:** research, **not legal advice**. Every claim below is either a quotation from a licence or terms document with its clause cited, or labelled interpretation. Where a source could not be read, the note says `unknown` rather than guessing.

**Verified:** 2026-10-31. Licences and terms change; re-verify before any decision, and note that the Prior Labs licences are expressly revocable.

---

## 1. The question, stated exactly

If we train a small "student" model on outputs produced by a TabPFN teacher, what terms does the student carry — and can an insurer deploy that student, air-gapped, as part of a commercial product?

Three things have to be separated, and are often conflated:

1. the **weights licence** that governs the teacher artefact;
2. the **service terms** that govern the hosted teacher *as a service*;
3. the **status of the student**, which is a new artefact nobody licensed directly.

---

## 2. (a) Facts, quoted

### 2.1 TabPFN v3 / v3.5 weights: non-commercial, and outputs are restricted separately from derivatives

Authority: `TABPFN-3 License v1.0`, last revised 24 March 2026, Prior Labs GmbH — <https://huggingface.co/Prior-Labs/tabpfn_3/blob/main/LICENSE> (sha256 `dca491280b68f471312a15d54add7b8e724adf19fb0e113544b1ef91e060f5d5`). The v3.5 text is identical in every clause quoted here (`TABPFN-3.5 License v1.0`, 9 September 2026, sha256 `9570fdd687bb76ed45499412ad57d6ba949848e6d731f1242572bb57f2f73ae1`).

**Outputs are expressly *not* derivatives** — the licence draws that line itself:

> "**Derivative**" means any (i) modified version of the TABPFN-3 Model (including but not limited to any customized, fine-tuned, retrained, or otherwise adapted version thereof), (ii) work based on the TABPFN-3 Model, or (iii) any other derivative work thereof. For the avoidance of doubt, Outputs are not considered Derivatives under this License.
> — §1(a)

**But outputs carry their own, separately worded restriction**:

> **Outputs.** We claim no ownership rights in and to the Outputs. You are solely responsible for the Outputs you generate and their subsequent uses in accordance with this License. Outputs may be used only for Non-Commercial Purposes. Any use of Outputs in production systems, business processes, commercial research services, client deliverables, or revenue-generating activities requires a separate commercial license. You may not use Outputs to train, fine-tune, or distill a model that is competitive with the TABPFN-3 Model.
> — §2(d)

**Distillation for commercial use is written into the definition of non-commercial**:

> For clarity, use (a) for any revenue-generating activity, (b) in direct or indirect interactions with end users or production systems, or (c) **to train, fine-tune, or distill other models for commercial use**, in each case is not a Non-Commercial Purpose.
> — §1(c) (emphasis added)

**Restrictions reach "any data produced by" the model**, not just the model:

> use, modify, copy, reproduce, create Derivatives of, or Distribute the TABPFN-3 Model (or any Derivative thereof, or **any data produced by the TABPFN-3 Model**), in whole or in part, (i) for any commercial or production purposes, …
> — §4(a) (emphasis added)

**The grant is revocable at will, and restrictions flow to derivatives**:

> … Company grants you a non-exclusive, worldwide, non-transferable, non-sublicensable, **revocable**, royalty-free and limited license … Any restrictions set forth herein regarding the TABPFN-3 Model also apply to any Derivative you create or that are created on your behalf.
> — §2(a); and §7(b): "We may terminate this License, in whole or in part, at any time upon notice (including electronic) to you."

**Indemnity covers output use**:

> … any Claims arising out of or related to (a) your access to or use of the TABPFN-3 Model (**including in connection with any Output, results or data generated from such access or use**) …
> — §6

**No hosted service** without a commercial licence, even of a derivative — §3(d): "You may not Distribute, host, or make available the TABPFN-3 Model or any Derivative as part of a hosted, managed, API, or SaaS service (whether paid or free) without a separate commercial license."

### 2.2 TabPFN v2 is **not** plain Apache 2.0 — it is Apache + an output-distillation attribution clause

Authority: `Prior Labs License, Version 1.1, May 2025` — <https://huggingface.co/Prior-Labs/TabPFN-v2-clf/blob/main/LICENSE.txt> (sha256 `08b1851b4b6136b5fb0cb124d3258e0d91e3e1623f1be5904b77e4d270d112d8`); same text for the regressor at `Prior-Labs/TabPFN-v2-reg`.

> This license is a derivative of the Apache 2.0 license (http://www.apache.org/licenses/) with a single modification: The added Paragraph 10 introduces an enhanced attribution requirement inspired by the Llama 3 license.
> — preamble

Paragraph 10, in full:

> **10. Additional attribution.**
> If You distribute or make available the Work or any Derivative Work thereof relating to any part of the source or model weights, or a product or service (including another AI model) that contains any source or model weights, You shall (A) provide a copy of this License with any such materials; and (B) prominently display "Built with PriorLabs-TabPFN" on each related website, user interface, blogpost, about page, or product documentation. **If You use the source or model weights or model outputs to create, train, fine tune, distil, or otherwise improve an AI model, which is distributed or made available, you shall also include "TabPFN" at the beginning of any such AI model name.** To clarify, internal benchmarking and testing without external communication shall not qualify as distribution or making available pursuant to this Section 10 and no attribution under this Section 10 shall be required.

Checked by full-text search of the 201-line file: the word "commercial" appears only in Apache's boilerplate warranty disclaimer (§7). **There is no non-commercial clause and no prohibition on output-derived training in the v2 weights licence.** The v2 grant itself is Apache's perpetual, irrevocable copyright and patent grant (§2, §3), so unlike v3 it cannot be revoked.

The URL the licence text prints for itself, `http://priorlabs.ai/tabpfn-license`, returns HTTP 404 as of 2026-10-31; the Hugging Face copy is the readable authority.

### 2.3 "v2" is a narrow window: 2.5 and 2.6 are non-commercial

The Prior Labs docs list each family's weights licence: TabPFNv2 under the Prior Labs License; **TabPFN-2.5 and TabPFN-2.6 under `TABPFN-2.5 License v1.1` / `TABPFN-2.6 License v1.0`**, which open "freely available for your non-commercial and non-production use" and contain the same §2(d) output clause as v3 — <https://docs.priorlabs.ai/models#tabpfn-model-license>. Also from that page:

> The code in the [TabPFN repository](https://github.com/PriorLabs/TabPFN) is licensed under Apache 2.0, **starting with `tabpfn` 9.0.0**. Model weights are licensed separately.

The GitHub repo `LICENSE` file is therefore Apache 2.0 **for code only**; it says nothing about weights (<https://github.com/PriorLabs/TabPFN/blob/main/LICENSE>, and `README.md` §"License": "Model weights are licensed separately.").

### 2.4 The hosted API is governed by different documents entirely

The v3 licence says so itself:

> **This License applies only to customers who download the TABPFN-3 Model. For customers accessing the TABPFN-3 Model through our API, only our General Terms and Conditions apply.**
> — TABPFN-3 License §preamble

So an API user is **not** bound by the non-commercial weights licence. They are bound by the `General Terms and Conditions` (status 23 June 2026) — <https://priorlabs.ai/general-terms-and-conditions> — and by the `Acceptable Use Policy` (status January 2025) — <https://priorlabs.ai/aup> — which the GTC incorporates as material obligations:

> The Customer acknowledges that the provisions set out in the AUP shall be deemed material obligations under this Contract.
> — GTC §5.5

What the GTC says about outputs, in both directions:

> **The Customer may freely use the Service Results.** PriorLabs provides the Service Results "as is". The Customer is responsible for reviewing any Service Results of its use of the Contract Software.
> — GTC §8.2

> PriorLabs may use the Service Results to develop, test and improve the Contract Software, in particular the underlying artificial intelligence systems and/or foundation models.
> — GTC §8.4

> PriorLabs remains the sole owner of all right, title, and interest in the Contract Software, including but not limited to any models, algorithms, model weights, and neural networks.
> — GTC §6.1

But the GTC also lists **knowledge distillation** as grounds for blocking access:

> … if there are reliable indications that the Customer or, where applicable, one of its employees is violating or has violated material obligations under this ToS, including the AUP, **in particular by engaging in reverse engineering or knowledge distillation of the Contract Software**, or by exceeding the agreed usage parameters …
> — GTC §10.1.1 (emphasis added)

and the AUP prohibits extracting know-how:

> Customer may not misappropriate, reverse-engineer, copy, disassemble, decompile, extract source code, trade secrets, or know-how, including PriorLabs' models, algorithms or artificial intelligence systems …
> — AUP §1

The contract is formed on registration, not on any act of training: "The contract is concluded … when the Customer registers and sets up an account via the Services … or, at the latest, upon PriorLabs granting the Customer access to the Services" (GTC §2.1).

**Fact, not interpretation:** the API route gives you a *different* instrument from the weights route — one that says results are freely usable (§8.2) while separately treating distillation as a material breach (§10.1.1). The two clauses are in tension and neither is qualified by the other.

### 2.5 The licensor's own stated reading of the v3 licence

Vendor FAQ is evidence of the licensor's position, not of law — <https://docs.priorlabs.ai/models#tabpfn-model-license>:

> **If we train a model from scratch without the weights, is that covered by this license?** — If you do not use any TabPFN model weights, checkpoints, or other licensed model elements, then the non-commercial license does not apply to that separately developed model. **However, if you use TabPFN (or its outputs) to train, guide, fine tune, or distill another model for commercial use, that is not permitted under this license.**

> **Can we use TabPFN to train a commercial model indirectly?** — No. Using TabPFN (or its outputs) to train, fine tune, distill, or otherwise improve a commercial model is not allowed without a commercial agreement.

> **What about outputs generated by the model?** — Outputs are yours, but they can only be used for non-commercial evaluation and research. Using them in production or for any business decisions requires a commercial license.

> **Do non-commercial rules also apply to derivative models or fine tuned versions?** — Yes.

### 2.6 The Apache-licensed alternatives — what the repositories actually contain

The repo catalog (`docs/analyses/tabular_foundation_models_catalog.md`, §Licences) is stale on several of these; issue #209 already flags staleness generally. Each row below was checked against the licence **file**, not the README's claim.

| Model | Code/weights licence file actually found | Notes |
|---|---|---|
| **TabDPT** | `layer6ai-labs/TabDPT-inference` → `LICENSE` = Apache License 2.0, full 202-line text. Weights `Layer6/TabDPT` on HF: card tag `license: apache-2.0`, `LICENSE` file in repo. | **The training repo is not Apache.** `layer6ai-labs/TabDPT-training/LICENSE`: "© Copyright 2018 The Toronto-Dominion Bank … Permission is hereby granted … to use, copy, distribute, publish and modify the Software, **only for research and for no other purpose**. For clarity, and without limitation, **this licence does not permit use of Software or any part thereof for commercial purposes.**" |
| **TabSwift** | `LAMDA-Tabular/TabSwift` → `LICENSE` = **MIT**, "Copyright (c) 2026 LAMDA-Tabular". HF `LAMDA-Tabular/TabSwift` card front-matter says `license: apache-2.0`. | Authors are Si-Yang Liu and Han-Jia Ye (ICML 2026) — **not** ServiceNow. `github.com/ServiceNow/TabSwift` returns 404. Repo and model card disagree on MIT vs Apache; both permissive. |
| **TabSTAR** | `alanarazi7/TabSTAR` → `LICENSE` = **MIT**, "Copyright (c) 2025 Alan Arazi"; README §License: "MIT". Weights `alana89/TabSTAR` on HF: card tag `license: cc-by-4.0`; paper-version fold checkpoints tagged `license: mit`. | **Not** ServiceNow, and not Apache 2.0. `github.com/ServiceNow/TabSTAR` returns 404. |
| **SAP-RPT-OSS** | `SAP-samples/sap-rpt-1-oss` → `LICENSE` = Apache 2.0, `LICENSES/Apache-2.0.txt`, `REUSE.toml` SPDX `Apache-2.0` covering `path = "*"`. HF `sap/sap-rpt-1-oss`: card tag `apache-2.0`, gated, contains `2025-11-04_sap-rpt-one-oss.pt` and `l2/base.pt.license`. | **README contradicts the code licence for the checkpoints:** "The model checkpoints have been trained on [the T4 dataset], which, in turn, is a subset of [the TabLib dataset]. As such, **they inherit the same restrictions described therein and in particular they are only intended for research purposes.**" |

On the SAP/T4 chain: the T4 dataset card (`mlfoundations/t4-full`) declares `license: other` with `license_link` pointing at `approximatelabs/tablib-v1-sample`, and both dataset cards are **gated** — the actual restriction text was not readable without authenticated acceptance on 2026-10-31. So the *content* of the inherited restriction is **unknown**; what is verified is SAP's own statement that a restriction exists and that the checkpoints are "only intended for research purposes".

Also verified: `github.com/yandex-research/tab-dpt` — the repo the catalog points at — returns **404**. The canonical repos are `layer6ai-labs/TabDPT-inference` and `layer6ai-labs/TabDPT-training`.

### 2.7 Catalog corrections

| Catalog claim | What the licence file says |
|---|---|
| "TabPFN … Non-commercial (v3) / Apache 2.0 (v2)" | v2 is Apache 2.0 **plus** a mandatory attribution/naming clause (§10), including for models distilled from outputs. Not plain Apache. |
| "TabDPT … Apache 2.0" | True of inference code and the published weights; **false of the training code** (TD Bank research-only licence). |
| "TabSwift / TabSTAR … ServiceNow … Apache 2.0" | No ServiceNow repository exists for either. TabSwift is LAMDA-Tabular, MIT (repo) / Apache-2.0 (HF tag); TabSTAR is Alan Arazi, MIT (repo) / CC-BY-4.0 (weights). |
| "SAP-RPT-OSS … Open-source" | Code Apache 2.0; **checkpoints are stated by SAP to be research-only**, inheriting T4/TabLib restrictions. |

---

## 3. (b) Interpretation — **not legal advice**

### 3.1 The student is a new artefact; the licence binds a *person*, not a file

A software licence is a permission addressed to a licensee. Nothing in the v3 licence says a model trained on its outputs *becomes* a licensed derivative — the licence goes out of its way to say the opposite for Outputs (§1(a)). What the v3 licence does instead is restrict what **the licensee may do with outputs** (§2(d), §4(a)) and define commercial distillation as outside the non-commercial purpose (§1(c)).

So the honest statement of the mechanism is: *the restriction attaches to the act of using the outputs, not to the bytes of the student.* Whether a downstream insurer who never accepted any Prior Labs terms is bound is therefore not answered by the licence text at all.

### 3.2 The two positions a lawyer would test

**Position A — "only the student must be clean."**
The student is an original work; it contains no TabPFN weights, no TabPFN code, and Outputs are expressly not Derivatives. An insurer that receives the student has no contract with Prior Labs, so no contractual restriction reaches it. On this view the teacher's licence is a compliance problem for whoever trained, and a clean v2/Apache teacher changes nothing about the student's own status — it merely avoids creating that problem. Air-gapped deployment is unobjectionable.

**Position B — "the teacher choice contaminates the lineage."**
The restriction is drafted to reach data and use, not artefacts: §4(a) reaches "any data produced by the TABPFN-3 Model … for any commercial or production purposes", and §1(c) puts commercial distillation outside the grant outright. On this view a student trained on v3 outputs for a commercial deployment is a restricted use whenever it is used commercially, whoever holds it, because the *use* of the training data was never licensed. The licensor asserts exactly this in its FAQ (§2.5). The practical bite is not prior restraint but **chain of title**: an insurer's procurement will ask for a warranty that the model may be used commercially; a supplier whose training corpus was v3 outputs cannot give that warranty without a Prior Labs commercial licence, and the licence is revocable at will (§7(b)) and indemnity-bearing for output use (§6).

Both positions are arguable on the text. Position B is the licensor's stated position, which is the one that matters for procurement risk even if Position A is legally stronger.

### 3.3 What "air-gapped" does and does not buy

An air gap removes the **teacher from the runtime**: no API call, no data egress, no ToS acceptance at inference, no §3(d) hosted-service question about the teacher. It removes none of the **training-act** analysis above. Air-gapping is necessary for an insurer's model-risk and data-residency requirements; it is not a licence cure.

### 3.4 The hosted-API route is not a clean workaround

It is tempting to read "the Customer may freely use the Service Results" (GTC §8.2) as permission to distil via the API. The same contract says knowledge distillation of the Contract Software is a material breach justifying a block (§10.1.1), and the AUP forbids extracting know-how from the models (§1). A distillation campaign against the API is therefore at best ambiguous on the licensor's own documents. Note also that these are **service terms, not a copyright licence**: they govern the account, and breach leads to blocking and termination, not to a claim that the student infringes.

### 3.5 What the v2 route actually costs

v2 is the only TabPFN generation whose weights licence permits commercial use and expressly contemplates output-derived training — at the price of §10 attribution: a copy of the licence with the materials, "Built with PriorLabs-TabPFN" on related sites/UI/docs, and, if the distilled model is "distributed or made available", the name must begin with "TabPFN". Handing a student to an insurer is making it available; internal benchmarking "without external communication" is exempt.

---

## 4. (c) Open questions a lawyer must answer

1. **Is a model trained on outputs a derivative work of the teacher** under the governing copyright law, independent of what the licence says? If yes, does the v3 "Outputs are not Derivatives" sentence bind a court, or is it only a contractual estoppel between the parties?
2. **Does the restriction bind a downstream recipient** who never accepted the v3 licence — under contract (no privity), under copyright (derivative/anti-circumvention), or not at all?
3. **Which law governs?** v3 is German law, Berlin courts (§10); the GTC is German law with CISG excluded (§15.2). A UK insurer deploying the model raises questions of mandatory rules applicable in the UK.
4. **Is a distilled student "competitive with the TABPFN-3 Model"** (§2(d))? On what test — benchmark parity, task overlap, market substitution? The clause is undefined and the burden of the ambiguity falls on whoever trained.
5. **Does "distill other models for commercial use" (§1(c)) catch a student trained for research and only later sold** — i.e. does the characterisation date from training or from deployment?
6. **What survives termination?** §7(d) requires ceasing use and deleting "the TABPFN-3 Model and any Derivatives". It does not mention Outputs or models trained on Outputs. Does a student survive? The omission is silent, not permissive.
7. **Do copyright/DB rights in the *pretraining data*** (rather than in the weights) create an independent claim against a student trained on synthetic-data teachers? TabPFN v3 is pretrained on synthetic data, which weakens a data-provenance claim; TabDPT and SAP-RPT-OSS, by contrast, are trained on real data with stated restrictions (§2.6). This is a separate exposure from the model licence.
8. **What is the T4/TabLib restriction?** Its text is gated and unread (`unknown`, §2.6). If SAP-RPT-OSS checkpoints are research-only, the SAP route closes on its own terms.
9. **Does an insurer's own model-risk regime** (PRA SS1/23, internal validation, third-party outsourcing) accept a model whose training provenance is contested even if the legal position is defensible? This is a governance question that can dominate the legal one.
10. **Would a Prior Labs commercial licence cure all of the above** — i.e. is it offered on terms that permit distillation and air-gapped redistribution, or does it merely permit API use? The FAQ points to "API or a commercial license" without publishing distillation terms.

---

## 5. Sources (all read 2026-10-31)

| Document | URL | Retrieval note |
|---|---|---|
| TABPFN-3 License v1.0 (weights) | https://huggingface.co/Prior-Labs/tabpfn_3/blob/main/LICENSE | full text read, sha256 `dca4912…` |
| TABPFN-3.5 License v1.0 (weights) | https://huggingface.co/Prior-Labs/tabpfn_3_5/blob/main/LICENSE | full text read, sha256 `9570fdd…` |
| Prior Labs License v1.1 (TabPFN v2 weights) | https://huggingface.co/Prior-Labs/TabPFN-v2-clf/blob/main/LICENSE.txt | full text read (201 lines), sha256 `08b1851…`; the self-cited `priorlabs.ai/tabpfn-license` is 404 |
| Prior Labs General Terms and Conditions (23 Jun 2026) | https://priorlabs.ai/general-terms-and-conditions | full text read; `priorlabs.ai/terms` redirects here |
| Prior Labs Acceptable Use Policy (Jan 2025) | https://priorlabs.ai/aup | full text read |
| Prior Labs models + licence FAQ | https://docs.priorlabs.ai/models | full text read |
| TabPFN repo code licence | https://github.com/PriorLabs/TabPFN/blob/main/LICENSE | Apache 2.0; code only, from `tabpfn` 9.0.0 |
| TabDPT inference licence | https://github.com/layer6ai-labs/TabDPT-inference/blob/main/LICENSE | Apache 2.0, 202 lines |
| TabDPT training licence | https://github.com/layer6ai-labs/TabDPT-training/blob/main/LICENSE | TD Bank, research-only, 27 lines |
| TabDPT weights | https://huggingface.co/Layer6/TabDPT | card tag `apache-2.0`, `LICENSE` present |
| TabSwift licence | https://github.com/LAMDA-Tabular/TabSwift/blob/main/LICENSE | MIT, © LAMDA-Tabular; HF card tag `apache-2.0` |
| TabSTAR licence | https://github.com/alanarazi7/TabSTAR/blob/main/LICENSE | MIT, © Alan Arazi; weights `alana89/TabSTAR` tag `cc-by-4.0` |
| SAP-RPT-OSS licence + README | https://github.com/SAP-samples/sap-rpt-1-oss | Apache 2.0 code; README says checkpoints research-only |
| SAP-RPT-OSS weights | https://huggingface.co/sap/sap-rpt-1-oss | gated; card tag `apache-2.0`; contains `l2/base.pt.license` |
| T4 / TabLib dataset terms | https://huggingface.co/datasets/mlfoundations/t4-full | **gated**; `license: other`, text `unknown` |

---

## 6. The one line

**A TabPFN v2 teacher leaves the option open** — its Apache-derived licence permits commercial use and expressly contemplates models trained on its outputs, at the cost of the §10 "TabPFN" naming and "Built with PriorLabs-TabPFN" attribution; **a TabPFN v3 or v3.5 teacher closes it**, because commercial distillation is outside its non-commercial grant (§1(c), §2(d)) unless a Prior Labs commercial licence is bought.
