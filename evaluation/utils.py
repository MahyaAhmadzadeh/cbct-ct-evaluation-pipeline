import re
import os
import shutil
import csv
import numpy as np
import SimpleITK as sitk
import math
import scipy.ndimage  # add at the top of your utils.py if not already there

class Utils:

    def __init__(self, configs) -> None:
        self.configs = configs       
    def resample_to_reference(self, image, reference):
        resample = sitk.ResampleImageFilter()
        resample.SetReferenceImage(reference)
        resample.SetInterpolator(sitk.sitkNearestNeighbor)
        resample.SetTransform(sitk.Transform(3, sitk.sitkIdentity))
        return resample.Execute(image)

    def get_class_name(self, path) -> str:
        name = os.path.basename(path).replace(".nii.gz", "").replace(".nrrd", "").replace(".mha", "").replace(".cxt", "")
        if name == self.configs.TS_PROSTATE_CLASS:
            return "TS_" + name
        elif name == self.configs.TS_BLADDER_CLASS:
            return "TS_" + name
        elif name == self.configs.GT_BLADDER_CLASS:
            return "GT_" + name
        elif name == self.configs.GT_PROSTATE_CLASS:
            return "GT_" + name
        elif name == self.configs.GT_RECTUM_CLASS:
            return "GT_" + name
        elif name == self.configs.TS_COLON:
            return "TS_" + name
        elif name == self.configs.TS_FEMUR_LEFT:
            return "TS_" + name
        elif name == self.configs.TS_FEMUR_RIGHT:
            return "TS_" + name
        elif name == self.configs.TS_HIP_LEFT:
            return "TS_" + name
        elif name == self.configs.TS_HIP_RIGHT:
            return "TS_" + name
        elif name == self.configs.TS_SACRUM:
            return "TS_" + name
        else:
            return name



    def get_patient_number(self, patient_dir) -> str:
        prefix = self.configs.PATIENT_PREFIX
        match = re.search(rf"(?<={prefix}-)\d+", patient_dir)
        return match[0] if match else "000"

    def get_roi_subset(self, patient_dir):
        patient_number = self.get_patient_number(patient_dir)
        roi_subset = []
        if patient_number in self.configs.patients_with_GT:
            # roi_subset = [self.configs.TS_PROSTATE_CLASS]
            roi_subset = [self.configs.TS_BLADDER_CLASS]
            if self.configs.use_extended_ts_organs:
                roi_subset += [
                    self.configs.TS_COLON, 
                    self.configs.TS_FEMUR_LEFT, self.configs.TS_FEMUR_RIGHT,
                    self.configs.TS_HIP_LEFT, self.configs.TS_HIP_RIGHT
                    
                ]
                # self.configs.TS_SACRUM
                # self.configs.TS_PROSTATE_CLASS
        return patient_number, roi_subset


    def replace_or_skip(self, dir, force) -> bool:
        if force and os.path.exists(dir):
            shutil.rmtree(dir)
        if os.path.exists(dir):
            print("skipping result creation")
            return True
        os.makedirs(dir, exist_ok=True)
        return False

    def get_coordinates(self, path) -> np.ndarray:
        with open(path,'r') as csvfile:
            data = csv.reader(filter(lambda row: row[0]!='#', csvfile))
            coord = None
            for i in data:
                curr = list(map(lambda x: float(x), i[1:4]))
                coord = np.array(curr).reshape((1, 3)) if coord is None else np.vstack((coord, curr))
            
            return coord
    
    def convert_nifti_to_nrrd(self, nifti_file_path):
        try:
            nifti_image = sitk.ReadImage(nifti_file_path)
            nrrd_file_path = os.path.join(os.path.dirname(nifti_file_path), f"{os.path.basename(nifti_file_path).removesuffix('.nii.gz')}.nrrd")
            sitk.WriteImage(nifti_image, nrrd_file_path)
            print(f"Saved .nrrd: {nrrd_file_path}")
            os.remove(nifti_file_path)
            print(f"Removed nifti: {nifti_file_path}")
        except Exception as e:
            print("Nifti to .nrrd conversion failed")
    def crop_colon_by_femurs(self, femur_left_path, femur_right_path, colon_path):
        try:
            if not os.path.exists(colon_path):
                print(f"Colon file missing: {colon_path}")
                return
            colon = sitk.ReadImage(colon_path)
            colon_array = sitk.GetArrayFromImage(colon)
     
            max_zs = []
     
            for femur_path in [femur_left_path, femur_right_path]:
                if os.path.exists(femur_path):
                    femur = sitk.ReadImage(femur_path)
                    femur_array = sitk.GetArrayFromImage(femur)
                    z_indices = np.any(femur_array, axis=(1, 2))
                    if np.any(z_indices):
                        max_zs.append(np.where(z_indices)[0].max())
     
            if not max_zs:
                print("No femur found for cropping")
                return
     
            max_z = max(max_zs)
            colon_array[max_z:] = 0
     
            cropped = sitk.GetImageFromArray(colon_array)
            cropped.CopyInformation(colon)
            sitk.WriteImage(cropped, colon_path)
            print(f"Cropped colon at z > {max_z}")
        except Exception as e:
            print(f"Cropping colon failed: {e}")
    def crop_ct_colon_by_cbct_sac(self, ct_colon_path, cbct_colon_path):
        try:
            # Load both images
            ct_img = sitk.ReadImage(ct_colon_path)
            cbct_img = sitk.ReadImage(cbct_colon_path)
    
            # Resample CBCT colon to CT geometry
            resample = sitk.ResampleImageFilter()
            resample.SetReferenceImage(ct_img)
            resample.SetInterpolator(sitk.sitkNearestNeighbor)
            resample.SetTransform(sitk.Transform(3, sitk.sitkIdentity))
            resample.SetDefaultPixelValue(0)
            resample.SetOutputSpacing(ct_img.GetSpacing())
            resample.SetOutputOrigin(ct_img.GetOrigin())
            resample.SetOutputDirection(ct_img.GetDirection())
            resample.SetSize(ct_img.GetSize())
    
            cbct_resampled = resample.Execute(cbct_img)
            cbct_array = sitk.GetArrayFromImage(cbct_resampled)
    
            nonzero_slices = np.where(np.any(cbct_array, axis=(1, 2)))[0]
            if len(nonzero_slices) == 0:
                print("[SKIP] Resampled CBCT colon is empty.")
                return
    
            z_min = nonzero_slices.min()
            z_max = nonzero_slices.max()
            print(f"[INFO] Cropping CT colon using CBCT Z range: {z_min}–{z_max}")
    
            # Load CT colon and crop it
            ct_array = sitk.GetArrayFromImage(ct_img)
            ct_array[:z_min] = 0
            ct_array[z_max + 1:] = 0
    
            # Keep largest component
            labeled_array, num_labels = scipy.ndimage.label(ct_array)
            if num_labels == 0:
                print("[WARNING] CT colon empty after cropping.")
                return
    
            sizes = scipy.ndimage.sum(ct_array, labeled_array, range(1, num_labels + 1))
            largest_idx = int(np.argmax(sizes)) + 1
            cleaned_array = np.where(labeled_array == largest_idx, ct_array, 0)
    
            cleaned_img = sitk.GetImageFromArray(cleaned_array)
            cleaned_img.CopyInformation(ct_img)
            sitk.WriteImage(cleaned_img, ct_colon_path)
            print(f"[CROPPED] CT colon saved with Z ∈ [{z_min}, {z_max}]")
    
        except Exception as e:
            print(f"[ERROR] crop_ct_colon_by_cbct_sac failed: {e}")
            import traceback
            traceback.print_exc()


    def crop_colon_to_lower_sac(self, colon_path, keep_ratio=0.3):
        try:
            if not os.path.exists(colon_path):
                print(f"[SKIP] Missing colon file: {colon_path}")
                return
    
            colon_img = sitk.ReadImage(colon_path)
            colon_array = sitk.GetArrayFromImage(colon_img)
    
            # Label connected components
            labeled_array, num_labels = scipy.ndimage.label(colon_array)
            if num_labels == 0:
                print(f"[WARNING] No colon components found in {colon_path}")
                return
    
            # Get lowest Z centroid component
            centroids = scipy.ndimage.center_of_mass(colon_array, labeled_array, range(1, num_labels + 1))
            lowest_idx = int(np.argmin([c[0] for c in centroids])) + 1
            component_mask = (labeled_array == lowest_idx)
    
            z_voxels = np.where(np.any(component_mask, axis=(1, 2)))[0]
            if len(z_voxels) == 0:
                print("[WARNING] No voxels in lowest colon component.")
                return
    
            z_min = z_voxels.min()
            z_max = z_voxels.max()
            z_len = z_max - z_min
            new_z_max = z_min + int(z_len * keep_ratio)
    
            print(f"[INFO] Trimming to bottom {keep_ratio*100:.1f}% of Z ∈ [{z_min}, {new_z_max}]")
    
            cropped_array = np.where(component_mask, colon_array, 0)
            cropped_array[:z_min] = 0
            cropped_array[new_z_max + 1:] = 0
    
            cropped_img = sitk.GetImageFromArray(cropped_array)
            cropped_img.CopyInformation(colon_img)
            sitk.WriteImage(cropped_img, colon_path)
            print(f"[CROPPED] Saved cropped CBCT colon to: {colon_path}")
    
        except Exception as e:
            print(f"[ERROR] crop_colon_to_lower_sac failed: {e}")
            import traceback
            traceback.print_exc()
    def crop_larger_bladder_to_smaller_extent_by_zmm(self, bladder_path1, bladder_path2):
        try:
            img1 = sitk.ReadImage(bladder_path1)
            img2 = sitk.ReadImage(bladder_path2)
            arr1 = sitk.GetArrayFromImage(img1)
            arr2 = sitk.GetArrayFromImage(img2)
    
            z_indices1 = np.where(np.any(arr1, axis=(1, 2)))[0]
            z_indices2 = np.where(np.any(arr2, axis=(1, 2)))[0]
    
            if len(z_indices1) == 0 or len(z_indices2) == 0:
                print("[SKIP] One of the bladder masks is empty.")
                return
    
            # Compute physical Z ranges (in mm)
            spacing1, origin1 = img1.GetSpacing(), img1.GetOrigin()
            spacing2, origin2 = img2.GetSpacing(), img2.GetOrigin()
    
            z_start1_mm = origin1[2] + z_indices1[0] * spacing1[2]
            z_end1_mm   = origin1[2] + z_indices1[-1] * spacing1[2]
            z_range1_mm = z_end1_mm - z_start1_mm
    
            z_start2_mm = origin2[2] + z_indices2[0] * spacing2[2]
            z_end2_mm   = origin2[2] + z_indices2[-1] * spacing2[2]
            z_range2_mm = z_end2_mm - z_start2_mm
    
            print(f"[INFO] CT bladder Z range (mm): {z_range1_mm:.2f}")
            print(f"[INFO] CBCT bladder Z range (mm): {z_range2_mm:.2f}")
    
            # Determine which to crop
            if z_range1_mm <= z_range2_mm:
                smaller_img, smaller_path = img1, bladder_path1
                larger_img, larger_arr, larger_path = img2, arr2, bladder_path2
            else:
                smaller_img, smaller_path = img2, bladder_path2
                larger_img, larger_arr, larger_path = img1, arr1, bladder_path1
    
            # Resample smaller to larger's space
            resample = sitk.ResampleImageFilter()
            resample.SetReferenceImage(larger_img)
            resample.SetInterpolator(sitk.sitkNearestNeighbor)
            resample.SetTransform(sitk.Transform(3, sitk.sitkIdentity))
            resample.SetDefaultPixelValue(0)
            resample.SetOutputSpacing(larger_img.GetSpacing())
            resample.SetOutputOrigin(larger_img.GetOrigin())
            resample.SetOutputDirection(larger_img.GetDirection())
            resample.SetSize(larger_img.GetSize())
    
            smaller_resampled = resample.Execute(smaller_img)
            smaller_arr = sitk.GetArrayFromImage(smaller_resampled)
    
            # Get 3D bounding box of the resampled smaller mask
            nz = np.argwhere(smaller_arr > 0)
            if nz.size == 0:
                print("[WARNING] Resampled smaller bladder is empty.")
                return
    
            zmin, ymin, xmin = nz.min(axis=0)
            zmax, ymax, xmax = nz.max(axis=0)
    
            print(f"[INFO] Cropping larger mask to Z[{zmin}:{zmax}], Y[{ymin}:{ymax}], X[{xmin}:{xmax}]")
    
            cropped = np.copy(larger_arr)
            cropped[:zmin] = 0
            cropped[zmax+1:] = 0
            cropped[:, :ymin, :] = 0
            cropped[:, ymax+1:, :] = 0
            cropped[:, :, :xmin] = 0
            cropped[:, :, xmax+1:] = 0
    
            # Keep only largest component
            labeled_array, num_labels = scipy.ndimage.label(cropped)
            if num_labels == 0:
                print("[WARNING] Cropped bladder is empty.")
                return
    
            sizes = scipy.ndimage.sum(cropped, labeled_array, range(1, num_labels + 1))
            largest_idx = int(np.argmax(sizes)) + 1
            final_arr = np.where(labeled_array == largest_idx, cropped, 0)
    
            # Save result
            out_img = sitk.GetImageFromArray(final_arr)
            out_img.CopyInformation(larger_img)
            sitk.WriteImage(out_img, larger_path)
            print(f"[CROPPED] Final bladder saved to: {larger_path}")
    
        except Exception as e:
            print(f"[ERROR] crop_larger_bladder_to_smaller_extent_by_zmm failed: {e}")
            import traceback
            traceback.print_exc()

    def crop_hip_by_femurs(self, hip_reference_path, hip_segment_path):
        try:
            print(f"\n[START] Cropping CT hip based on CBCT hip reference.")
            print(f"  Reference (CBCT) path: {hip_reference_path}")
            print(f"  Segment (CT) path: {hip_segment_path}")
    
            hip_ref = sitk.ReadImage(hip_reference_path)
            spacing_cbct = hip_ref.GetSpacing()
            origin_cbct = hip_ref.GetOrigin()
            z_spacing_cbct = spacing_cbct[2]
    
            hip_ref_array = sitk.GetArrayFromImage(hip_ref)
            z_indices_ref = np.any(hip_ref_array, axis=(1, 2))
            if not np.any(z_indices_ref):
                print(f"  [WARNING] No non-zero slices found in CBCT hip!")
                return
            top_z_cbct_slice = int(np.max(np.argwhere(z_indices_ref)))
            print(f"  Top Z slice of CBCT hip: {top_z_cbct_slice}, spacing: {z_spacing_cbct}")
    
            # Compute top Z position in physical mm
            top_cbct_mm_z = origin_cbct[2] + top_z_cbct_slice * z_spacing_cbct
    
            # --- Load CT segmentation ---
            hip_seg = sitk.ReadImage(hip_segment_path)
            spacing_ct = hip_seg.GetSpacing()
            origin_ct = hip_seg.GetOrigin()
            z_spacing_ct = spacing_ct[2]
    
            hip_seg_array = sitk.GetArrayFromImage(hip_seg)
            z_dim_ct = hip_seg_array.shape[0]
    
            z_indices_ct = np.any(hip_seg_array, axis=(1, 2))
            if not np.any(z_indices_ct):
                print(f"  [WARNING] No non-zero slices found in CT hip!")
                return
    
            # Convert CBCT physical z to CT slice index
            crop_z_ct = int(np.floor((top_cbct_mm_z - origin_ct[2]) / z_spacing_ct))
            crop_z_clipped = np.clip(crop_z_ct, 0, z_dim_ct)
    
            print(f"  Cropping CT hip above slice {crop_z_clipped} (CT shape = {z_dim_ct})")
            is_femur = "femur" in hip_reference_path
            # if is_femur:
            #     if crop_z_clipped < z_dim_ct:
            #         hip_seg_array[:crop_z_clipped] = 0
            #     else:
            #         print(f"  [INFO] crop_z ({crop_z_clipped}) >= CT volume depth ({z_dim_ct}), skipping crop.")
            # else:
            if crop_z_clipped < z_dim_ct:
                hip_seg_array[crop_z_clipped:] = 0
            else:
                print(f"  [INFO] crop_z ({crop_z_clipped}) >= CT volume depth ({z_dim_ct}), skipping crop.")
    
            # Save the cropped image
            cropped = sitk.GetImageFromArray(hip_seg_array)
            cropped.CopyInformation(hip_seg)
            sitk.WriteImage(cropped, hip_segment_path)
            print(f"  [SUCCESS] Cropped CT hip saved to: {hip_segment_path}\n")
    
        except Exception as e:
            print(f"[ERROR] Cropping CT hip failed: {e}")
            import traceback
            traceback.print_exc()
    def get_colon_z_extent(self, colon_path):
        colon = sitk.ReadImage(colon_path)
        colon_array = sitk.GetArrayFromImage(colon)
        z_indices = np.any(colon_array, axis=(1, 2))
        if not np.any(z_indices):
            return None
        z_min = np.min(np.argwhere(z_indices))
        z_max = np.max(np.argwhere(z_indices))
        return z_min, z_max, colon
    
    def apply_z_crop_to_colon(self, colon_img, z_min, z_max, save_path):
        colon_array = sitk.GetArrayFromImage(colon_img)
        colon_array[:z_min] = 0
        colon_array[z_max+1:] = 0
        cropped = sitk.GetImageFromArray(colon_array)
        cropped.CopyInformation(colon_img)
        sitk.WriteImage(cropped, save_path)
                
    def crop_ct_femur_using_cbct(self, cbct_femur_path, ct_femur_path):
        try:
            print(f"\n[START] Cropping CT femur using CBCT femur reference.")
            print(f"  CBCT femur: {cbct_femur_path}")
            print(f"  CT femur:   {ct_femur_path}")
    
            # Load CBCT femur segmentation
            cbct_seg = sitk.ReadImage(cbct_femur_path)
            cbct_array = sitk.GetArrayFromImage(cbct_seg)
            z_spacing_cbct = cbct_seg.GetSpacing()[2]
            origin_cbct_z = cbct_seg.GetOrigin()[2]
    
            z_indices_cbct = np.any(cbct_array, axis=(1, 2))
            if not np.any(z_indices_cbct):
                print("  [WARNING] CBCT femur segment is empty.")
                return
    
            # Use BOTTOM slice of CBCT femur as reference
            bottom_cbct_slice = int(np.min(np.argwhere(z_indices_cbct)))
            bottom_cbct_mm = origin_cbct_z + bottom_cbct_slice * z_spacing_cbct
            print(f"  Bottom CBCT femur slice: {bottom_cbct_slice}, mm: {bottom_cbct_mm:.2f}")
    
            # Load CT femur segmentation
            ct_seg = sitk.ReadImage(ct_femur_path)
            ct_array = sitk.GetArrayFromImage(ct_seg)
            z_spacing_ct = ct_seg.GetSpacing()[2]
            origin_ct_z = ct_seg.GetOrigin()[2]
            z_dim_ct = ct_array.shape[0]
    
            # Convert CBCT femur bottom Z (mm) → CT slice index
            crop_z_ct = int(np.floor((bottom_cbct_mm - origin_ct_z) / z_spacing_ct))
            crop_z_clipped = np.clip(crop_z_ct, 0, z_dim_ct)
            print(f"  Crop below CT slice index: {crop_z_clipped}")
    
            # Remove everything BELOW the bottom of CBCT femur in CT
            if crop_z_clipped < z_dim_ct:
                ct_array[:crop_z_clipped] = 0
                print(f"  Cropped CT femur below slice {crop_z_clipped}")
            else:
                print("  [INFO] crop_z exceeds CT bounds, skipping crop.")
    
            # Save
            cropped = sitk.GetImageFromArray(ct_array)
            cropped.CopyInformation(ct_seg)
            sitk.WriteImage(cropped, ct_femur_path)
            print(f"  [DONE] Cropped CT femur saved to: {ct_femur_path}\n")
    
        except Exception as e:
            print(f"[ERROR] Cropping femur failed: {e}")
            import traceback
            traceback.print_exc()

