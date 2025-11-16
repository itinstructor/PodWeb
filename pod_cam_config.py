# ---------------------------------------------------------------------------
# CAMERA CONFIGURATION
# ---------------------------------------------------------------------------
# These values describe where the upstream Raspberry Pi (or server) streams live.
# If the Pi's IP changes on the network, update DEFAULT_STREAM_HOST.
DEFAULT_STREAM_HOST = "10.0.0.6"
DEFAULT_STREAM_PORT = 8000

# Paths exposed by the Raspberry Pi streaming script:
#   /stream0.mjpg  -> physical camera index 0 (Pod)
#   /stream1.mjpg  -> physical camera index 2 (plants) mapped by your Pi script
DEFAULT_STREAM_PATH_0 = "/stream0.mjpg"  # Martian POD
# Removed secondary stream (previously /stream1.mjpg) now single camera setup

