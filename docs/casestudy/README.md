# 📚 Deepfake Case Studies — Research & Architectural Analysis

Welcome to the **Deepfake Agentic AI Case Study Series**. This directory contains five in-depth forensic investigations exploring real-world deepfake threat scenarios, analyzing the limitations of traditional single-model classifiers, and detailing how the multi-signal agentic architecture of this platform solves each challenge.

All case studies are grounded in peer-reviewed academic literature, industry standards (C2PA, NIST, ISO), and documented cyber-forensic incidents.

---

## 📑 Case Study Matrix

| # | Case Study | Threat Scenario | Primary Forensic Focus | Academic Benchmark / Source |
| :--- | :--- | :--- | :--- | :--- |
| **01** | [Executive Impersonation & Real-Time Financial Fraud](casestudy01.md) | $25M Hong Kong multi-person deepfake video teleconference scam | Real-time facial landmark drift, video stream container jitter | *FaceForensics++* (ICCV 2019)<br>*DFDC* (arXiv:2006.07397)<br>*DeepAgent* (arXiv:2512.07351) |
| **02** | [Social Media Disinformation & Election Integrity](casestudy02.md) | Viral diffusion portraits (Midjourney v6, Stable Diffusion 3, Flux) | Latent diffusion signatures, blur suppression, middle-zone ambiguity | *Corvi et al.* (ICASSP 2023)<br>*Ojha et al.* (CVPR 2023)<br>*Wang et al.* (CVPR 2020) |
| **03** | [Non-Consensual Imagery & Facial Inpainting](casestudy03.md) | Targeted harassment & face-swapping (SimSwap, RoOP, DeepFaceLab) | Facial boundary blending, mask feathering, localized inpainting | *Face X-Ray* (CVPR 2020)<br>*Nirkin et al.* (TPAMI 2021)<br>*Zou et al.* (arXiv:2608.06865) |
| **04** | [Compression Laundering & Adversarial Evasion](casestudy04.md) | Social media re-compression across WhatsApp, Telegram, X, TikTok | High-frequency quantization, spectral decay, signal conflict resolution | *Frank et al.* (ICML 2020)<br>*Durall et al.* (CVPRW 2020)<br>*TruEDebate/TED* (arXiv:2505.08532) |
| **05** | [Provenance, Legal Admissibility & Compliance](casestudy05.md) | EU AI Act (Article 50) & courtroom evidence admissibility (FRE 901/902) | Cryptographic chain-of-custody, C2PA manifests, RFC 7807 problem details | *C2PA Technical Spec v2.0*<br>*NIST SP 800-86*<br>*RFC 7807 Problem Details* |

---

## 🔬 Architectural Summary Across All Scenarios

Across all five case studies, the fundamental failure mode of legacy detection tools is their **monolithic, single-pass design**: they treat deepfake detection as a static scalar prediction task.

**Deepfake Agentic AI** resolves these threats by decoupling detection into an **adaptive multi-signal cognitive pipeline**:

```
                       ┌──────────────────────────────────────────────┐
                       │           Incoming Media Stream              │
                       └──────────────────────┬───────────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │                                               │
                      ▼                                               ▼
     ┌─────────────────────────────────┐             ┌─────────────────────────────────┐
     │      Perceptual ML Service      │             │      Forensic Agent Service     │
     │  • RetinaFace face localization │             │  • Metadata & provenance check  │
     │  • SigLIP Vision Transformer    │             │  • SambaNova Gemma log analyser │
     │  • Laplacian blur quality gate  │             │  • Conflict resolution decider  │
     └────────────────┬────────────────┘             └────────────────┬────────────────┘
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │ Dynamic Reliability Fusion  │
                               │  W_i = r_i / sum(r_j)       │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │  Auditable Legal Verdict    │
                               │  (REAL / FAKE / REVIEW)     │
                               └─────────────────────────────┘
```

1. **Sensory Isolation:** Computer vision workloads (RetinaFace, SigLIP) run in an isolated ML service, avoiding resource starvation and memory contention.
2. **Reliability Weighting:** Every signal carries both a `score` and a runtime `reliability` factor (e.g., scaled by face coverage ratio, compression factor, or blur variance).
3. **Cognitive Deliberation:** Edge cases are not arbitrarily rounded to $0$ or $1$. They trigger deliberative reanalysis (Paths 3a and 3b) and LLM anomaly reasoning.
4. **Verifiable Auditability:** Verdicts are stored alongside the exact weight breakdown, decision path, and MinIO object key, ensuring compliance with international legal standards.

---

## 🛠️ Testing & Reproducing Case Scenarios

To run automated benchmarks against fixtures simulating these case studies:

```bash
# Execute the precision/recall evaluation against the balanced 140k subset
docker compose exec api python /app/tests/eval/evaluate.py
```
