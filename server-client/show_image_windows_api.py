import ctypes
from ctypes import wintypes
import logging
import threading, socket
import math, time
from ftp_protocol import FTP_FINISH
import tcp_by_size
from tcp_by_size import recv_by_size, send_with_size

window_map = {}

wintypes.HCURSOR = wintypes.HANDLE

if ctypes.sizeof(ctypes.c_void_p) == 8:  
    wintypes.LRESULT = ctypes.c_int64
    wintypes.WPARAM = ctypes.c_uint64
    wintypes.LPARAM = ctypes.c_int64
else:
    wintypes.LRESULT = ctypes.c_long
    wintypes.WPARAM = ctypes.c_uint
    wintypes.LPARAM = ctypes.c_long


USER32 = ctypes.windll.user32
GDI32 = ctypes.windll.gdi32
KERNEL32 = ctypes.windll.kernel32

win = USER32.GetDesktopWindow()
dpi = USER32.GetDpiForWindow(win)
SCALE_FACTOR = dpi / 96  # 96 DPI is 100%

GDI32.SetStretchBltMode.argtypes = [wintypes.HANDLE, wintypes.INT]
GDI32.SetStretchBltMode.restype = wintypes.BOOL



SRCCOPY = 0x00CC0020

DIB_HEADER_SIZE = 40

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 1),
    ]

class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint_left", wintypes.LONG),
        ("rcPaint_top", wintypes.LONG),
        ("rcPaint_right", wintypes.LONG),
        ("rcPaint_bottom", wintypes.LONG),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]

def py_wndproc(hwnd, msg, wparam, lparam):
    self_obj = window_map.get(hwnd)
    logging.info(f"Window Proc called: hwnd={hwnd}, msg={msg}, wparam={wparam}, lparam={lparam}")
    if msg == 0x0002:  # WM_DESTROY
        logging.info("WM_DESTROY received, posting quit message")
        if self_obj:
            self_obj.DONE = True  # Signal threads to stop
        USER32.PostQuitMessage(0)
        return 0
    elif msg == 0x000F:  # WM_PAINT
        
        logging.info("WM_PAINT received, performing BitBlt")
        USER32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
        USER32.BeginPaint.restype = wintypes.HDC
        USER32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
        USER32.EndPaint.restype = wintypes.BOOL
        ps = PAINTSTRUCT()
        hdc = USER32.BeginPaint(hwnd, ctypes.byref(ps))

        GDI32.SetStretchBltMode(hdc, 4)  # HALFTONE

        
        if self_obj and getattr(self_obj, "_hdc_mem", None):
            with self_obj.bitmap_lock:
                res = GDI32.StretchBlt(
                    hdc,          # destination DC
                    0, 0, math.ceil(self_obj._w / SCALE_FACTOR), math.ceil(abs(self_obj._h) / SCALE_FACTOR),  # destination rectangle (scaled size)
                    self_obj._hdc_mem,   # source DC
                    0, 0, self_obj._w, abs(self_obj._h),  # source rectangle (original size)
                    SRCCOPY
                )
                logging.info(f"BitBlt returned: {res}")
            

        else:
            logging.warning("Memory DC not ready, skipping BitBlt")

        logging.info(f"EndPaint")
        x = USER32.EndPaint(hwnd, ctypes.byref(ps))
        logging.info(f"EndPaint: {x}")
        
        return 0
    
    
    USER32.DefWindowProcW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
    USER32.DefWindowProcW.restype = wintypes.LRESULT

    x = USER32.DefWindowProcW(hwnd, msg, wparam, lparam)
    logging.info(f"wndproc: {x}")
    return x

