from dataclasses import dataclass, field
from typing import List
import os


@dataclass
class EvaluationConfig:
    # Mahya's Changes for unifiying the pipelines:
    # Change Set 1: where we are going to use the generated images for both totalsegmenator contouring and image intensities
    use_generated_ct_everywhere: bool = False
    # Change Set 2: where we are using the generated iamges only for totalsegmentator contouring, but we use the LT_CBCT directly for image intensities
    use_generated_ct_for_segmentation: bool = False
    # Change Set 3: where we are adding new organs for totalsegmentator to be segmented
    use_extended_ts_organs: bool = False
    crop_colon: bool = True

    # a new variable: patient prefix and which dataset (MGH or PRD)
    VARIANT_TAG: str = "baseline"
    PATIENT_PREFIX: str = "MGH"
    # Extended TS organ
    TS_COLON: str = "colon"
    TS_FEMUR_LEFT: str="femur_left"
    TS_FEMUR_RIGHT: str="femur_right"

    TS_GMAX_LEFT: str = "gluteus_maximus_left"
    TS_GMAX_RIGHT: str = "gluteus_maximus_right"
    TS_GMED_LEFT: str = "gluteus_medius_left"
    TS_GMED_RIGHT: str = "gluteus_medius_right"
    TS_GMIN_LEFT: str = "gluteus_minimus_left"
    TS_GMIN_RIGHT: str = "gluteus_minimus_right"
    PROSTATE: str = "prostate"
    TS_HIP_LEFT: str = "hip_left"
    TS_HIP_RIGHT: str = "hip_right"


    GENERATED_CT_DIR: str = "GENERATED_CT"

    #
    TS_SACRUM: str = "sacrum"
    TS_PROSTATE_CLASS: str = "prostate"
    TS_BLADDER_CLASS: str = "urinary_bladder"
    GT_PROSTATE_CLASS: str = "Prostate"
    GT_BLADDER_CLASS: str = "Bladder"
    GT_RECTUM_CLASS: str = "Rectum"
    TS_male_roi_subset: List[str] = field(init=False)
    TS_female_roi_subset: List[str] = field(init=False)
    GT_roi_subset: List[str] = field(init=False)
    patients_with_GT: List = field(default_factory= lambda: ["001","002", "007", "009", "010", "012", "016", "018", "020","023"])
    CT_DIR = "CT"
    CBCT_DIR = "CBCT"
    GT_CONTOURS_DIR = "GT_contours"
    FDMS_DIR = "FDMs"
    FCVS = "fcsvs"
    SEGMENTS = "seg"
    
    def get_subdir(self, name):
        return os.path.join(self.get_eval_dir(), name)
     
    @property
    def LT_CBCT_DIR(self): return self.get_subdir("LT_CBCT")
    @property
    def LT_CBCT_SEG_DIR(self): return self.get_subdir("LT_CBCT_seg")
    @property
    def CT_SEG_DIR(self): return self.get_subdir("CT_seg")
    @property
    def DMAPS_DIR(self): return self.get_subdir("dmaps")
    @property
    def CXTS_DIR(self): return self.get_subdir("cxts")
    @property
    def FCVS_DIR(self): return self.get_subdir("fcsvs")
    @property
    def REGISTER_PARAMS_DIR(self): return self.get_subdir("register_params")
    @property
    def REGISTERED_VOLUMES_DIR(self): return self.get_subdir("registered_volumes")
    @property
    def VF_VOLUMES_DIR(self): return self.get_subdir("VFs")
    @property
    def WARPS_DIR(self): return self.get_subdir("warps")
    @property
    def SCORES_DIR(self): return self.get_subdir("scores")
        
    TS = "TS"
    GT = "GT"
    NOPD = "NOPD"
    GT_BLADDER_ONLY = "GT_bladder_only"
    GT_BLADDER_RECTUM_ONLY: str = "GT_bladder_rectum_only"
    VF_PREFIX = "VF_"
    WARP_PREFIX = "W_"
    AFFINE_TRANSFORM_FILENAME = "LinearTransform.txt"
    PATIENT_NUM_KEY = "Patient #"
    RESULTS_DIR = os.path.join(os.path.curdir, "results")
    DICE_CSV_FILENAME = "dice.csv"
    HD_CSV_FILENAME = "hd.csv"
    FD_SEP_CSV_FILENAME = "fd-sep.csv"
    LAMBDA = 10000

    # LUT = {
    #     PATIENT_NUM_KEY: PATIENT_NUM_KEY,
    #     'Bladder - GT ALL | PD': 'W_GT_Bladder',
    #     'Prostate - GT ALL | PD': 'W_GT_Prostate',
    #     'Rectum - GT ALL | PD': 'W_GT_Rectum',
    #     'Bladder - GT Bladder Only | PD': 'W_GT_bladder_rectum_only_Bladder',
    #     'Prostate - GT Bladder Only | PD': 'W_GT_bladder_only_Prostate',
    #     'Rectum - GT Bladder Only | PD': 'W_GT_bladder_only_Rectum',
    #     'Bladder - NOPD': 'W_NOPD_Bladder',
    #     'Prostate - NOPD': 'W_NOPD_Prostate',
    #     'Rectum - NOPD': 'W_NOPD_Rectum',
    #     'Bladder - TS ALL | PD': 'W_TS_Bladder',
    #     'Prostate - TS ALL | PD': 'W_TS_Prostate',
    #     'Rectum - TS ALL | PD': 'W_TS_Rectum',
    #     'urinary_bladder - TS ALL | PD': 'W_TS_urinary_bladder',
    #     'Bladder - TS CBCT vs GT CBCT': 'TS_CBCT_GT_CBCT',
    #     'Bladder - TS CT vs GT CT': 'TS_CT_GT_CT',
    # }

    
    def __post_init__(self):
        # self.TS_male_roi_subset = [self.TS_PROSTATE_CLASS]
        self.TS_male_roi_subset = [self.TS_BLADDER_CLASS]
        self.TS_female_roi_subset = [self.TS_BLADDER_CLASS]
        if self.use_extended_ts_organs:
            self.TS_male_roi_subset += [
                self.TS_COLON,
                self.TS_FEMUR_LEFT,
                self.TS_FEMUR_RIGHT,
                self.TS_HIP_LEFT,
                self.TS_HIP_RIGHT
            ]
            #self.TS_SACRUM
            # self.TS_PROSTATE_CLASS
        self.GT_roi_subset = [self.GT_PROSTATE_CLASS, self.GT_BLADDER_CLASS, self.GT_RECTUM_CLASS]
    def get_eval_dir(self):
        return f"eval_{self.VARIANT_TAG}"

    def get_flag_summary(self):
        return (
            f"use_generated_ct_everywhere={self.use_generated_ct_everywhere}, "
            f"use_generated_ct_for_segmentation={self.use_generated_ct_for_segmentation}, "
            f"use_extended_ts_organs={self.use_extended_ts_organs}"
        )
    def __str__(self):
        return f"[{self.VARIANT_TAG}] {self.get_flag_summary()}"
