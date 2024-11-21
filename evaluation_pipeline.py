import argparse
from glob import glob
from evaluation.plastimatch import *
from evaluation.register_params import create_register_params_file
from totalsegmentator.python_api import totalsegmentator
import os
import shutil
from evaluation.fcsv import create_fcsv
from config import Configs
from evaluation.utils import get_class_name, get_roi_subset, get_patient_number
import pandas as pd


def segmentation(input_path, output_seg_path, force_run=False):
    if force_run and os.path.exists(output_seg_path):
        shutil.rmtree(output_seg_path)

    if os.path.exists(output_seg_path):
        print("skipping segmentation")
        return
    
    _, roi_subset = get_roi_subset(input_path)
    totalsegmentator(input_path, output_seg_path, roi_subset=roi_subset)
        
def pw_linear_transformation(patient_dir, force_run=False):
    cbct_path =  os.path.join(patient_dir, configs.CBCT_DIR)
    ltcbct_path = os.path.join(patient_dir, configs.LT_CBCT_DIR)
    if force_run and os.path.exists(ltcbct_path):
        shutil.rmtree(ltcbct_path)

    if os.path.exists(ltcbct_path):
        print("skipping linear tranformation")
        return

    pw_linear_transform(cbct_path, ltcbct_path)
    convert("input", f"{ltcbct_path}.nrrd", "output-dicom", ltcbct_path)

def dmap_calcualtion(patient_dir, force_run=False):
    dmaps_dir = os.path.join(patient_dir, configs.DMAPS_DIR)
    if force_run and os.path.exists(dmaps_dir):
        shutil.rmtree(dmaps_dir)

    if os.path.exists(dmaps_dir):
        print("skipping dmap calculation")
        return

    os.makedirs(dmaps_dir, exist_ok=True)
    ltcbct_seg_path = os.path.join(patient_dir, configs.LT_CBCT_SEG_DIR)
    cbct_gt_contours_path = os.path.join(patient_dir, configs.GT_CONTOURS_DIR, configs.CBCT_DIR)
    input_paths = glob(f"{ltcbct_seg_path}/*") + glob(f"{cbct_gt_contours_path}/*")
    for input_path in input_paths:
        class_name = get_class_name(input_path)
        if class_name:
            output_path = os.path.join(dmaps_dir, f"{class_name}.mha")
            dmap(input_path, output_path)

def cxt_conversion(patient_dir, force_run=False):
    cxts_dir = os.path.join(patient_dir, configs.CXTS_DIR)
    if force_run and os.path.exists(cxts_dir):
        shutil.rmtree(cxts_dir)

    if os.path.exists(cxts_dir):
        print("skipping cxts creation")
        return
    
    os.makedirs(cxts_dir, exist_ok=True)
    
    ct_seg_path = os.path.join(patient_dir, configs.CT_SEG_DIR)
    ct_gt_contours_path = os.path.join(patient_dir, configs.GT_CONTOURS_DIR, configs.CT_DIR)
    input_paths = glob(f"{ct_seg_path}/*") + glob(f"{ct_gt_contours_path}/*")
    for input_path in input_paths:
        class_name = get_class_name(input_path)
        if class_name:
            output_path = os.path.join(cxts_dir, f"{class_name}.cxt")
            convert("input-ss-img", input_path, "output-cxt", output_path)

def create_fcsvfile(patient_dir, force_run=False):
    fcsvs_dir = os.path.join(patient_dir, configs.FCVS_DIR)
    if force_run and os.path.exists(fcsvs_dir):
        shutil.rmtree(fcsvs_dir)

    if os.path.exists(fcsvs_dir):
        print("skipping fcsvs creation")
        return
    
    os.makedirs(fcsvs_dir, exist_ok=True)
    cxts_dir = os.path.join(patient_dir, configs.CXTS_DIR)
    for cxt_filepath in glob(f"{cxts_dir}/*"):
        class_name = get_class_name(cxt_filepath)
        fcsv_filepath = os.path.join(fcsvs_dir, f"{class_name}.fcsv")
        csv_filepath = os.path.join(fcsvs_dir, f"{class_name}.csv")
        create_fcsv(cxt_filepath, fcsv_filepath, csv_filepath)

