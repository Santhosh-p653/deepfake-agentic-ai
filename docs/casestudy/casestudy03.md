# 🔬 Case Study 03: Non-Consensual Imagery & Facial Inpainting

**Focus Area:** Non-Consensual Synthetic Media, Face-Swapping, and Boundary Inpainting  
**Forensic Category:** Boundary Discontinuity, Mask Feathering, and Localized Manipulation  
**Real-World Scenario:** Defamation & Targeted Harassment of Public Figures and Private Citizens (RoOP / DeepFaceLab / SimSwap)

---

## 1. Threat Scenario & Context

Non-consensual deepfake imagery—predominantly targeting women, journalists, and public figures—represents the largest single category of malicious synthetic media on the internet today. Using open-source face-swapping packages (e.g., DeepFaceLab, SimSwap, RoOP, FaceFusion), bad actors splice the target's face onto a donor body with high photorealism.

In these attacks, the manipulation is **spatially localized**: only the facial oval or facial landmarks are synthesized, while the remainder of the image (hair, background, torso) remains authentic. Because the surrounding context is genuine, global image classifiers that evaluate the whole image frequently miss the localized swap, resulting in disastrous false negatives.

---

## 2. Research Grounding & Academic Sources

Academic research confirms that localized facial replacement creates distinct boundary and contextual inconsistencies:

1. **Face X-Ray for More General Face Forgery Detection**  
   *Lingzhi Li, Jianmin Bao, Ting Zhang, Hao Yang, Dong Chen, Fang Wen, Baining Guo* (IEEE/CVF CVPR 2020)  
   *Finding:* Almost all face-swapping pipelines involve three steps: face synthesis, color correction, and boundary blending. The blending step invariably introduces subtle structural discontinuities (the "Face X-Ray") where image noise, color gradients, and pixel statistics from the donor face fail to match the background frame.  
   *DOI:* [10.1109/CVPR42600.2020.00281](https://doi.org/10.1109/CVPR42600.2020.00281)

2. **DeepFake Detection Based on Discrepancies Between Faces and their Context**  
   *Yuval Nirkin, Iacopo Masi, Anh Tuan Tran, Tal Hassner, Gerard Medioni* (IEEE TPAMI 2021)  
   *Finding:* State-of-the-art face swappers successfully mimic inner facial landmarks (eyes, nose, mouth) but struggle with outer boundary coherence, leading to statistical discrepancies between facial skin and surrounding neck/hair regions.  
   *DOI:* [10.1109/TPAMI.2021.3061484](https://doi.org/10.1109/TPAMI.2021.3061484)

3. **Multi-Agent Forensic Reasoning for Generalizable Deepfake Video Detection**  
   *Xuechao Zou et al.* (arXiv:2608.06865, Aug 2026)  
   *Finding:* Localized forgeries require specialized spatial reasoning agents focused on mask borders rather than monolithic whole-frame inference.

---

## 3. Why Traditional Single-Pass Detectors Fail

* **Whole-Frame Averaging:** Monolithic CNN classifiers pool feature activations across the entire image. When an authentic background occupies $80\%$ of the image pixels, authentic signals drown out the $20\%$ manipulated facial region.
* **Small Face Invisibility:** If the target is standing several meters from the camera, standard detectors fail to locate or properly crop the face, defaulting to an erroneous "Real" verdict.
* **Lighting and Skin-Tone Normalization:** Modern face-swappers use Poisson image editing to smooth color transitions, defeating basic histogram and color-difference checks.

---

## 4. How Deepfake Agentic AI Addresses This Threat

The **Deepfake Agentic AI** platform isolates and evaluates localized facial forgeries through **RetinaFace Crop Extraction & Dynamic Coverage Weighting**:

```
Input Image / Video
   │
   ├── [RetinaFace] ────────► PyTorch RetinaNetMobileNetV1 detects facial bounding boxes
   │                           └── Rejects background noise; extracts tight facial crops
   │
   ├── [Per-Crop SigLIP] ───► Independent scoring of each detected face
   │                           └── Evaluates facial boundaries, eye reflections, skin pores
   │
   ├── [Reliability Scaling] ► Reliability r_det = min(1.0, Face Area / Frame Area * 4)
   │                           └── Prevents tiny false crops from distorting final verdict
   │
   ├── [Source Verifier] ───► Inspects EXIF tags for face-swap tool metadata signatures
   │
   └── [Adaptive Decider] ──► Path 1 Enforcement: Aggregated Score ≥ 0.70 → FAKE
```

### Technical Workflow & Code Mapping

1. **Face Isolation via RetinaFace:**
   In [ml/detection.py](file:///home/santhosh/deepfake-agentic-ai/ml/detection.py), the `_detect_faces()` method runs RetinaFace (PyTorch) with confidence threshold $0.5$ and NMS IoU threshold $0.3$:
   ```python
   # Extract cropped face arrays, ignoring non-facial background
   detections = detector.detect(frame_rgb)
   for x1, y1, x2, y2, score in detections:
       crop = frame_uint8[y1:y2, x1:x2]
       crops.append(crop)
   ```
   This ensures that SigLIP evaluates *only the localized facial pixels*, eliminating background interference.

2. **Per-Face Scorer:**
   In `_score_faces()`, each face crop is normalized and passed through `SiglipForImageClassification`. The model assesses the probability that the face was synthesized:
   ```python
   probs = torch.nn.functional.softmax(outputs.logits, dim=1)
   fake_prob = probs[0][0].item() # index 0 = "fake"
   ```

3. **Dynamic Coverage-Based Reliability:**
   If multiple faces exist, the highest-confidence forgery is weighted by its coverage. If a face occupies a prominent region of the frame, its signal reliability increases to near $1.0$, preventing dilution by unmanipulated peripheral bodies.

4. **Forensic Record Preservation:**
   When detected, the verdict (`FAKE`) and full signal breakdown (`{ml.detection: 0.94, preprocessing: 0.82}`) are persisted in PostgreSQL, creating an auditable forensic record suitable for victim legal defense.