class ViewBitMap:
    def __init__(self):
        logging.info("Initializing ViewBitMap")
        self.hInstance = KERNEL32.GetModuleHandleW(None)
        self.classname_w = ctypes.c_wchar_p("MyWindowClass")
        self.windowname_w = ctypes.c_wchar_p("My Window")
        self._h = 0
        self._w = 0
        self._dc = 0
        self._hdc_mem = 0
        self.path = r"C:\Users\roniy\Downloads\testing.bmp"
        self.define_window_class()

    def show_map(self):
        USER32.ShowWindow(self._hwnd, 1)
        USER32.UpdateWindow(self._hwnd)
        self.handle_message()

    def define_window_class(self):
        logging.info("Defining window class")
        WNDPROC = ctypes.WINFUNCTYPE(wintypes.LRESULT,
                             wintypes.HWND,
                             wintypes.UINT,
                             wintypes.WPARAM,
                             wintypes.LPARAM)

        self._wndproc = WNDPROC(py_wndproc)
        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", ctypes.c_uint),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)
            ]


        IDC_ARROW_CURSOR = 32512

        wc = WNDCLASS()
        wc.style = 0
        wc.lpfnWndProc = self._wndproc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = self.hInstance
        wc.hIcon = USER32.LoadIconW(None, 1)  # IDI_APPLICATION
        wc.hCursor = USER32.LoadCursorW(None, IDC_ARROW_CURSOR)
        wc.hbrBackground = GDI32.GetStockObject(0)  # WHITE_BRUSH
        wc.lpszMenuName = None
        wc.lpszClassName = self.classname_w



        self._atom = USER32.RegisterClassW(ctypes.byref(wc))
        if not self._atom:
            raise ctypes.WinError()
        logging.info(f"Window class registered, atom={self._atom}")

    def open_window(self):
        logging.info("Creating window")
        WS_OVERLAPPEDWINDOW = 0xcf0000

        SIZE_X = self._w
        SIZE_Y = abs(self._h)
        POS_X = 0
        POS_Y = 0

        WS_POPUP = 0x80000000
        WS_VISIBLE = 0x10000000

        self._hwnd = USER32.CreateWindowExW(
            0,
            self.classname_w,
            self.windowname_w,
            WS_POPUP | WS_VISIBLE,
            POS_X, POS_Y, SIZE_X, SIZE_Y,
            None, None, self.hInstance, None
        )

        if not self._hwnd:
            raise ctypes.WinError()
        
        window_map[self._hwnd] = self
        
        logging.info(f"Window created, hwnd={self._hwnd}")

    def initialize_bitmap_info(self):
        logging.info(f"Parsing bitmap info from {self.path}")
        self._bmp_info = BITMAPINFO()

        self._bmp_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)# length of header
        self._bmp_info.bmiHeader.biWidth = self._w  # width of picture

        # Height of picture, negative to make the bitmap be read from up down and not down up
        self._bmp_info.bmiHeader.biHeight = -abs(self._h)  

        # A field that is not used anymore
        self._bmp_info.bmiHeader.biPlanes = 1

        # Size of pixel, 3 bytes (RGB)
        self._bmp_info.bmiHeader.biBitCount = 24
        self._bmp_info.bmiHeader.biCompression = 0        # BI_RGB
        self._bmp_info.bmiHeader.biSizeImage = 0          # for BI_RGB can be 0
        self._bmp_info.bmiHeader.biXPelsPerMeter = 0
        self._bmp_info.bmiHeader.biYPelsPerMeter = 0
        self._bmp_info.bmiHeader.biClrUsed = 0
        self._bmp_info.bmiHeader.biClrImportant = 0
    
    def create_dib_section(self):
        logging.info("Creating DIB section")
        USER32.GetDC.argtypes = [wintypes.HWND]
        
        USER32.GetDC.restype  = wintypes.HDC

        self._dc = USER32.GetDC(self._hwnd)

        logging.info(f"Window DC obtained: {self._dc}")

        GDI32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        
        GDI32.CreateCompatibleDC.restype = ctypes.POINTER(ctypes.c_void_p)

        print(self._w,self._h)

        GDI32.CreateDIBSection.argtypes = [
            wintypes.HDC,
            BITMAPINFO,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p),
            wintypes.HANDLE,
            wintypes.DWORD
        ]

        DIB_RGB_COLORS = 1

        self._ppvBits = ctypes.c_void_p()

        GDI32.CreateDIBSection.restype  = wintypes.HBITMAP

        self._dibSection = GDI32.CreateDIBSection(
            self._dc,
            self._bmp_info,
            DIB_RGB_COLORS,
            ctypes.byref(self._ppvBits),
            ctypes.c_void_p(0),
            wintypes.DWORD(0)
        )

        if not self._dibSection:
            raise ctypes.WinError()
        logging.info(f"DIBSection created: hBitmap={self._dibSection}, ppvBits={self._ppvBits.value}")

        
        self._hdc_mem = GDI32.CreateCompatibleDC(self._dc)

        logging.info(f"Memory DC created: {self._hdc_mem}")
        
        GDI32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        GDI32.SelectObject.restype = wintypes.HGDIOBJ
        
        GDI32.SelectObject(self._hdc_mem, self._dibSection)
        logging.info("DIBSection selected into memory DC")


    def handle_message(self):
        logging.info("Entering message loop")
        msg = wintypes.MSG()
        while USER32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            USER32.TranslateMessage(ctypes.byref(msg))
            USER32.DispatchMessageW(ctypes.byref(msg))
            
