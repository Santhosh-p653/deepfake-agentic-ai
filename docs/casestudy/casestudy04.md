# 🔬 Case Study 04: Compression Laundering & Adversarial Evasion

**Focus Area:** Media Laundering via Social Media Platforms (WhatsApp, Telegram, X, TikTok)  
**Forensic Category:** High-Frequency Quantization & Lossy Re-Compression Artifacts  
**Real-World Scenario:** Adversarial Stripping of Forensic Clues through Multi-Generation Compression

---

## 1. Threat Scenario & Context

When sophisticated state-sponsored or cybercriminal actors disseminate synthetic media, they rarely publish the raw uncompressed output directly. Instead, they execute **media laundering**: the synthetic image or video is repeatedly forwarded, re-uploaded, screenshotted, and re-encoded across platforms such as WhatsApp, X (formerly Twitter), Telegram, and TikTok.

Each transfer applies aggressive lossy compression codecs (JPEG quantization, H.264/AVC, H.265/HEVC, WebP downsampling). This lossy pipeline acts as an accidental or intentional low-pass filter: it removes high-frequency spatial residuals, blurs fine facial landmarks, and alters color quantization tables. Traditional deepfake detectors trained on pristine academic datasets (such as FaceForensics++ raw or Celeb-DF) fail catastrophically when applied to laundered social media uploads.

---

## 2. Research Grounding & Academic Sources

Forensic literature has extensively documented how compression destroys standard algorithmic indicators:

1. **Leveraging Frequency Analysis for DeepFake Detection**  
   *Joel Frank, Thorsten Eisenhofer, Lea Schönherr, Asja Fischer, Dorothea Kolossa, Thorsten Holz* (PMLR ICML 2020)  
   *Finding:* In the spatial frequency domain (via Discrete Cosine Transform or 2D-FFT), generative models exhibit severe spectral decay and periodic grid spikes. However, aggressive social media compression (JPEG quality factor $Q < 60$) suppresses these high-frequency bands, causing pure frequency-domain detectors to suffer high false-negative rates.  
   *Paper:* [arXiv:2003.08685](https://arxiv.org/abs/2003.08685)

2. **Unmasking DeepFakes with Simple Features**  
   *Ricard Durall, Margret Keuper, Janis Keuper* (IEEE/CVF CVPRW 2020)  
   *Finding:* Visual artifact detectors that do not account for degradation factors fail to differentiate between genuine sensor compression and synthetic generation artifacts, causing rampant false positive spikes on poor-quality legitimate images.  
   *DOI:* [10.1109/CVPRW50498.2020.00331](https://doi.org/10.1109/CVPRW50498.2020.00331)

3. **The Truth Becomes Clearer Through Debate! Multi-Agent Systems with Large Language Models Unmask Fake News (TruEDebate / TED)**  
   *Yuhan Liu et al.* (arXiv:2505.08532, May 2025)  
   *Finding:* When sensory inputs are noisy or degraded by compression, multi-agent cross-examination between specialized agents (visual, contextual, and metadata agents) resolves perceptual ambiguities that confuse single end-to-end models.

---

## 3. Why Traditional Single-Pass Detectors Fail

* **Domain Generalization Collapse:** Detectors overfit to the high-resolution, uncompressed artifacts of their training set. On degraded media, they either label all compressed images as fake (high false alarm) or miss forgeries completely (high miss rate).
* **Static Weighting Assumptions:** Standard ensembles average model predictions with fixed weights (e.g., $50\%$ CNN $+ 50\%$ ViT). If compression blinds the CNN, the fixed ensemble still grants it equal authority, poisoning the verdict.
* **Inability to Diagnose Blur vs. Forgery:** Single-pass models cannot distinguish whether an eye is blurry because it was synthesized by an imperfect diffusion model or because WhatsApp downscaled it to $640\times 480$ resolution.

---

## 4. How Deepfake Agentic AI Addresses This Threat

The **Deepfake Agentic AI** platform survives social media compression laundering through **Preprocessing Quality Gating & Dynamic Reliability Weighting**:

```
Compressed Social Media Upload
   │
   ├── [ml.preprocessing] ───► Evaluates Laplacian Blur Variance & Compression Artifacts
   │                           └── Lowers reliability r_prep if image is heavily quantized
   │
   ├── [ml.detection] ───────► SigLIP ViT evaluates remaining semantic/spatial clues
   │                           └── Generates Score & Reliability (r_det)
   │
   ├── [source_verifier] ────► Pure Python Metadata Forensics
   │                           └── Inspects EXIF quantization tables & compression history
   │
   ├── [Adaptive Aggregator] ► Normalizes Weights at Runtime:
   │                           └── W_i = r_i / sum(r_j) (De-weights degraded signals)
   │
   └── [Decider Path 3b] ────► If 70/30 module conflict arises:
                               └── Reanalyses with targeted weights on conflicting modules
```

### Technical Workflow & Code Mapping

1. **Empirical Sharpness & Compression Metrics:**
   In [ml/preprocessing.py](file:///home/santhosh/deepfake-agentic-ai/ml/preprocessing.py), the image is evaluated before passing to the heavy neural network:
   ```python
   # Laplacian variance measures edge sharpness and high-frequency energy
   gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
   is_blurry = laplacian_var < BLUR_THRESHOLD
   ```
   If $laplacian\_var$ is extremely low due to aggressive compression, the module emits a degraded reliability score, alerting the downstream aggregator.

2. **Dynamic Reliability Weighting:**
   In [agents/aggregator.py](file:///home/santhosh/deepfake-agentic-ai/agents/aggregator.py), weights are never static. They are computed from empirical reliability at runtime:
   $$w_i = \frac{r_i}{\sum_{j} r_j}$$
   If compression reduces the ML detection reliability from $0.90$ to $0.35$, the aggregator automatically dampens the ML module's influence, preventing noisy predictions from causing false alarms.

3. **Path 3b Conflict Re-analysis:**
   In [agents/decider.py](file:///home/santhosh/deepfake-agentic-ai/agents/decider.py), if one module predicts Real ($0.20$) while another predicts Fake ($0.80$) due to compression noise, the system triggers **Path 3b** targeted conflict reanalysis, logging the variance and isolating the discrepant source.
