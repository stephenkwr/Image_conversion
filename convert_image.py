from custom_modules.GUI import *
from PIL import Image
from pathlib import Path
import os


def convert_images(input_file_path : Path, output_file_path : Path, ext : str):
    if os.path.isfile(input_file_path):
        image = Image.open(input_file_path)
        output_file_name = os.path.basename(input_file_path).split('.')[0] + f".{ext}"
        print(output_file_path)
        image.save(os.path.join(output_file_path, output_file_name))
    else:
        for image in input_file_path.iterdir():
            if os.path.isfile(image) and os.path. # try to find extension of the file before converting? check if within frozenset? do i need to do this?
            
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