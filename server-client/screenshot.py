import ctypes

BMP_FILE_HEADER_SIZE = 14
DIB_HEADER_SIZE = 40
BITS_PER_PIXEL = 24
PIXEL_OFFSET = BMP_FILE_HEADER_SIZE + DIB_HEADER_SIZE


USER32 = ctypes.windll.user32
GDI32 = ctypes.windll.gdi32
SRCCOPY = 0x00CC0020

def int_to_bytes(x):
    return (x).to_bytes(4, 'little')

class ScreenCapture:
    hdc_screen = USER32.GetDC(0)
    WIDTH = GDI32.GetDeviceCaps(hdc_screen, 118)  # HORZRES
    HEIGHT = GDI32.GetDeviceCaps(hdc_screen, 117) # VERTRES
    USER32.ReleaseDC(0, hdc_screen)

    @staticmethod
    def save_screenshot(path):
        # Prepare a context for the screen and memory for the screenshot
        hdc_screen = USER32.GetDC(0)
        hdc_mem = GDI32.CreateCompatibleDC(hdc_screen)

        # Build a bitmap and inject the reference to the memory object
        hbitmap = GDI32.CreateCompatibleBitmap(hdc_screen, ScreenCapture.WIDTH, ScreenCapture.HEIGHT)
        GDI32.SelectObject(hdc_mem, hbitmap)

        # Fast copy all the screenshot into the memory for the bitmap
        GDI32.BitBlt(hdc_mem, 0, 0, ScreenCapture.WIDTH, ScreenCapture.HEIGHT, hdc_screen, 0, 0, SRCCOPY)

        # Make a c struct which contains two fields, one 40 bytes, the other 0
        class BITMAPINFO(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", ctypes.c_byte * DIB_HEADER_SIZE),
                ("bmiColors", ctypes.c_byte * 0)
            ]

        # Make the struct and populate the bit map header with fields
        bmp_info = BITMAPINFO()
        bmp_info.bmiHeader[0:4] = int_to_bytes(40)  # length of header
        bmp_info.bmiHeader[4:8] = int_to_bytes(ScreenCapture.WIDTH)  # width of picture

        # Height of picture, negative to make the bitmap be read from up down and not down up
        bmp_info.bmiHeader[8:12] = (-ScreenCapture.HEIGHT).to_bytes(4, 'little', signed=True)  

        # A field that is not used anymore
        bmp_info.bmiHeader[12:14] = (1).to_bytes(2, 'little')

        # Size of pixel, 3 bytes (RGB)
        bmp_info.bmiHeader[14:16] = (BITS_PER_PIXEL).to_bytes(2, 'little')


        buffer = ctypes.create_string_buffer(ScreenCapture.HEIGHT * ScreenCapture.WIDTH * 3)

        GDI32.GetDIBits(hdc_mem, hbitmap, 0, ScreenCapture.HEIGHT, buffer, ctypes.byref(bmp_info), 0) # Moves the data into the buffer

        ScreenCapture.write_bitmap_format(buffer, path)

        GDI32.DeleteObject(hbitmap) # Free memory because c doesn't know garbage collector
        GDI32.DeleteDC(hdc_mem) # Free memory because c doesn't know garbage collector
        USER32.ReleaseDC(0, hdc_screen) # Free memory because c doesn't know garbage collector

    @staticmethod
    def write_bitmap_format(buffer, path):
        with open(path, mode = "wb") as screenshot:
            # File header
            screenshot.write(b"BM") # BM header

            row_bytes = ScreenCapture.WIDTH * 3
            padding = (4 - (row_bytes % 4)) % 4
            pixel_data_size = (row_bytes + padding) * ScreenCapture.HEIGHT
            file_size = BMP_FILE_HEADER_SIZE + DIB_HEADER_SIZE + pixel_data_size
            size_bytes = file_size.to_bytes(4, 'little')
            screenshot.write(size_bytes) # Size of file

            zero = int_to_bytes(0)
            screenshot.write(zero) # useless empty bytes
            screenshot.write(int_to_bytes(PIXEL_OFFSET)) # offset of data

            # BMP header

            screenshot.write(int_to_bytes(DIB_HEADER_SIZE)) # BMP header size
            screenshot.write(int_to_bytes(ScreenCapture.WIDTH)) # width 
            screenshot.write((-ScreenCapture.HEIGHT).to_bytes(4, 'little',signed = True)) # height in a format to be read top bottom
            screenshot.write((1).to_bytes(2, 'little')) # planes don't matter
            screenshot.write((BITS_PER_PIXEL).to_bytes(2, 'little')) # 24 bits = 3 bytes = RGB
            screenshot.write(zero) # no compression
            screenshot.write(zero) # image size doesn't matter in compression
            screenshot.write(zero) # pixels/meter doesn't matter for now
            screenshot.write(zero) # ''
            screenshot.write(zero) # true-color is on
            screenshot.write(zero) # no important colors

            # Write all data with the proper padding
            for y in range(ScreenCapture.HEIGHT):
                row_start = y * ScreenCapture.WIDTH * 3
                row_end = row_start + ScreenCapture.WIDTH * 3
                screenshot.write(buffer[row_start:row_end]) # write actual bytes
                screenshot.write(b'\x00' * padding)  # pad to 4 bytes

if __name__ == "__main__":
    ScreenCapture.save_screenshot(r"C:\Users\roniy\Downloads\testing.bmp")