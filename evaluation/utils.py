import re
import os
import shutil
import csv
import numpy as np

class Utils:

    def __init__(self, configs) -> None:
        self.configs = configs       
 
    def get_class_name(self, path) -> str:
        if self.configs.TS_PROSTATE_CLASS in path:
            return "TS_" + self.configs.TS_PROSTATE_CLASS 
        elif self.configs.TS_BLADDER_CLASS in path:
            return "TS_" + self.configs.TS_BLADDER_CLASS 
        elif self.configs.GT_BLADDER_CLASS in path:
            return "GT_" + self.configs.GT_BLADDER_CLASS 
        elif self.configs.GT_PROSTATE_CLASS in path:
            return "GT_" + self.configs.GT_PROSTATE_CLASS 
        elif self.configs.GT_RECTUM_CLASS in path:
            return "GT_" + self.configs.GT_RECTUM_CLASS
        else:
            return None

    def get_patient_number(self, patient_dir) -> str:
        return re.search(r"(?<=Pelvic-Ref-)\d+", patient_dir)[0]

    def get_roi_subset(self, patient_dir):
        patient_number = self.get_patient_number(patient_dir)
        roi_subset = self.configs.TS_male_roi_subset if patient_number in self.configs.patients_with_GT else self.configs.TS_female_roi_subset
        return patient_number, roi_subset

    def replace_or_skip(self, dir, force) -> bool:
        if force and os.path.exists(dir):
            shutil.rmtree(dir)
        if os.path.exists(dir):
            print("skipping warps creation")
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