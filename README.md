# CBCT-to-CT Evaluation Pipeline (Modified from Santhosh)

This is a modified version of the Cycle-GAN CBCT-to-CT Evaluation Pipeline originally developed by Santhosh. The goal is to evaluate registration and segmentation performance on MGH CBCT and CT and generated CT dataset using deformable image registration, segmentation tools (e.g., TotalSegmentator), and various evaluation metrics (Dice, Hausdorff, fiducial distance) for LT-CBCT in MSE and 3 other PD variants (GT-bladder-rectum, GT-All, TS-bladder, TS-extra)​.

---

## Folder Overview

Each patient folder (e.g., `MGH-001`, `MGH-002`, etc.) resides under `./datasets/MGH/` and is processed with multiple evaluation variants. After running the pipeline, you will see subfolders such as:

```
MGH-002/
├── CBCT/                         # Median filtered and affine-transformed CBCT DICOM files
├── CT/                           # Original CT DICOM files
├── GT_contours/                  # Ground-truth segmentations
│   ├── CBCT/                     # Ground truth on CBCT in .mha format (affine-transformed)
│   └── CT/                       # Ground truth on CT in .mha format
├── GENERATED_CT/                 # Generated synthetic CT (e.g., via CycleGAN, in .nrrd format)
├── eval_baseline/                # Evaluation results for baseline variant (vanilla TS + PD)
│   ├── CT_seg/                   # Cropped TotalSegmentator segmentations on CT
│   ├── LT_CBCT/                  # Linear-transformed CBCT volume folder
│   ├── LT_CBCT_seg/              # Cropped TotalSegmentator segmentations on LT_CBCT
│   ├── cxts/                     # Converted contours in .cxt format (CBCT/CT)
│   ├── dmaps/                    # Distance maps from contours for CBCT
│   ├── fcsvs/                    # .fcsv files for CT
│   ├── register_params/          # Parameter text files for registration
│   ├── registered_volumes/       # Registered CBCT volumes into CT space
│   ├── uncropped_cxts/           # Full-size (uncropped) .cxt contours
│   ├── uncropped_dmaps/          # Full-size distance maps for CBCT
│   ├── uncropped_fcsvs/          # Full-size .fcsv files for CT
│   ├── uncrp_CT_segments/        # Full-size TotalSegmentator segmentation on CT
│   ├── uncrp_LT_CBCT_segments/   # Full-size TotalSegmentator segmentation on LT_CBCT
│   ├── VFs/                      # Deformation vector fields from registration
│   ├── warps/                    # Warped CBCT segmentations into CT space
│   └── LT_CBCT.nrrd              # Affine-transformed CBCT volume as single .nrrd file
├── eval_extorgans/              # Variant using extended organ set for registration
├── eval_genctseg/               # Variant using synthetic CT (GEN_CT) for segmentation
├── eval_genctseg_extorgans/     # Synthetic CT segmentation + extended organs for registration
├── eval_genctall/               # Uses generated CT for both segmentation and registration (MSE + PD)
├── eval_genctall_extorgans/     # Same as above but with extended organ set
├── 002-LinearTransform.txt      # Affine transform file from 3D Slicer
```




---
## Where to Find Segmentations

| **Data Type**                     | **Location (example for MGH-002)**                                           | **Format** |
|-----------------------------------|-------------------------------------------------------------------------------|------------|
| Ground Truth CT                   | `MGH-002/GT_contours/CT/`                                                     | `.mha`     |
| Ground Truth CBCT                 | `MGH-002/GT_contours/CBCT/`                                                   | `.mha`     |
| TotalSegmentator (Uncropped CT)   | `MGH-002/eval_baseline/uncrp_CT_segments/`                                    | `.nrrd`    |
| TotalSegmentator (Uncropped CBCT) | `MGH-002/eval_baseline/uncrp_LT_CBCT_segments/`                               | `.nrrd`    |
| TotalSegmentator (Cropped CT)     | `MGH-002/eval_baseline/CT_seg/`                                               | `.nrrd`    |
| TotalSegmentator (Cropped CBCT)   | `MGH-002/eval_baseline/LT_CBCT_seg/`                                          | `.nrrd`    |
| Warped CBCT Segmentations         | `MGH-002/eval_baseline/warps/seg`                                             | `.mha`     |
| Dice Scores (CBCT→CT)             | `results/merged_all/structure_tables_extorgans/Prostate_dice_table.csv`       | `.csv`     |



### Notes:
- **Cropped** CT segmentations are aligned to the CBCT segmentations field of view for faster registration and clearer boundary refinement.
- **Uncropped** segmentations retain the volume field and can be used for comparison.
- Warped segmentations are the result of deformable registration (e.g., CBCT → CT space).
- Dice score tables summarize the overlap accuracy between warped and ground truth segmentations.
---


## Running the Pipeline



1. **Activate your environment**
   ```bash
   conda activate pipeline
   ```
2. **Run for a single or multiple patients**
   ```bash
   # Force re-run all steps for patients 002 and 003 for baseline variant
   python main.py -d ./datasets/MGH/MGH* -v baseline -n 002,003 -a -f
   
   # Force re-run all steps for patients 002 and 003 for all variants
   python main.py -d ./datasets/MGH/MGH* -n 002,003 -a -f

   # Only run segmentation and registration for all patients (skip if already done)
   python main.py -d ./datasets/MGH/MGH* -s -r
   ```
---

## Available Variants

The pipeline supports multiple evaluation variants, controlled via folder names or internal arguments:

- `baseline`: GT All + NOPD + GT_Bladder_Rectum_only, TS_Bladder_Only
- `extorgans`: TS_Extra_Organs
- `genctseg`: baseline but with generated CT in only TS segmentation
- `genctseg_extorgans`: Same as above with extended organs
- `genctall`: Segmentation + registration using generated CT
- `genctall_extorgans`: Same as above with extended organs

---


## Metrics

After the pipeline runs, you'll find:

- **Dice Score Tables**: CSVs summarizing segmentation overlap per structure
- **Fiducial Distance**: Euclidean distances between landmark points (if available)
- **Hausdorff Distance**: Surface similarity (if enabled in evaluation)

---

## Dependencies

- [Plastimatch](https://plastimatch.org/)
- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
- [3D Slicer](https://www.slicer.org/)

---

Feel free to raise issues or contribute improvements to this fork.