def create_register_params(patient_dir):

    # Flags to keep track of the register params file created
    NOPD, TS, GT_bladder_only, GT = False, False, False, False
    patient_number, TS_roi_subset = get_roi_subset(patient_dir)
    
    NOPD = create_register_params_file(patient_dir, configs.NOPD)
    
    segments = []
    for class_name in TS_roi_subset:
        class_name = get_class_name(class_name)
        segments.append({
            "fixed_file": os.path.join(patient_dir, configs.FCVS_DIR, f"{class_name}.fcsv"),
            "moving_file": os.path.join(patient_dir, configs.DMAPS_DIR, f"{class_name}.mha")
        })
    TS = create_register_params_file(patient_dir, configs.TS, segments)

    ct_gt_contours_path = os.path.join(patient_dir, configs.GT_CONTOURS_DIR, configs.CT_DIR)
    if (str(patient_number) in configs.patients_with_GT) and (os.path.exists(ct_gt_contours_path)):
        class_name = get_class_name(configs.GT_BLADDER_CLASS)
        segments = [{
                "fixed_file": os.path.join(patient_dir, configs.FCVS_DIR, f"{class_name}.fcsv"),
                "moving_file": os.path.join(patient_dir, configs.DMAPS_DIR, f"{class_name}.mha")
            }]
        GT_bladder_only = create_register_params_file(patient_dir, configs.GT_BLADDER_ONLY, segments)

        segments = []
        for class_name in configs.GT_roi_subset:
            class_name = get_class_name(class_name)
            segments.append({
                "fixed_file": os.path.join(patient_dir, configs.FCVS_DIR, f"{class_name}.fcsv"),
                "moving_file": os.path.join(patient_dir, configs.DMAPS_DIR, f"{class_name}.mha")
            })
        GT = create_register_params_file(patient_dir, configs.GT, segments)

    return (NOPD, TS, GT_bladder_only, GT)

def start_registration(patient_dir, flags):
    NOPD, TS, GT_bladder_only, GT = flags
    params_dir = os.path.join(patient_dir, configs.REGISTER_PARAMS_DIR)

    if NOPD:
        params_txt = os.path.join(params_dir, f"{configs.NOPD}.txt")
        register(params_txt)
    else:
        print("NOPD Params file not created")

    if TS:
        params_txt = os.path.join(params_dir, f"{configs.TS}.txt")
        register(params_txt)
    else:
        print("TS Params file not created")
    
    if GT_bladder_only:
        params_txt = os.path.join(params_dir, f"{configs.GT_BLADDER_ONLY}.txt")
        register(params_txt)
    else:
        print("GT Bladder Only Params file not created")

    if GT:
        params_txt = os.path.join(params_dir, f"{configs.GT}.txt")
        register(params_txt)
    else:
        print("GT Params file not created")

def start_warp(patient_dir):
    patient_number, TS_roi_subset = get_roi_subset(patient_dir)
    input_dir = os.path.join(patient_dir, configs.GT_CONTOURS_DIR, configs.CBCT_DIR)
    output_dir = os.path.join(patient_dir, configs.WARPS_DIR)
    vf_dir = os.path.join(patient_dir, configs.VF_VOLUMES_DIR)
    if (str(patient_number) in configs.patients_with_GT):
        for segment in configs.GT_roi_subset:
            
            input = os.path.join(input_dir, f"{segment}.mha")

            # Warping the segment with VF_GT.nrrd
            output = os.path.join(output_dir, f"{configs.WARP_PREFIX}{configs.GT}_{segment}")
            vf = os.path.join(vf_dir, f"{configs.VF_PREFIX}{configs.GT}.nrrd")
            warp(input, output, vf)
            
            # Warping the segment with VF_NOPD.nrrd
            output = os.path.join(output_dir, f"{configs.WARP_PREFIX}{configs.NOPD}_{segment}")
            vf = os.path.join(vf_dir, f"{configs.VF_PREFIX}{configs.NOPD}.nrrd")
            warp(input, output, vf)
            
            # Warping the segment with VF_GT_bladder_only.nrrd
            output = os.path.join(output_dir, f"{configs.WARP_PREFIX}{configs.GT_BLADDER_ONLY}_{segment}")
            vf = os.path.join(vf_dir, f"{configs.VF_PREFIX}{configs.GT_BLADDER_ONLY}.nrrd")
            warp(input, output, vf)


    for segment in TS_roi_subset:
        # Warping the segment with VF_TS.nrrd
        input = os.path.join(patient_dir, configs.LT_CBCT_SEG_DIR, f"{segment}.nii.gz")
        output = os.path.join(output_dir, f"{configs.WARP_PREFIX}{segment}")
        vf = os.path.join(vf_dir, f"{configs.VF_PREFIX}{configs.TS}.nrrd")
        warp(input, output, vf)

