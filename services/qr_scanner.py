"""Webcam QR scanner. Capture and decoding run in a background thread; the UI polls the results."""

import sys
import threading
import time

import cv2

_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


class CameraError(Exception):
    pass


def _open_capture(index):
    cap = cv2.VideoCapture(index, _BACKEND)
    if not cap.isOpened():
        cap.release()
        return None
    ok, _ = cap.read()
    if not ok:
        cap.release()
        return None
    return cap


def list_cameras(max_index=5):
    """Indexes of the cameras that can be opened."""
    found = []
    for index in range(max_index):
        cap = _open_capture(index)
        if cap is not None:
            found.append(index)
            cap.release()
    return found


class QrScanner:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self._cap = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._frame = None
        self._decoded = []
        self._last_seen = 0.0  # monotonic time a QR was last detected (decoded or not)

    def start(self):
        self._cap = _open_capture(self.camera_index)
        if self._cap is None:
            raise CameraError(
                f"No camera available (camera {self.camera_index}). "
                "Connect a camera or choose another one in Settings."
            )
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="qr-scanner", daemon=True)
        self._thread.start()

    def _run(self):
        detector = cv2.QRCodeDetector()
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            try:
                text, points, _ = detector.detectAndDecode(frame)
            except cv2.error:
                text, points = "", None
            with self._lock:
                self._frame = frame
                if points is not None:
                    self._last_seen = time.monotonic()
                if text:
                    self._decoded.append(text)

    def get_frame(self):
        """Latest frame as RGB array (or None if there is no new one)."""
        with self._lock:
            frame, self._frame = self._frame, None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame is not None else None

    def pop_decoded(self):
        with self._lock:
            texts, self._decoded = self._decoded, []
        return texts

    @property
    def last_seen(self):
        with self._lock:
            return self._last_seen

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
