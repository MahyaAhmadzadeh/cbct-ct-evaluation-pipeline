from glob import glob
from typing import List
from evaluation.params import create_params_txt
from totalsegmentator.python_api import totalsegmentator
import os
from evaluation.fcsv import create_fcsv
from evaluation.plastimatch import Plastimatch
from evaluation.config import EvaluationConfig
from evaluation.utils import Utils
import pandas as pd
import numpy as np

class EvaluationPipeline:
    def __init__(self) -> None:
        self.configs = EvaluationConfig()
        self.DSC_df = { v: [] for v in self.configs.LUT.keys() }
        self.HD_df =  { v: [] for v in self.configs.LUT.keys() }
        self.FD_SEP_df = {
            self.configs.PATIENT_NUM_KEY: [],
            self.configs.GT: [],
            self.configs.GT_BLADDER_ONLY: [],
            self.configs.NOPD: [],
            self.configs.TS: []
        }
        self._plastimatch = Plastimatch()
        self._utils = Utils(self.configs)


    def pw_linear_transformation(self, patient_dir, force):
        ltcbct_path = os.path.join(patient_dir, self.configs.LT_CBCT_DIR)
        is_skip = self._utils.replace_or_skip(ltcbct_path, force)
        if is_skip: return
        
        cbct_path =  os.path.join(patient_dir, self.configs.CBCT_DIR)
        self._plastimatch.pw_linear_transform(cbct_path, ltcbct_path)
        self._plastimatch.convert("input", f"{ltcbct_path}.nrrd", "output-dicom", ltcbct_path)

    def segmentation(self, input_path, output_seg_path, force):
        is_skip = self._utils.replace_or_skip(output_seg_path, force)
        if is_skip: return

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
        NOPD, TS, GT_bladder_only, GT = False, False, False, False

        reg_params_dir = os.path.join(patient_dir, self.configs.REGISTER_PARAMS_DIR)
        is_skip = self._utils.replace_or_skip(reg_params_dir, force)
        if is_skip:
            return (NOPD, TS, GT_bladder_only, GT)
        
        patient_number, TS_roi_subset = self._utils.get_roi_subset(patient_dir)
        
        NOPD = create_params_txt(patient_dir, self.configs.NOPD)
        
        segments = []
        for class_name in TS_roi_subset:
            class_name = self._utils.get_class_name(class_name)
            segments.append({
                "fixed_file": os.path.join(patient_dir, self.configs.FCVS_DIR, f"{class_name}.fcsv"),
                "moving_file": os.path.join(patient_dir, self.configs.DMAPS_DIR, f"{class_name}.mha")
            })
        TS = create_params_txt(patient_dir, self.configs.TS, segments)

        ct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR)
        if (str(patient_number) in self.configs.patients_with_GT) and (os.path.exists(ct_gt_contours_path)):
            class_name = self._utils.get_class_name(self.configs.GT_BLADDER_CLASS)
            segments = [{
                    "fixed_file": os.path.join(patient_dir, self.configs.FCVS_DIR, f"{class_name}.fcsv"),
                    "moving_file": os.path.join(patient_dir, self.configs.DMAPS_DIR, f"{class_name}.mha")
                }]
            GT_bladder_only = create_params_txt(patient_dir, self.configs.GT_BLADDER_ONLY, segments)

            segments = []
            for class_name in self.configs.GT_roi_subset:
                class_name = self._utils.get_class_name(class_name)
                segments.append({
                    "fixed_file": os.path.join(patient_dir, self.configs.FCVS_DIR, f"{class_name}.fcsv"),
                    "moving_file": os.path.join(patient_dir, self.configs.DMAPS_DIR, f"{class_name}.mha")
                })
            GT = create_params_txt(patient_dir, self.configs.GT, segments)

        return (NOPD, TS, GT_bladder_only, GT)

    def start_registration(self, patient_dir, flags, force):
        
        reg_vol_dir = os.path.join(patient_dir, self.configs.REGISTERED_VOLUMES_DIR)
        is_skip = self._utils.replace_or_skip(reg_vol_dir, force)
        if is_skip:
            return

        NOPD, TS, GT_bladder_only, GT = flags
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
        
        if GT_bladder_only:
            params_txt = os.path.join(params_dir, f"{self.configs.GT_BLADDER_ONLY}.txt")
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
                output = os.path.join(warps_seg_dir, f"{self.configs.WARP_PREFIX}{self.configs.GT_BLADDER_ONLY}_{segment}.mha")
                vf = os.path.join(vf_dir, f"{self.configs.VF_PREFIX}{self.configs.GT_BLADDER_ONLY}.nrrd")
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

    def calculate_scores(self, patient_dir):

        results = {}
        warps_dir = os.path.join(patient_dir, self.configs.WARPS_DIR, self.configs.SEGMENTS)
        _ , TS_roi_subset = self._utils.get_roi_subset(patient_dir)
        for warp in glob(f"{warps_dir}/*"):
            class_name = self._utils.get_class_name(warp)[3:]
            if class_name in TS_roi_subset:
                segment = os.path.join(patient_dir, self.configs.CT_SEG_DIR, f"{class_name}.nrrd")
            else:
                segment = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR, f"{class_name}.mha")
            result = self._plastimatch.dice(segment, warp)
            if result != None:
                result = result.stdout.split("\n")
                DSC, HD = list(filter(lambda x: "DICE" in x or "Percent (0.95) Hausdorff distance (boundary)" in x, result))
                DSC, HD = DSC.split(":")[1].strip(), HD.split("=")[1].strip()
                results[os.path.basename(warp)[:-4]] = (DSC, HD)
            else:
                results[os.path.basename(warp)[:-4]] = ('None', 'None')
        
        patient_number = self._utils.get_patient_number(patient_dir)
        self.DSC_df[self.configs.PATIENT_NUM_KEY].append(patient_number)
        self.HD_df[self.configs.PATIENT_NUM_KEY].append(patient_number)
        for key in self.DSC_df.keys():
            if key != self.configs.PATIENT_NUM_KEY:
                lut_key = self.configs.LUT[key]
                if lut_key in results:
                    self.DSC_df[key].append(results[lut_key][0])
                    self.HD_df[key].append(results[lut_key][1])
                else:
                    self.DSC_df[key].append('0')
                    self.HD_df[key].append('0')

    def calculate_fiducial_sep(self, patient_dir):
        ct_gt_contours_path = os.path.join(patient_dir, self.configs.GT_CONTOURS_DIR, self.configs.CT_DIR)
        patient_num = self._utils.get_patient_number(patient_dir)
        self.FD_SEP_df[self.configs.PATIENT_NUM_KEY].append(patient_num)
        if (str(patient_num) in self.configs.patients_with_GT) and (os.path.exists(ct_gt_contours_path)):
            ct_fdm = os.path.join(patient_dir, self.configs.FDMS_DIR, f"{patient_num}-{self.configs.CT_DIR}-fdm.fcsv")
            ct_coord = self._utils.get_coordinates(ct_fdm)
            w_fcsvs_dir = os.path.join(patient_dir, self.configs.WARPS_DIR, self.configs.FCVS)
            for key in self.FD_SEP_df:
                if key != self.configs.PATIENT_NUM_KEY:
                    w_cbct_fcsv = os.path.join(w_fcsvs_dir, f"{self.configs.WARP_PREFIX}{key}_{patient_num}-{self.configs.CBCT_DIR}-fdm.fcsv")
                    if os.path.exists(w_cbct_fcsv):
                        w_cbct_coord = self._utils.get_coordinates(w_cbct_fcsv)
                        mu_sep = np.sqrt(np.sum(np.square(w_cbct_coord - ct_coord), 1)).mean() # Euclidean distance
                        key = os.path.basename(w_cbct_fcsv).removeprefix(self.configs.WARP_PREFIX).removesuffix(f"_{patient_num}-{self.configs.CBCT_DIR}-fdm.fcsv")
                        self.FD_SEP_df[key].append(mu_sep)
                    else:
                        self.FD_SEP_df[key].append("inf")
            print(f"Patient-{patient_num} fiducial separation calcualted")
        else:
            print(f"Patient-{patient_num} do not have fiducials")
            for key in self.FD_SEP_df.keys():
                if key != self.configs.PATIENT_NUM_KEY:
                    self.FD_SEP_df[key].append("inf")

    def write_results(self, all, metric, fiducial_sep):
        if all or metric:
            df = pd.DataFrame(self.DSC_df)
            df.to_csv(self.configs.DICE_CSV_FILENAME, index=False)
            df = pd.DataFrame(self.HD_df)
            df.to_csv(self.configs.HD_CSV_FILENAME, index=False)
        
        if all or fiducial_sep:
            df = pd.DataFrame(self.FD_SEP_df)
            df.to_csv(self.configs.FD_SEP_CSV_FILENAME, index=False)

    def evaluate(self, data: str, force: bool=False, nums: List[int]=[], all: bool=False, seg: bool=False,
                 pw_linear: bool=False, dmap: bool=False, cxt: bool=False, fcsv: bool=False,
                 params: bool=False, register: bool=False, warp: bool=False, metric: bool=False,
                 fiducial_sep: bool=False):
        
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
                    self.segmentation(ltcbct_path, ltcbct_seg_path, force)

                    ct_path = os.path.join(patient_dir, self.configs.CT_DIR)
                    ct_seg_path = os.path.join(patient_dir, self.configs.CT_SEG_DIR)
                    self.segmentation(ct_path, ct_seg_path, force)

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
                if all or params:
                    NOPD, TS, GT_bladder_only, GT = self.create_register_params(patient_dir, force)

                ## Start regitration
                if all or register:
                    self.start_registration(patient_dir, (NOPD, TS, GT_bladder_only, GT), force)
                
                ## Start warping
                if all or warp:
                    self.start_warp(patient_dir, force)

                ## Calculate scores
                if all or metric:
                    self.calculate_scores(patient_dir)
                    
                ## Calculate scores
                if all or fiducial_sep:
                    self.calculate_fiducial_sep(patient_dir)
            except Exception as e:
                print(f"Exception for patient: {patient_dir}")
                print(f"Error: {e}")

        self.write_results(all, metric, fiducial_sep)
