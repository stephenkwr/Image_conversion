from tkinter import Tk, Label, Button, filedialog
import os
from pathlib import Path

def select_folders():
    result = {"inputfolder" : None, "outputfolder" : None}

    def pick_input():
        i = filedialog.askdirectory(title="Select input folder")
        if i: result["inputfolder"] = i
        input_btn.config(text=os.path.basename(i))

    def pick_output():
        o = filedialog.askdirectory(title="Select output folder")
        if o: result["inputfolder"] = o
        output_btn.config(text=os.path.basename(o))

    def finish():
        root.quit()

    root = Tk()
    root.title("Pick folders")
    root.geometry("520x160")
    root.resizable(False, False)

    Label(root, text="Input folder:").grid(row=0, column=0, padx=10, pady=8, sticky='e')
    input_btn = Button(root, text="Choose...", wdith=35, command=pick_input)
    input_btn.grid(row=0, column=1, pady=8)

    Label(root, text="Output folder:").grid(row=1, column=0, padx=10, pady=8, sticky='e')
    output_btn = Button(root, text="Choose...", wdith=35, command=pick_output)
    output_btn.grid(row=1, column=1, pady=8)

    Button(root, text="run", width=18, command=finish).grid(row=3, column=0, columnspan=2, pady=12)

    root.mainloop()
    root.destroy()
    return result

result = select_folders()

print(result)