def calculate_scores(patient_dir):
    results = {}
    warps_dir = os.path.join(patient_dir, configs.WARPS_DIR)
    _ , TS_roi_subset = get_roi_subset(patient_dir)
    for warp in glob(f"{warps_dir}/*"):
        class_name = get_class_name(warp)[3:]
        
        if class_name in TS_roi_subset:
            segment = os.path.join(patient_dir, configs.CT_SEG_DIR, f"{class_name}.nii.gz")
        else:
            segment = os.path.join(patient_dir, configs.GT_CONTOURS_DIR, configs.CT_DIR, f"{class_name}.mha")
        
        result = dice(segment, warp)
        if result != None:
            result = result.stdout.split("\n")
            DSC, HD = list(filter(lambda x: "DICE" in x or "Percent (0.95) Hausdorff distance (boundary)" in x, result))
            DSC, HD = DSC.split(":")[1].strip(), HD.split("=")[1].strip()
            results[os.path.basename(warp)[:-4]] = (DSC, HD)
        else:
            results[os.path.basename(warp)[:-4]] = ('None', 'None')
    
    patient_number = get_patient_number(patient_dir)
    DSC_df["patient_number"].append(patient_number)
    HD_df["patient_number"].append(patient_number)
    for key in DSC_df.keys():
        if key != "patient_number":
            if key in results:
                DSC_df[key].append(results[key][0])
                HD_df[key].append(results[key][1])
            else:
                DSC_df[key].append('0')
                HD_df[key].append('0')

DSC_df = {
    "patient_number": [],
    "W_GT_Bladder": [],
    "W_GT_Prostate": [],
    "W_GT_Rectum": [],
    "W_GT_bladder_only_Bladder": [],
    "W_GT_bladder_only_Prostate": [],
    "W_GT_bladder_only_Rectum": [],
    "W_NOPD_Bladder": [],
    "W_NOPD_Prostate": [],
    "W_NOPD_Rectum": [],
    "W_urinary_bladder": [],
}
HD_df = {
    "patient_number": [],
    "W_GT_Bladder": [],
    "W_GT_Prostate": [],
    "W_GT_Rectum": [],
    "W_GT_bladder_only_Bladder": [],
    "W_GT_bladder_only_Prostate": [],
    "W_GT_bladder_only_Rectum": [],
    "W_NOPD_Bladder": [],
    "W_NOPD_Prostate": [],
    "W_NOPD_Rectum": [],
    "W_urinary_bladder": [],
}

def main(args):
    # args.force_run = True
    # args.patient_dirs = [
    #     ".\datasets\pelvic_reference\Pelvic-Ref-003",
    #     ".\datasets\pelvic_reference\Pelvic-Ref-004"
    # ]
    # for patient_dir in args.patient_dirs:
    for patient_dir in glob(args.patient_dirs):
        print("--------------------------------------------------------------------")
        print(f"\t START: {patient_dir}")
        print("--------------------------------------------------------------------")
        try:
            # ## Linear tranform of CBCT
            # pw_linear_transformation(patient_dir, args.force_run)

            # ## Segmenting the LTCBCT
            # ltcbct_path = os.path.join(patient_dir, configs.LT_CBCT_DIR)
            # ltcbct_seg_path = os.path.join(patient_dir, configs.LT_CBCT_SEG_DIR)
            # segmentation(ltcbct_path, ltcbct_seg_path, args.force_run)
            
            # ## Segmenting the CT
            # ct_path = os.path.join(patient_dir, configs.CT_DIR)
            # ct_seg_path = os.path.join(patient_dir, configs.CT_SEG_DIR)
            # segmentation(ct_path, ct_seg_path, args.force_run)

            # ## LT_CBCT dmap calculation from the LTCBCT TS masks and CBCT GT masks
            # dmap_calcualtion(patient_dir, args.force_run)

            # ## CT cxt creation from the CT TS and GT masks
            # cxt_conversion(patient_dir, args.force_run)

            # ## fcsv files creation
            # create_fcsvfile(patient_dir, args.force_run)

            # ## Registers params.txt file creation
            # NOPD, TS, GT_bladder_only, GT = create_register_params(patient_dir)

            # ## Start regitration
            # start_registration(patient_dir, (NOPD, TS, GT_bladder_only, GT))
            
            # ## Start warping
            # start_warp(patient_dir)

            ## Calculate scores
            calculate_scores(patient_dir)
            df = pd.DataFrame(DSC_df)
            df.to_csv("dice.csv", index=False)
            df = pd.DataFrame(HD_df)
            df.to_csv("hd.csv", index=False)


        
        except Exception as e:
            print(f"Exception for patient: {patient_dir}")
            print(f"Error: {e}")
        finally:
            print("--------------------------------------------------------------------")
            print(f"\t END: {patient_dir}")
            print("--------------------------------------------------------------------")
            
        # break

configs = Configs()

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--patient_dirs", type=str, help="All patient dirs in glob format")
    parser.add_argument("--force_run", action='store_true', help="All patient dits in glob format")

    args = parser.parse_args()
    main(args)