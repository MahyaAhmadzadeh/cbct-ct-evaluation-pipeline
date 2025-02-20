import os
from evaluation.config import EvaluationConfig
from evaluation.utils import Utils

def create_params_txt(patient_dir, filename, configs, segements=[]):
    
    utils = Utils(configs)
    patient_number = utils.get_patient_number(patient_dir)
    # affine_transform_txt = os.path.join(patient_dir, f"{patient_number}-{configs.AFFINE_TRANSFORM_FILENAME}")
    params_txt = os.path.join(patient_dir, configs.REGISTER_PARAMS_DIR, f"{filename}.txt")
    img_out = os.path.join(patient_dir, configs.REGISTERED_VOLUMES_DIR, f"{filename}.nrrd")
    vf_out = os.path.join(patient_dir, configs.VF_VOLUMES_DIR, f"{configs.VF_PREFIX}{filename}.nrrd")
    
    ct_path = os.path.join(patient_dir, configs.CT_DIR)
    cbct_path = os.path.join(patient_dir, configs.CBCT_DIR)
    total_segements = [{
            "fixed_file": ct_path,
            "moving_file": cbct_path
        }]
    total_segements = total_segements + segements

    stage_params = f"""
xform=bspline
impl=plastimatch
grid_spac=100 100 100
curvature_penalty=100
res=6 6 2
flavor=p

[STAGE]
grid_spac=80 80 80
curvature_penalty=10
res=4 4 1

[STAGE]
grid_spac=60 60 60
curvature_penalty=10
res=3 3 1
"""

    global_params = "[GLOBAL]\n"
    for i, filepath in enumerate(total_segements):
        global_params += f"fixed[{i}]={filepath['fixed_file']}\nmoving[{i}]={filepath['moving_file']}\n\n"
    
    global_params += f"""default_value=-1000
img_out={img_out}
vf_out={vf_out}\n\n"""
#xform_in={affine_transform_txt}\n\n"""
    
    metric_params = "[STAGE]\n"
    for i in range(len(total_segements)):
        metric_params += f"metric[{i}]=mse\n" if i==0 else f"metric[{i}]=pd\n"

    metric_params += "\n"

    for i in range(len(total_segements)):
        metric_params += f"metric_lambda[{i}]=1\n" if i==0 else f"metric_lambda[{i}]={configs.LAMBDA}\n"
    
    try:
        dir_name = os.path.dirname(params_txt)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        file = open(params_txt, 'w')
        file.write(global_params + metric_params + stage_params)
        file.close()
        print(f"CREATED: {params_txt}")
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False