import cv2

print("Scanning for available camera streams on your PC...\n")

found_any = False
# Test default, DirectShow, and Media Foundation backends across indices 0-5
backends = [
    ("Default", None),
    ("DirectShow (CAP_DSHOW)", cv2.CAP_DSHOW),
    ("Media Foundation (CAP_MSMF)", cv2.CAP_MSMF)
]

for backend_name, backend_code in backends:
    for index in range(4):
        if backend_code is None:
            cap = cv2.VideoCapture(index)
        else:
            cap = cv2.VideoCapture(index, backend_code)
            
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"[SUCCESS] Found working camera! Backend: {backend_name} | Index: {index}")
                found_any = True
                cap.release()
                break
            cap.release()

if not found_any:
    print("[FAILED] No working camera streams detected.")
    print("Please check: Physical shutter switch, Windows Privacy Settings, or other active camera apps.")