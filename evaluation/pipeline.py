from glob import glob
from typing import List
from uuid import uuid4
import shutil
from evaluation.evaluator import Evaluator
import sys
from contextlib import redirect_stdout, redirect_stderr
from evaluation.params import create_params_txt
from totalsegmentator.python_api import totalsegmentator
import os
import re

from evaluation.fcsv import create_fcsv
from evaluation.plastimatch import Plastimatch
from evaluation.config import EvaluationConfig
from evaluation.utils import Utils
import pandas as pd
import numpy as np
from datetime import datetime

class EvaluationPipeline:
    def __init__(self, configs: EvaluationConfig) -> None:
        self.configs: EvaluationConfig = configs

        self.merged_dice = [] 
        self.merged_hd = []
        self.merged_fd = []

        self.FD_SEP_df = {
            self.configs.PATIENT_NUM_KEY: [],
            self.configs.GT: [],
            self.configs.GT_BLADDER_RECTUM_ONLY: [],
            self.configs.NOPD: [],
            self.configs.TS: []
        }

        self._plastimatch = Plastimatch()
        self._utils = Utils(self.configs)


    def pw_linear_transformation(self, patient_dir, force):
        ltcbct_path = os.path.join(patient_dir, self.configs.LT_CBCT_DIR)
        is_skip = self._utils.replace_or_skip(ltcbct_path, force)
     
        if is_skip:
            return
     
        if self.configs.use_generated_ct_everywhere:
            generated_dicom_folder = os.path.join(patient_dir, "GENERATED_CT")
            generated_nrrd_path = os.path.join(patient_dir, "GENERATED_CT.nrrd")
     
            if not os.path.exists(generated_nrrd_path):
                print(f"[INFO] Converting GENERATED_CT DICOM to NRRD: {generated_nrrd_path}")
                self._plastimatch.convert("input", generated_dicom_folder, "output-img", generated_nrrd_path)
     
            cbct_path = generated_nrrd_path
        else:
            cbct_path = os.path.join(patient_dir, self.configs.CBCT_DIR)
     
        self._plastimatch.pw_linear_transform(
            cbct_path,
            ltcbct_path,
            use_identity=self.configs.use_generated_ct_everywhere
        )
     
        nrrd_file = f"{ltcbct_path}.nrrd"
        if not os.path.exists(nrrd_file):
            raise FileNotFoundError(f"Error: {nrrd_file} not created after pw-linear transform.")
     
        self._plastimatch.convert("input", nrrd_file, "output-dicom", ltcbct_path)
    
    def segmentation(self, input_path, output_seg_path, force, roi_subset=None):
        is_skip = self._utils.replace_or_skip(output_seg_path, force)
        if is_skip:
            return
    
        if roi_subset is None:
            _, roi_subset = self._utils.get_roi_subset(input_path)
    
        totalsegmentator(input_path, output=output_seg_path, roi_subset=roi_subset)
        
        for nifti_file_path in glob(f"{output_seg_path}/*"):
            self._utils.convert_nifti_to_nrrd(nifti_file_path)

    def dmap_calcualtion(self, patient_dir, force):
        dmaps_dir = os.path.join(patient_dir, self.configs.DMAPS_DIR)
        is_skip = self._utils.replace_or_skip(dmaps_dir, force)
        if is_skip:
            return
        ltcbct_seg_path = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR)
        cbct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CBCT_DIR)
        input_paths = glob(f"{ltcbct_seg_path}/*") + glob(f"{cbct_gt_contours_path}/*")
        for input_path in input_paths:
            class_name = self._utils.get_class_name(input_path)
            if class_name:
                output_path = os.path.join(dmaps_dir, f"{class_name}.mha")
                self._plastimatch.dmap(input_path, output_path)

    def cxt_conversion(self, patient_dir, force):
        cxts_dir = os.path.join(patient_dir, self.configs.CXTS_DIR)
        is_skip = self._utils.replace_or_skip(cxts_dir, force)
        if is_skip:
            return
        
        ct_seg_path = os.path.join(patient_dir, self.configs.CT_SEG_DIR)
        ct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR)
        input_paths = glob(f"{ct_seg_path}/*") + glob(f"{ct_gt_contours_path}/*")
        for input_path in input_paths:
            class_name = self._utils.get_class_name(input_path)
            if class_name:
                output_path = os.path.join(cxts_dir, f"{class_name}.cxt")
                self._plastimatch.convert("input-ss-img", input_path, "output-cxt", output_path)

    def create_fcsvfile(self, patient_dir, force):
        fcsvs_dir = os.path.join(patient_dir, self.configs.FCVS_DIR)
        is_skip = self._utils.replace_or_skip(fcsvs_dir, force)
        if is_skip:
            return
        
        cxts_dir = os.path.join(patient_dir, self.configs.CXTS_DIR)
        for cxt_filepath in glob(f"{cxts_dir}/*"):
            class_name = self._utils.get_class_name(cxt_filepath)
            fcsv_filepath = os.path.join(fcsvs_dir, f"{class_name}.fcsv")
            csv_filepath = os.path.join(fcsvs_dir, f"{class_name}.csv")
            create_fcsv(cxt_filepath, fcsv_filepath, csv_filepath)

    def create_register_params(self, patient_dir, force):
        # Flags to keep track of the register params file created
        NOPD, TS, GT_bladder_rectum_only, GT = False, False, False, False
    
        reg_params_dir = os.path.join(patient_dir, self.configs.REGISTER_PARAMS_DIR)
        if force and os.path.exists(reg_params_dir):
            shutil.rmtree(reg_params_dir)
        os.makedirs(reg_params_dir, exist_ok=True)
    
        patient_number, TS_roi_subset = self._utils.get_roi_subset(patient_dir)
        print(f"[DEBUG] patient_number: {patient_number}")
        print(f"[DEBUG] patients_with_GT: {self.configs.patients_with_GT}")
    
        # Exclude femurs from registration (they're only used for colon cropping)
        TS_roi_subset_filtered = TS_roi_subset
        print(f"[DEBUG] Final TS_roi_subset_filtered for registration: {TS_roi_subset_filtered}")
    
        # Create NOPD params
        NOPD = create_params_txt(patient_dir, self.configs.NOPD, self.configs)
        print(f"[DEBUG] NOPD param created: {NOPD}")
    
        # Create TS params (conditionally includes colon if extended organs are enabled)
        segments = []
        for r in TS_roi_subset_filtered:
            name = f"TS_{r}"
            segments.append({
                "fixed_file": os.path.join(patient_dir, self.configs.FCVS_DIR, f"{name}.fcsv"),
                "moving_file": os.path.join(patient_dir, self.configs.DMAPS_DIR, f"{name}.mha")
            })
        TS = create_params_txt(patient_dir, self.configs.TS, self.configs, segments)
        print(f"[DEBUG] TS param created: {TS}")
    
        # Create GT-based params (bladder-only and all)
        ct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR)
        print(f"[DEBUG] CT_GT folder exists: {os.path.exists(ct_gt_contours_path)}")
        
        if (str(patient_number) in self.configs.patients_with_GT) and os.path.exists(ct_gt_contours_path):
            # GT Bladder and Rectum Only
            segments = []
            for class_name in [self.configs.GT_BLADDER_CLASS, self.configs.GT_RECTUM_CLASS]:
                name = self._utils.get_class_name(class_name)
                segments.append({
                    "fixed_file": os.path.join(patient_dir, self.configs.FCVS_DIR, f"{name}.fcsv"),
                    "moving_file": os.path.join(patient_dir, self.configs.DMAPS_DIR, f"{name}.mha")
                })
            GT_bladder_rectum_only = create_params_txt(patient_dir, self.configs.GT_BLADDER_RECTUM_ONLY, self.configs, segments)
            print(f"[DEBUG] GT_bladder_rectum_only param created: {GT_bladder_rectum_only}")
    
            # GT All
            segments = []
            for class_name in self.configs.GT_roi_subset:
                name = self._utils.get_class_name(class_name)
                segments.append({
                    "fixed_file": os.path.join(patient_dir, self.configs.FCVS_DIR, f"{name}.fcsv"),
                    "moving_file": os.path.join(patient_dir, self.configs.DMAPS_DIR, f"{name}.mha")
                })
            GT = create_params_txt(patient_dir, self.configs.GT, self.configs, segments)
            print(f"[DEBUG] GT param created: {GT}")
        else:
            print(f"[WARNING] Skipping GT param creation for patient {patient_number}.")
    
        return (NOPD, TS, GT_bladder_rectum_only, GT)


    def start_registration(self, patient_dir, flags, force):
        
        reg_vol_dir = os.path.join(patient_dir, self.configs.REGISTERED_VOLUMES_DIR)
        is_skip = self._utils.replace_or_skip(reg_vol_dir, force)
        if is_skip:
            return

        NOPD, TS, GT_bladder_rectum_only, GT = flags
        params_dir = os.path.join(patient_dir, self.configs.REGISTER_PARAMS_DIR)

        if NOPD:
            params_txt = os.path.join(params_dir, f"{self.configs.NOPD}.txt")
            self._plastimatch.register(params_txt)
        else:
            print("NOPD Params file not created")

        if TS:
            params_txt = os.path.join(params_dir, f"{self.configs.TS}.txt")
            self._plastimatch.register(params_txt)
        else:
            print("TS Params file not created")
        
        if GT_bladder_rectum_only:
            params_txt = os.path.join(params_dir, f"{self.configs.GT_BLADDER_RECTUM_ONLY}.txt")
            self._plastimatch.register(params_txt)
        else:
            print("GT Bladder Only Params file not created")

        if GT:
            params_txt = os.path.join(params_dir, f"{self.configs.GT}.txt")
            self._plastimatch.register(params_txt)
        else:
            print("GT Params file not created")

    def start_warp(self, patient_dir, force):
        warps_dir = os.path.join(patient_dir, self.configs.WARPS_DIR)
        is_skip = self._utils.replace_or_skip(warps_dir, force)
        if is_skip: return

        warps_seg_dir = os.path.join(warps_dir, self.configs.SEGMENTS)
        patient_number, TS_roi_subset = self._utils.get_roi_subset(patient_dir)
        input_dir = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CBCT_DIR)
        vf_dir = os.path.join(patient_dir, self.configs.VF_VOLUMES_DIR)
        ct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR)

        if (str(patient_number) in self.configs.patients_with_GT) and (os.path.exists(ct_gt_contours_path)):

            for segment in self.configs.GT_roi_subset:
                input = os.path.join(input_dir, f"{segment}.mha")
                # Warping the segment with VF_GT.nrrd
                output = os.path.join(warps_seg_dir, f"{self.configs.WARP_PREFIX}{self.configs.GT}_{segment}.mha")
                vf = os.path.join(vf_dir, f"{self.configs.VF_PREFIX}{self.configs.GT}.nrrd")
                self._plastimatch.warp(input, "output-img", output, vf)
                
                # Warping the segment with VF_NOPD.nrrd
                output = os.path.join(warps_seg_dir, f"{self.configs.WARP_PREFIX}{self.configs.NOPD}_{segment}.mha")
                vf = os.path.join(vf_dir, f"{self.configs.VF_PREFIX}{self.configs.NOPD}.nrrd")
                self._plastimatch.warp(input, "output-img", output, vf)
                
                # Warping the segment with VF_GT_bladder_only.nrrd
                output = os.path.join(warps_seg_dir, f"{self.configs.WARP_PREFIX}{self.configs.GT_BLADDER_RECTUM_ONLY}_{segment}.mha")
                vf = os.path.join(vf_dir, f"{self.configs.VF_PREFIX}{self.configs.GT_BLADDER_RECTUM_ONLY}.nrrd")
                self._plastimatch.warp(input, "output-img", output, vf)
                
                try:
                    # Warping the segment with VF_TS.nrrd
                    output = os.path.join(warps_seg_dir, f"{self.configs.WARP_PREFIX}{self.configs.TS}_{segment}.mha")
                    vf = os.path.join(vf_dir, f"{self.configs.VF_PREFIX}{self.configs.TS}.nrrd")
                    self._plastimatch.warp(input, "output-img", output, vf)
                except Exception as e:
                    print(e)

            
            # Warping for fiducial markers
            filename = f"{patient_number}-{self.configs.CBCT_DIR}-fdm.fcsv"
            input = os.path.join(patient_dir, self.configs.FDMS_DIR, filename)
            for vf in glob(f"{vf_dir}/*"):
                output = os.path.basename(vf).removeprefix(self.configs.VF_PREFIX).removesuffix('.nrrd')
                output = os.path.join(warps_dir, self.configs.FCVS, f"{self.configs.WARP_PREFIX}{output}_{filename}")
                self._plastimatch.warp(input, "output-pointset", output, vf)

        try:
            for segment in TS_roi_subset:
                # Warping the segment with VF_TS.nrrd
                input = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{segment}.nrrd")
                output = os.path.join(warps_seg_dir, f"{self.configs.WARP_PREFIX}{self.configs.TS}_{segment}.mha")
                vf = os.path.join(vf_dir, f"{self.configs.VF_PREFIX}{self.configs.TS}.nrrd")
                self._plastimatch.warp(input, "output-img", output, vf)
        except Exception as e:
            print(e)


    # def calculate_fiducial_sep(self, patient_dir):
    #     ct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR)
    #     patient_num = self._utils.get_patient_number(patient_dir)
    #     self.FD_SEP_df[self.configs.PATIENT_NUM_KEY].append(patient_num)
    
    #     if (str(patient_num) in self.configs.patients_with_GT) and (os.path.exists(ct_gt_contours_path)):
    #         ct_fdm = os.path.join(patient_dir, self.configs.FDMS_DIR, f"{patient_num}-{self.configs.CT_DIR}-fdm.fcsv")
    #         try:
    #             ct_coord = self._utils.get_coordinates(ct_fdm)
    #             w_fcsvs_dir = os.path.join(patient_dir, self.configs.WARPS_DIR, self.configs.FCVS)
    #             for key in self.FD_SEP_df:
    #                 if key != self.configs.PATIENT_NUM_KEY:
    #                     w_cbct_fcsv = os.path.join(w_fcsvs_dir, f"{self.configs.WARP_PREFIX}{key}_{patient_num}-{self.configs.CBCT_DIR}-fdm.fcsv")
    #                     if os.path.exists(w_cbct_fcsv):
    #                         w_cbct_coord = self._utils.get_coordinates(w_cbct_fcsv)
    #                         mu_sep = np.sqrt(np.sum(np.square(w_cbct_coord - ct_coord), 1)).mean()  # Euclidean distance
    #                         tag = os.path.basename(w_cbct_fcsv).removeprefix(self.configs.WARP_PREFIX).removesuffix(f"_{patient_num}-{self.configs.CBCT_DIR}-fdm.fcsv")
    #                         self.FD_SEP_df[tag].append(mu_sep)
    #                     else:
    #                         self.FD_SEP_df[key].append("inf")
    #         except Exception as e:
    #             print(f"Error calculating fiducial separation for patient {patient_num}: {e}")
    #             for key in self.FD_SEP_df.keys():
    #                 if key != self.configs.PATIENT_NUM_KEY:
    #                     self.FD_SEP_df[key].append("inf")
    #     else:
    #         print(f"Patient-{patient_num} does not have fiducials")
    #         for key in self.FD_SEP_df.keys():
    #             if key != self.configs.PATIENT_NUM_KEY:
    #                 self.FD_SEP_df[key].append("inf")
    
    #     # Final padding to ensure all columns are same length
    #     max_len = len(self.FD_SEP_df[self.configs.PATIENT_NUM_KEY])
    #     for key in self.FD_SEP_df:
    #         while len(self.FD_SEP_df[key]) < max_len:
    #             self.FD_SEP_df[key].append("inf")


    def write_results(self, all, metric, fiducial_sep):
        results_dir = os.path.join(self.configs.RESULTS_DIR, datetime.now().strftime('%Y_%m_%d-%H_%M') + "_" + str(uuid4())[:4])
        os.makedirs(results_dir, exist_ok=True)
    
        with open(os.path.join(results_dir, "config_summary.txt"), "w") as f:
            f.write(f"use_generated_ct_everywhere: {self.configs.use_generated_ct_everywhere}\n")
            f.write(f"use_generated_ct_for_segmentation: {self.configs.use_generated_ct_for_segmentation}\n")
            f.write(f"use_extended_ts_organs: {self.configs.use_extended_ts_organs}\n")
            f.write(f"LAMBDA: {self.configs.LAMBDA}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
        # Save global metrics to run-specific folder
        if all or metric:
            df_dice = pd.DataFrame(self.merged_dice)
            df_hd = pd.DataFrame(self.merged_hd)
            df_dice.to_csv(os.path.join(results_dir, self.configs.DICE_CSV_FILENAME), index=False)
            df_hd.to_csv(os.path.join(results_dir, self.configs.HD_CSV_FILENAME), index=False)
    
        if all or fiducial_sep:
            df_fd = pd.DataFrame(self.FD_SEP_df)
            df_fd.to_csv(os.path.join(results_dir, self.configs.FD_SEP_CSV_FILENAME), index=False)
    
        # Always update merged results
        merged_dir = os.path.join(self.configs.RESULTS_DIR, "merged_all")
        os.makedirs(merged_dir, exist_ok=True)
        pd.DataFrame(self.merged_dice).to_csv(os.path.join(merged_dir, "merged_dice.csv"), index=False)
        pd.DataFrame(self.merged_hd).to_csv(os.path.join(merged_dir, "merged_hd.csv"), index=False)

    def evaluate(self, data: str, force: bool=False, nums: List[int]=[], all: bool=False, seg: bool=False,
                 pw_linear: bool=False, dmap: bool=False, cxt: bool=False, fcsv: bool=False,
                 params: bool=False, register: bool=False, warp: bool=False, metric: bool=False,
                 fiducial_sep: bool=False, shared_variant: str = None):
        # Create the structure_tables_<variant> folder path
        log_dir = os.path.join(self.configs.RESULTS_DIR, f"structures_tables_{self.configs.VARIANT_TAG}")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"log_{self.configs.VARIANT_TAG}.txt")
        
        log_file = open(log_path, "w")
        sys.stdout = log_file
        sys.stderr = log_file
        print("--------------------------------------------------")
        print("PIPELINE CONFIGURATION:")
        if self.configs.use_generated_ct_everywhere:
            print("  - Using Generated CT everywhere (no pw-linear)")
        elif self.configs.use_generated_ct_for_segmentation:
            print("  - Using Generated CT only for segmentation")
        else:
            print("  - Using CBCT + pw-linear for input")
    
        if self.configs.use_extended_ts_organs:
            print("  - Using extended TS organs (colon, Femurs and Hips)")
        else:
            print("  - Using bladder-only segmentation")
        print("--------------------------------------------------\n")
        skip_gt_related = shared_variant is not None
        if skip_gt_related:
            print(f"[INFO] Skipping GT/NOPD-related steps. Reusing results from: {shared_variant}")
        
        evaluator = Evaluator(self.configs, self._utils, self._plastimatch)

        data = data if len(nums)==0 else [data[i] for i in nums]
        for patient_dir in data:
            print("--------------------------------------------------------------------")
            print(f"\t START: {patient_dir}")
            print("--------------------------------------------------------------------")
            try:

                ## Linear tranform of CBCT
                if all or pw_linear:
                    self.pw_linear_transformation(patient_dir, force)

                ## Segmenting the LTCBCT and the CT
                if all or seg:
                    ltcbct_path = os.path.join(patient_dir, self.configs.LT_CBCT_DIR)
                    ltcbct_seg_path = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR)
                    generatedct_path = os.path.join(patient_dir, self.configs.GENERATED_CT_DIR)
                 
                    seg_input_path = (
                        generatedct_path if (
                            self.configs.use_generated_ct_everywhere or self.configs.use_generated_ct_for_segmentation
                        ) else ltcbct_path
                    )
                 
                    roi_subset = [self.configs.TS_BLADDER_CLASS]
                    # roi_subset = [self.configs.TS_PROSTATE_CLASS]

                    if self.configs.use_extended_ts_organs:
                        roi_subset += [
                            self.configs.TS_COLON,
                            self.configs.TS_FEMUR_LEFT,
                            self.configs.TS_FEMUR_RIGHT,
                            self.configs.TS_HIP_LEFT, self.configs.TS_HIP_RIGHT
                        ]
                 # self.configs.TS_SACRUM

                 # self.configs.TS_PROSTATE_CLASS
                    # Segment LT_CBCT (or generated) and CT
                    self.segmentation(seg_input_path, ltcbct_seg_path, force, roi_subset=roi_subset)
                    ct_path = os.path.join(patient_dir, self.configs.CT_DIR)
                    ct_seg_path = os.path.join(patient_dir, self.configs.CT_SEG_DIR)
                    self.segmentation(ct_path, ct_seg_path, force, roi_subset=roi_subset)
                    
                    # Create folders to save uncropped copies
                    uncropped_ct_dir = os.path.join(patient_dir, f'eval_{self.configs.VARIANT_TAG}', "uncrp_CT_segments")
                    uncropped_cbct_dir = os.path.join(patient_dir, f'eval_{self.configs.VARIANT_TAG}', "uncrp_LT_CBCT_segments")
                    os.makedirs(uncropped_ct_dir, exist_ok=True)
                    os.makedirs(uncropped_cbct_dir, exist_ok=True)
                    
                    # Copy uncropped CT segments
                    for f in glob(f"{ct_seg_path}/*.nrrd"):
                        shutil.copy(f, os.path.join(uncropped_ct_dir, os.path.basename(f)))
                    
                    # Copy uncropped CBCT segments
                    for f in glob(f"{ltcbct_seg_path}/*.nrrd"):
                        shutil.copy(f, os.path.join(uncropped_cbct_dir, os.path.basename(f)))

                    # Define output dirs for DMAPs and FCSVs
                    uncropped_dmap_dir = os.path.join(patient_dir, f'eval_{self.configs.VARIANT_TAG}', "uncropped_dmaps")
                    uncropped_cxt_dir = os.path.join(patient_dir,  f'eval_{self.configs.VARIANT_TAG}', "uncropped_cxts")
                    uncropped_fcsv_dir = os.path.join(patient_dir, f'eval_{self.configs.VARIANT_TAG}', "uncropped_fcsvs")
                    os.makedirs(uncropped_dmap_dir, exist_ok=True)
                    os.makedirs(uncropped_cxt_dir, exist_ok=True)
                    os.makedirs(uncropped_fcsv_dir, exist_ok=True)
                    
                    # Generate DMAPs from uncropped segments
                    for seg_dir in [uncropped_ct_dir, uncropped_cbct_dir]:
                        for seg_path in glob(f"{seg_dir}/*.nrrd"):
                            class_name = self._utils.get_class_name(seg_path)
                            dmap_path = os.path.join(uncropped_dmap_dir, f"{class_name}.mha")
                            self._plastimatch.dmap(seg_path, dmap_path)
                    
                    # Convert uncropped CT segments to CXT, then to FCSV
                    for seg_path in glob(f"{uncropped_ct_dir}/*.nrrd"):
                        class_name = self._utils.get_class_name(seg_path)
                        cxt_path = os.path.join(uncropped_cxt_dir, f"{class_name}.cxt")
                        fcsv_path = os.path.join(uncropped_fcsv_dir, f"{class_name}.fcsv")
                        csv_path = os.path.join(uncropped_fcsv_dir, f"{class_name}.csv")
                    
                        self._plastimatch.convert("input-ss-img", seg_path, "output-cxt", cxt_path)
                        create_fcsv(cxt_path, fcsv_path, csv_path)
                        
                    # Automatically crop larger bladder to match smaller one
                    # Automatically crop bladder with larger Z-extent to the other
                    if self.configs.use_extended_ts_organs:
                        bladder_ct = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_BLADDER_CLASS}.nrrd")
                        bladder_cbct = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_BLADDER_CLASS}.nrrd")
                        self._utils.crop_larger_bladder_to_smaller_extent_by_zmm(bladder_ct, bladder_cbct)

                    # Cropping colon using CBCT sac extent
                    if self.configs.use_extended_ts_organs and self.configs.crop_colon:
                        colon_ct_path = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_COLON}.nrrd")
                        colon_cbct_path = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_COLON}.nrrd")
                    
                        # Apply sac filtering to CBCT colon (with height truncation)
                        # Keep bottom 30% of lowest colon structure
                        # Step 1: Crop the CBCT colon with bottom focus (you said leave this unchanged)
                        self._utils.crop_colon_to_lower_sac(colon_cbct_path, keep_ratio=0.8)
                        
                        # Step 2: Use CBCT colon to crop CT colon (now aligned properly!)
                        self._utils.crop_ct_colon_by_cbct_sac(colon_ct_path, colon_cbct_path)
                                                


                        femur_left_ct = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_FEMUR_LEFT}.nrrd")
                        femur_right_ct = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_FEMUR_RIGHT}.nrrd")
                        femur_left_cbct = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_FEMUR_LEFT}.nrrd")
                        femur_right_cbct = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_FEMUR_RIGHT}.nrrd")
                                        
                        # self._utils.crop_colon_by_femurs(femur_left_ct, femur_right_ct, colon_ct_path)
                        # self._utils.crop_colon_by_femurs(femur_left_cbct, femur_right_cbct, colon_cbct_path)
                    if self.configs.use_extended_ts_organs:
                        # ----------- Define paths -----------
                        hip_left_ct = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_HIP_LEFT}.nrrd")
                        hip_right_ct = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_HIP_RIGHT}.nrrd")

                        hip_left_cbct = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_HIP_LEFT}.nrrd")
                        hip_right_cbct = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_HIP_RIGHT}.nrrd")

                        # sacrum_ct = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{self.configs.TS_SACRUM}.nrrd")
                        # sacrum_cbct = os.path.join(patient_dir, self.configs.LT_CBCT_SEG_DIR, f"{self.configs.TS_SACRUM}.nrrd")

                        # ----------- Crop CT hips using femur pair -----------
                        self._utils.crop_ct_femur_using_cbct(femur_left_cbct, femur_left_ct)
                        self._utils.crop_ct_femur_using_cbct(femur_right_cbct, femur_right_ct)                    
                        # # ----------- Crop CT hips using femur pair -----------
                        self._utils.crop_hip_by_femurs(hip_left_cbct, hip_left_ct)
                        self._utils.crop_hip_by_femurs(hip_right_cbct, hip_right_ct)
                        # # ----------- Crop CT hips using femur pair -----------
                        # self._utils.crop_hip_by_femurs(sacrum_cbct, sacrum_ct)
                                                

                ## LT_CBCT dmap calculation from the LTCBCT TS masks and CBCT GT masks
                if all or dmap:
                    self.dmap_calcualtion(patient_dir, force)

                ## CT cxt creation from the CT TS and GT masks
                if all or cxt:
                    self.cxt_conversion(patient_dir, force)

                ## fcsv files creation
                if all or fcsv:
                    self.create_fcsvfile(patient_dir, force)

                ## Registers params.txt file creation
                if all or params or register or warp:
                    if skip_gt_related:
                        print("[INFO] Skipping GT/NOPD/GT Bladder Only registration param creation.")
                        NOPD = GT = GT_bladder_rectum_only = False
                        _, TS, _, _ = self.create_register_params(patient_dir, force=True)  # Only create TS params
                    else:
                        NOPD, TS, GT_bladder_rectum_only, GT = self.create_register_params(patient_dir, force)

                ## Start regitration
                if all or register:
                    self.start_registration(patient_dir, (NOPD, TS, GT_bladder_rectum_only, GT), force)

                ## Start warping
                if all or warp:
                    self.start_warp(patient_dir, force)


                # ## Calculate scores
                # if all or fiducial_sep:
                #     if not skip_gt_related:
                #         self.calculate_fiducial_sep(patient_dir)
                #     else:
                #         print("[INFO] Skipping GT/NOPD fiducial distance calculation.")
                
                if all or metric:
                    evaluator.calculate_scores(patient_dir)

                # if all or metric:
                #     self.calculate_scores(patient_dir)
            except Exception as e:
                print(f"Exception for patient: {patient_dir}")
                print(f"Error: {e}")
                
        evaluator.export_scores(os.path.join(self.configs.RESULTS_DIR, "merged_all"))
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        log_file.close()
