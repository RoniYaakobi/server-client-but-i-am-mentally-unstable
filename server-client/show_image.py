import tkinter as tk
from datetime import datetime


root = tk.Tk()

start = datetime.now()

with open(r"C:\Users\roniy\Downloads\testing.bmp", mode= "rb") as img:
    img.seek(18) # skip file herader and ignore bit map header size
    width_bytes = img.read(4) # get the bytes of the width
    height_bytes = img.read(4) # get the bytes of the height

    w = int.from_bytes(width_bytes, "little")
    h = int.from_bytes(height_bytes, "little", signed=True)

    # create the image object
    # expects positve values for height and width, start 0,0 at top left corner
    root.call('image', 'create', 'photo', 'myimg', '-width', w, '-height', abs(h)) # height is positive

    img.seek(54) # go to the start of the data we actually care about

    BGR_pixels = img.read() # rest of file is pixels

    pixels = bytearray(BGR_pixels) # use a more comfortable format

    #

    hex_table = [f"{i:02x}" for i in range(256)]

    rows = []
    row_bytes = w * 3
    padding = (4 - (row_bytes % 4)) % 4
    start1 = datetime.now()
    dtA = datetime.now() - datetime.now()
    for y in range(abs(h)):
        row_start = y * (row_bytes + padding)
        row = pixels[row_start:row_start+row_bytes]
        
        startA = datetime.now()
        hex_row = " ".join(
        f"#{hex_table[row[i+2]]}{hex_table[row[i+1]]}{hex_table[row[i]]} #{hex_table[row[i+5]]}{hex_table[row[i+4]]}{hex_table[row[i+3]]}"
        for i in range(0, len(row), 6)
    )
        endA = datetime.now()
        dtA += endA-startA
        rows.append(f"{{{hex_row}}}")
    print(dtA)
    end1 = datetime.now()
    print(end1-start1)

    pixel_string = " ".join(rows)
    start2 = datetime.now()
    root.call('myimg', 'put', pixel_string)
    end2 = datetime.now()
    print(end2-start2)
    


root.tk.call('label', '.lbl', '-image', 'myimg')
root.tk.call('pack', '.lbl')

end = datetime.now()

print(end-start)

root.mainloop()
