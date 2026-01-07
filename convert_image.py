from custom_modules.GUI import *
from custom_modules.constants import MAX_PIXEL_LIMIT
from custom_modules.helpers import get_suffix
from PIL import Image
from pathlib import Path
import os

"""
some image conversion types require pre processing before conversion can be done 
eg jpeg and jpg for alpha
to do so, do pre processing for the image type by parsing the suffix then
deciding what to do before saving as new image extension
To do...
"""
Image.MAX_IMAGE_PIXELS = MAX_PIXEL_LIMIT

def convert_images(input_file_path : Path, output_file_path : Path, ext : str):
    if os.path.isfile(input_file_path):
        suffix = get_suffix(input_file_path)
        if suffix not in savable_exts:
            print(f"Error! Cannot convert file with extension: {suffix}")
            return
        image = Image.open(input_file_path)
        output_file_name = os.path.basename(input_file_path).split('.')[0] + f".{ext}"
        image.save(os.path.join(output_file_path, output_file_name))
    else:
        iter_dir = Path(input_file_path)
        for image_path in iter_dir.iterdir():
            try:
                suffix = get_suffix(image_path)
                if suffix in savable_exts:
                    image = Image.open(image_path)
                    output_file_name = os.path.basename(image_path).split('.')[0] + f".{ext}"
                    image.save(os.path.join(output_file_path, output_file_name))
                else:
                    print(f"Skipped {image_path}")
                    continue
            except Exception as e:
                print(f"ERROR! The following image has an error: {image_path}")
                print(f"Exception is {e}")
                
            

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