from custom_modules.GUI import *
from PIL import *
from pathlib import Path
import os


def convert_images(input_file_path : Path, output_file_path : Path, ext : str):
    if os.path.isfile(input_file_path):
        print(os.path.basename(input_file_path))
        print("File")
    else:
        print(os.path.basename(input_file_path))
        print("folder")

    

    print(os.path.basename(output_file_path))
    print(ext)

def main():
    input_path = Path(__file__)
    output_path = Path(__file__)
    
    convert_option = select_convert_single_or_folder()

    if convert_option == "single":
        results = select_photos()
    else:
        results = select_folders()
    
    if results["input"] == None:
        print(f"Error! Require input path!")
        return
    input_path = results["input"]
    if results["output"] != None: 
        output_path = results["output"]
    
    convert_images(input_path, output_path, results["Extension"])

if __name__ == "__main__":
    main()