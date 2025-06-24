import subprocess

class Plastimatch:
    def __init__(self) -> None:
        pass

    def convert(self, input_arg, input_path, output_arg, output_path):
        command = [
            "plastimatch", "convert",
            f"--{input_arg}", input_path,
            f"--{output_arg}", output_path
        ]
        print(f"Running command: {command}")

        try:
            subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            print("Plastimatch convert completed successfully.")
        except Exception as e:
            print(f"Error: Plastimatch convert failed with error: {e}")


    def pw_linear_transform(self, input_path, output_path, use_identity=False):
        if use_identity:
            command = [
                "plastimatch", "adjust",
                "--input", input_path,
                "--linear", "0,1",
                "--output", f"{output_path}.nrrd"
            ]
        else:
            command = [
                "plastimatch", "adjust",
                "--input", input_path,
                "--pw-linear", "7, -981, 142, -895, 560, -112, 605, -97, 628, -90, 630, 38, 665, 55, 679, 96, 797, 255, 1072, 290, 1345, 902",
                "--output", f"{output_path}.nrrd"
            ]
    
        print(f"Running command: {command}")
        try:
            subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            print("Plastimatch adjustment completed successfully.")
        except Exception as e:
            print(f"Error: Plastimatch adjustment failed with error: {e}")


    def dmap(self, input_path, output_path):
        command = [
            "plastimatch", "dmap",
            "--input", input_path,
            "--absolute-distance",
            "--output", output_path
        ]
        print(f"Running command: {command}")
        try:
            subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            print("Plastimatch dmap calculation completed successfully.")
        except Exception as e:
            print(f"Error: Plastimatch dmap calculation with error: {e}")

    def register(self, params_filepath):
        command = ["plastimatch", params_filepath]
        print(f"Running command: {command}")
        try:
            subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            print("Plastimatch register completed successfully.")
        except Exception as e:
            print(f"Error: Plastimatch register failed with error: {e}")
            
    def warp(self, input, output_cmd, output, vf):
        command = [
            "plastimatch", "warp",
            "--input", input,
            f"--{output_cmd}", output,
            "--xf", vf
        ]
        print(f"Running command: {command}")
        try:
            subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            print("Plastimatch warp completed successfully.")
        except Exception as e:
            print(f"Error: Plastimatch warp failed with error: {e}")
            
    def dice(self, segment, warp):
        result = None
        command = [
            "plastimatch", "dice",
            "--all", segment, warp
        ]
        print(f"Running command: {command}")
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            print("Plastimatch dice completed successfully.")
        except Exception as e:
            print(f"Error: Plastimatch dice failed with error: {e}")
        
        return result
