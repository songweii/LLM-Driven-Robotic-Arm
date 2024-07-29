from core.realsense2 import *
from core.wrap_xarm import xarm6
from core.calibrate import Calibration


robot = xarm6()  # robot
realcam = Realsense2()  # camera