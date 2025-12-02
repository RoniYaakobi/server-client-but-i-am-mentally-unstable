import ctypes

BMP_FILE_HEADER_SIZE = 14
DIB_HEADER_SIZE = 40
BITS_PER_PIXEL = 24
PIXEL_OFFSET = BMP_FILE_HEADER_SIZE + DIB_HEADER_SIZE

SRCCOPY = 0x00CC0020

def int_to_bytes(x):
    return (x).to_bytes(4, 'little')

class take:
    def __init__(self):
        # Get references to the dlls 
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32

        # Get the device dimensions from the windows API
        self.width = self.user32.GetSystemMetrics(0)
        self.height = self.user32.GetSystemMetrics(1)

    def save_screenshot(self,path):
        # Prepare a context for the screen and memory for the screenshot
        hdc_screen = self.user32.GetDC(0)
        hdc_mem = self.gdi32.CreateCompatibleDC(hdc_screen)

        # Build a bitmap and inject the reference to the memory object
        hbitmap = self.gdi32.CreateCompatibleBitmap(hdc_screen, self.width, self.height)
        self.gdi32.SelectObject(hdc_mem, hbitmap)

        # Fast copy all the screenshot into the memory for the bitmap
        self.gdi32.BitBlt(hdc_mem, 0, 0, self.width, self.height, hdc_screen, 0, 0, SRCCOPY)

        # Make a c struct which contains two fields, one 40 bytes, the other 0
        class BITMAPINFO(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", ctypes.c_byte * DIB_HEADER_SIZE),
                ("bmiColors", ctypes.c_byte * 0)
            ]

        # Make the struct and populate the bit map header with fields
        bmp_info = BITMAPINFO()
        bmp_info.bmiHeader[0:4] = int_to_bytes(40)  # length of header
        bmp_info.bmiHeader[4:8] = int_to_bytes(self.width)  # width of picture

        # Height of picture, negative to make the bitmap be read from up down and not down up
        bmp_info.bmiHeader[8:12] = (-self.height).to_bytes(4, 'little', signed=True)  

        # A field that is not used anymore
        bmp_info.bmiHeader[12:14] = (1).to_bytes(2, 'little')

        # Size of pixel, 3 bytes (RGB)
        bmp_info.bmiHeader[14:16] = (BITS_PER_PIXEL).to_bytes(2, 'little')


        buffer = ctypes.create_string_buffer(self.height * self.width * 3)

        self.gdi32.GetDIBits(hdc_mem, hbitmap, 0, self.height, buffer, ctypes.byref(bmp_info), 0) # Moves the data into the buffer

        self.write_bitmap_format(self.width, self.height, buffer, path)

        self.gdi32.DeleteObject(hbitmap) # Free memory because c doesn't know garbage collector
        self.gdi32.DeleteDC(hdc_mem) # Free memory because c doesn't know garbage collector
        self.user32.ReleaseDC(0, hdc_screen) # Free memory because c doesn't know garbage collector


    def write_bitmap_format(self, width, height, buffer, path):
        with open(path, mode = "wb") as screenshot:
            # File header
            screenshot.write(b"BM") # BM header

            row_bytes = width * 3
            padding = (4 - (row_bytes % 4)) % 4
            pixel_data_size = (row_bytes + padding) * height
            file_size = BMP_FILE_HEADER_SIZE + DIB_HEADER_SIZE + pixel_data_size
            size_bytes = file_size.to_bytes(4, 'little')
            screenshot.write(size_bytes) # Size of file

            zero = int_to_bytes(0)
            screenshot.write(zero) # useless empty bytes
            screenshot.write(int_to_bytes(PIXEL_OFFSET)) # offset of data

            # BMP header

            screenshot.write(int_to_bytes(DIB_HEADER_SIZE)) # BMP header size
            screenshot.write(int_to_bytes(width)) # width 
            screenshot.write((-height).to_bytes(4, 'little',signed = True)) # height in a format to be read top bottom
            screenshot.write((1).to_bytes(2, 'little')) # planes don't matter
            screenshot.write((BITS_PER_PIXEL).to_bytes(2, 'little')) # 24 bits = 3 bytes = RGB
            screenshot.write(zero) # no compression
            screenshot.write(zero) # image size doesn't matter in compression
            screenshot.write(zero) # pixels/meter doesn't matter for now
            screenshot.write(zero) # ''
            screenshot.write(zero) # true-color is on
            screenshot.write(zero) # no important colors

            # Write all data with the proper padding
            for y in range(height):
                row_start = y * width * 3
                row_end = row_start + width * 3
                screenshot.write(buffer[row_start:row_end]) # write actual bytes
                screenshot.write(b'\x00' * padding)  # pad to 4 bytes


take().save_screenshot(r"C:\Users\roniy\server-client-but-i-am-mentally-unstable\sussy.bmp")