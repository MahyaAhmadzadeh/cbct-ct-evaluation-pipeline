from dataclasses import dataclass, field
from typing import List
import os


@dataclass
class Configs:
    TS_PROSTATE_CLASS: str = "prostate"
    TS_BLADDER_CLASS: str = "urinary_bladder"
    GT_PROSTATE_CLASS: str = "Prostate"
    GT_BLADDER_CLASS: str = "Bladder"
    GT_RECTUM_CLASS: str = "Rectum"
    TS_male_roi_subset: List[str] = field(init=False)
    TS_female_roi_subset: List[str] = field(init=False)
    GT_roi_subset: List[str] = field(init=False)
    patients_with_GT: List = field(default_factory= lambda: ["003", "006", "013", "025", "027", "046", "050", "054", "057", "058"])
    EVAL_DIR = "eval"
    GT_CONTOURS_DIR = "GT_contours"
    CT_DIR = "CT"
    CBCT_DIR = "CBCT"
    LT_CBCT_DIR = os.path.join(EVAL_DIR, "LT_CBCT")
    LT_CBCT_SEG_DIR = os.path.join(EVAL_DIR, "LT_CBCT_seg")
    CT_SEG_DIR = os.path.join(EVAL_DIR, "CT_seg")
    DMAPS_DIR = os.path.join(EVAL_DIR, "dmaps")
    CXTS_DIR = os.path.join(EVAL_DIR, "cxts")
    FCVS_DIR = os.path.join(EVAL_DIR, "fcsvs")
    REGISTER_PARAMS_DIR = os.path.join(EVAL_DIR, "register_params")
    REGISTERED_VOLUMES_DIR = os.path.join(EVAL_DIR, "registered_volumes")
    VF_VOLUMES_DIR = os.path.join(EVAL_DIR, "VFs")
    WARPS_DIR = os.path.join(EVAL_DIR, "warps")
    SCORES_DIR = os.path.join(EVAL_DIR, "scores")

    TS = "TS"
    GT = "GT"
    NOPD = "NOPD"
    GT_BLADDER_ONLY = "GT_bladder_only"
    VF_PREFIX = "VF_"
    WARP_PREFIX = "W_"
    AFFINE_TRANSFORM_FILENAME = "LinearTransform.txt"

    LUT = {
            'patient_number': 'patient_number',
            'Bladder - GT ALL | PD': 'W_GT_Bladder',
            'Prostate - GT ALL | PD': 'W_GT_Prostate',
            'Rectum - GT ALL | PD': 'W_GT_Rectum',
            'Bladder - GT Bladder Only | PD': 'W_GT_bladder_only_Bladder',
            'Prostate - GT Bladder Only | PD': 'W_GT_bladder_only_Prostate',
            'Rectum - GT Bladder Only | PD': 'W_GT_bladder_only_Rectum',
            'Bladder - NOPD': 'W_NOPD_Bladder',
            'Prostate - NOPD': 'W_NOPD_Prostate',
            'Rectum - NOPD': 'W_NOPD_Rectum',
            'Bladder - TS Bladder | PD': 'W_TS_Bladder',
            'Prostate - TS Bladder | PD': 'W_TS_Prostate',
            'Rectum - TS Bladder | PD': 'W_TS_Rectum',
            'urinary_bladder - TS Bladder | PD': 'W_TS_urinary_bladder'
        }

    def __post_init__(self):
        self.TS_male_roi_subset = [self.TS_BLADDER_CLASS]
        self.TS_female_roi_subset = [self.TS_BLADDER_CLASS]
        self.GT_roi_subset = [self.GT_PROSTATE_CLASS, self.GT_BLADDER_CLASS, self.GT_RECTUM_CLASS]