class ViewBitMapStream(ViewBitMap):
    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self.get_bitmap_info()
        self.bitmap_lock = threading.Lock()  # Shared lock for bitmap access
        self.open_window()
        self.create_dib_section()
        
        self.DONE = False
        
        self.get_bitmap()

        self.update = threading.Thread(target=self.update_routine, daemon=True)
        self.update.start()

        self.show_map()  # Blocks here until window closes

        # Signal thread to stop and wait for it
        self.DONE = True
        self.update.join(timeout=2.0)  # Wait max 2 seconds
    
    def get_bitmap_info(self):
        self._w = int.from_bytes(recv_by_size(self.sock), "little") 
        self._h = int.from_bytes(recv_by_size(self.sock), "little", signed=True) 
        self.initialize_bitmap_info()

    def update_routine(self):
        while not self.DONE:
            time.sleep(0.02)
            try:
                send_with_size(self.sock, "show me")
                tcp_by_size.TCP_DEBUG = False
                with self.bitmap_lock:  # Protect bitmap access
                    if not self.DONE:  # Double-check we're not shutting down
                        self.update_bitmap()
                tcp_by_size.TCP_DEBUG = True
            except Exception as e:
                logging.error(f"Error in update routine: {e}")
                break

    def update_bitmap(self):
        # Don't call this if window is being destroyed
        if self.DONE:
            return
            
        # ignore metadata
        _ = int.from_bytes(recv_by_size(self.sock), "little")
        _ = int.from_bytes(recv_by_size(self.sock), "little", signed=True)

        row_bytes = self._w * 3
        height = abs(self._h)

        pixel_ptr = self._ppvBits.value
        offset = 0
        
        pixel_array = (ctypes.c_ubyte * (row_bytes * height)).from_address(pixel_ptr)

        chunk = recv_by_size(self.sock)
        while chunk != FTP_FINISH:
            if chunk != b'':
                length = len(chunk)
                pixel_array[offset : offset + length] = chunk
                offset += length
            chunk = recv_by_size(self.sock)

        # Only invalidate if window still exists
        if not self.DONE and self._hwnd:
            USER32.InvalidateRect(self._hwnd, None, False)  # Changed True to False

    def get_bitmap(self):
        row_bytes = self._w * 3
        height = abs(self._h)
        pixel_ptr = self._ppvBits.value
        offset = 0
        
        pixel_array = (ctypes.c_ubyte * (row_bytes * height)).from_address(pixel_ptr)

        with self.bitmap_lock:  # Use the shared lock
            chunk = recv_by_size(self.sock)
            while chunk != FTP_FINISH:
                if chunk != b'':
                    length = len(chunk)
                    pixel_array[offset : offset + length] = chunk
                    offset += length
                chunk = recv_by_size(self.sock)

                

class ViewBitMapFile(ViewBitMap):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.parse_as_bitmap_info()
        self.open_window()
        self.create_dib_section()
        self.get_bitmap_pixels()
        self.show_map()

    def parse_as_bitmap_info(self):
        with open(self.path, mode = "rb") as img:
            img.seek(18) # skip file herader and ignore bit map header size
            width_bytes = img.read(4) # get the bytes of the width
            height_bytes = img.read(4) # get the bytes of the height

            self._w = int.from_bytes(width_bytes, "little")
            self._h = int.from_bytes(height_bytes, "little", signed=True)
            logging.info(f"Bitmap dimensions: width={self._w}, height={self._h}")

        self.initialize_bitmap_info()

    def get_bitmap_pixels(self):
        logging.info("Loading bitmap pixels into DIBSection")
        row_bytes = self._w * 3
        padding = (4 - (row_bytes % 4)) % 4
        height = abs(self._h)

        pixel_ptr = self._ppvBits.value  # address of raw pixel memory
        if not pixel_ptr:
            raise RuntimeError("DIBSection pointer is NULL")
        
        # Create contiguous pixel array for DIBSection
        pixel_array = (ctypes.c_ubyte * (row_bytes * height)).from_address(pixel_ptr)

        with open(self.path, "rb") as img:
            img.seek(54)  # skip BMP header
            for y in range(height):
                # Read the actual pixel bytes
                row_data = img.read(row_bytes)
                # Skip the padding bytes in the file
                img.read(padding)

                # Determine destination row in DIBSection memory
                if self._bmp_info.bmiHeader.biHeight > 0:  # bottom-up BMP
                    dest_row = (height - 1 - y) * row_bytes
                else:  # top-down BMP
                    dest_row = y * row_bytes

                # Copy row_data into memory
                pixel_array[dest_row:dest_row + row_bytes] = row_data
        logging.info("Bitmap pixels loaded successfully")
