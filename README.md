## Cycle-GAN CBCT-CT Evaluation Pipeline
Evaluation pipleline for the CBCT to CT domain transfer using Cycle-GAN project. Uses Plastimatch to do all the necessary functions and finally calculates the Dice Similaruty Score, Hausdorff Distance and the Euclidean distance of the fiducial markers. This project utilizes [Plastimatch](https://plastimatch.org/), [TotalSegmentor](https://github.com/wasserth/TotalSegmentator), [3D Slicer](https://www.slicer.org/).

## Folder Structure
```text
project/
├── datasets/
│   └── pelvic_reference/
│       ├── Pelvic-Ref-001/              # Patient with GT contours
│       │   ├── CBCT/                    # Contains the CBCT DICOM files
│       │   ├── CT/                      # Contains the CT DICOM files
│       │   ├── FDMs/                    # Contains the Fiducial Distance Markup files (if available)
│       │   ├── GT_contours/             # Contains ground truth contours
│       │   │   ├── CT/                  # CT contours in .mha format
│       │   │   └── CBCT/                # CBCT contours in .mha format
│       │   └── 001-LinearTransform.txt  # Affine transform values from 3D Slicer
│       ├── Pelvic-Ref-002/              # Patient without GT contours
│       │   ├── CBCT/
│       │   ├── CT/
│       │   └── 002-LinearTransform.txt
│       └── ... (additional patient data folders)
├── evaluation/
│   ├── __init__.py
│   ├── config.py
│   ├── fcsv.py
│   ├── params.py
│   ├── pipeline.py
│   ├── plastimatch.py
│   └── util.py
├── main.py
├── requirements.txt
└── README.md
```
## Steps to Run the Code
1. Create a new environment
   ```bash
   conda create --name eval-pipeline python=3.10
   conda activate eval-pipeline
   ```
2. Install the dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Run the pipeline in terminal (-d argument should be in glob format)
   ```bash
   python main.py -d ./datasets/pelvic_reference/Pel*
   ```
4. Run the pipeline from code
   ```python
   from evaluation.pipeline import EvaluationPipeline
   from glob import glob
   import os

   data = glob(os.path.join(os.path.curdir, "datasets", "pelvic_reference", "Pel*"))
   pipeline = EvaluationPipeline()
   pipeline.evaluate(data)
   ```
## Evaluation Pipeline Arguments
1. For Terminal
  ```text
usage: main.py [-h] [-d] [-n] [-f] [-a] [-s] [-pw] [-dm] [-c] [-fc] [-p] [-r] [-w] [-m] [-fs]

options:
  -h, --help            show this help message and exit
  -d, --data            all patient dirs in glob format
  -n, --nums            patient numbers to process (in csv format)
  -f, --force           force run, deletes previous results and creates a new one. Otherwise skips the step if results already present
  -a, --all             run all the steps
  -s, --seg             run segmentation only
  -pw, --pw-linear      run pw-linear transformation only
  -dm, --dmap           run dmap calculation only
  -c, --cxt             run cxt conversion only
  -fc, --fcsv           run fcsv creation only
  -p, --params          run register params.txt creation only
  -r, --register        run plastimatch register only
  -w, --warp            run warp only
  -m, --metric          run calculate scores only
  -fs, --fiducial-sep   run calculate fiducial distance only
```
Example:
```bash
  1. python main.py -d ./datasets/pelvic_reference/Pel* -f -n 3,4 -a        # Force runs all the steps for patients 3 and 4
  2. python main.py -d ./datasets/pelvic_reference/Pel* -f -n 3,4 -s -pw    # Force runs the segmentation and pw-linear transform steps for patients 3 and 4
  3. python main.py -d ./datasets/pelvic_reference/Pel* -f -s -pw           # Force runs the segmentation and pw-linear transform steps for all the patients
  3. python main.py -d ./datasets/pelvic_reference/Pel* -s -pw              # Initates the segmentation and pw-linear transform steps for all the patients, but skips if the result is already present
  ```
2. For Python
   ```python
   nums = [] or [3, 4]   # Runs for all the patients if [] is passed
   force = False
   all = True            # Runs all the steps if True
   seg = False
   pw_linear = False
   dmap = False
   cxt = False
   fcsv = False
   params = False
   register = False
   warp = False
   metric = False
   fiducial_sep = False
   data = glob(os.path.join(os.path.curdir, "datasets", "pelvic_reference", "Pel*"))
   
   pipeline = EvaluationPipeline()
   pipeline.evaluate(data, force, nums, all, seg, pw_linear,
                        dmap, cxt, fcsv, params, register,
                        warp, metric, fiducial_sep)
   ```

## References
1. [Plastimatch](https://plastimatch.org/)
2. [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)

---
