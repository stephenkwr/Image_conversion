from tkinter import Tk, Label, Button, filedialog, ttk, Radiobutton, StringVar
import os
from custom_modules.constants import image_exts, IMAGE_FILETYPES

options = frozenset({"single", "folder"})

def select_convert_single_or_folder():
    root = Tk()
    root.geometry("200x150")
    root.resizable(False, False)

    result = StringVar(value=iter(options))

    def finish():
        root.quit()

    for i, lang in enumerate(options, start=0):
        rb = Radiobutton(root, text=lang, variable=result, value=lang)
        rb.grid(row=i, column=0, padx=10, pady=8, sticky='e')

    Button(root, text="run", width=9, command=finish).grid(row=3, column=0, columnspan=1, pady=12, padx=8)

    root.mainloop()
    root.destroy()
    return result.get()

def select_photos():
    root = Tk()
    root.title("Select files")
    root.geometry("520x200")
    root.resizable(False, False)

    result = {"input" : None, "output" : None, "Extension" : None}

    def pick_input():
        i = filedialog.askopenfilename(title="select file to convert...", filetypes=IMAGE_FILETYPES)
        if i: result["input"] = i
        input_btn.config(text=os.path.basename(i))

    def pick_output_folder():
        o = filedialog.askdirectory(title="Select output folder...")
        if o: 
            result["output"] = o
        output_btn.config(text=os.path.basename(o))

    def finish():
        result["Extension"] = cb.get()
        root.quit()

    Label(root, text="Select photo to convert:").grid(row=0, column=0, padx=10, pady=8, sticky='e')
    input_btn = Button(root, text="Choose...", width=35, command=pick_input)
    input_btn.grid(row=0, column=1, pady=8)

    Label(root, text="Pick Output Folder").grid(row=1, column=0, padx=10, pady=8, sticky='e')
    output_btn = Button(root, text="Pick output folder", width=35, command=pick_output_folder)
    output_btn.grid(row=1, column=1, pady=8)

    Label(root, text="Select converted image type:").grid(row=2, column=0, padx=10, pady=8, sticky='e')
    cb = ttk.Combobox(root, values=sorted(image_exts), state="readonly", width=33)
    cb.grid(row=2, column=1, pady=8)
    cb.current(0)

    Button(root, text="Run", width=35, command=finish).grid(row=3, column=0, pady=12, columnspan=2)

    root.mainloop()
    root.destroy()
    return result

def select_folders():
    result = {"input" : None, "output" : None, "Extension" : None}

    def pick_input():
        i = filedialog.askdirectory(title="Select input folder")
        if i: result["input"] = i
        input_btn.config(text=os.path.basename(i))

    def pick_output():
        o = filedialog.askdirectory(title="Select output folder")
        if o: result["output"] = o
        output_btn.config(text=os.path.basename(o))
        
    def finish():
        result["Extension"] = cb.get()
        root.quit()

    root = Tk()
    root.title("Select folders")
    root.geometry("520x200")
    root.resizable(False, False)

    Label(root, text="Input folder:").grid(row=0, column=0, padx=10, pady=8, sticky='e')
    input_btn = Button(root, text="Choose...", width=35, command=pick_input)
    input_btn.grid(row=0, column=1, pady=8)

    Label(root, text="Output folder:").grid(row=1, column=0, padx=10, pady=8, sticky='e')
    output_btn = Button(root, text="Choose...", width=35, command=pick_output)
    output_btn.grid(row=1, column=1, pady=8)

    Label(root, text="Select converted image type:").grid(row=2, column=0, padx=10, pady=8, sticky='e')
    cb = ttk.Combobox(root, values=sorted(image_exts), state="readonly", width=33)
    cb.grid(row=2, column=1, pady=8)
    cb.current(0)

    Button(root, text="run", width=18, command=finish).grid(row=3, column=0, columnspan=2, pady=12)

    root.mainloop()
    root.destroy()
    return result


# result = select_convert_single_or_folder()
# print(result)

# if result == "folder":
#     result = select_folders()
# else:
#     result = select_photos()

# print(result)