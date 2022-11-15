import numpy as np
from dataclasses import dataclass
import matplotlib
from matplotlib.transforms import Affine2D
from matplotlib.patches import Wedge
from matplotlib.collections import PatchCollection
import math


@dataclass
class Para:
    # dim
    EGO_DIM: int = 6
    GOAL_DIM: int = 3
    N = 20

    # reward hparam
    scale_devi_p: float = 0.2
    scale_devi_v: float = 0.05
    scale_devi_phi: float = 0.8
    scale_punish_yaw_rate: float = 0.02  # 0.1
    scale_punish_steer: float = 0.2  # 1
    scale_punish_a_x: float = 0.02  # 0.1

    # action scale factor
    ACC_SCALE: float = 3.0
    ACC_SHIFT: float = 1.0
    STEER_SCALE: float = 0.3
    STEER_SHIFT: float = 0

    # done
    POS_TOLERANCE: float = 10
    ANGLE_TOLERANCE: float = 60.0

    # ego shape
    L: float = 4.8
    W: float = 2.0

    # goal
    GOAL_X_LOW: float = -40.
    GOAL_X_UP: float = 40.
    GOAL_Y_LOW: float = 40.
    GOAL_Y_UP: float = 60.
    GOAL_PHI_LOW: float = 0.
    GOAL_PHI_UP: float = 180.

    # ref path
    METER_POINT_NUM: int = 30
    START_LENGTH: float = 5.
    END_LENGTH: float = 5.

    # initial obs noise
    MU_X: float = 0
    SIGMA_X: float = 1
    MU_Y: float = 0
    SIGMA_Y: float = 1
    MU_PHI: float = 0
    SIGMA_PHI: float = 5

    # simulation settings
    FREQUENCY: float = 10


def cal_eu_dist(x1, y1, x2, y2):
    return np.sqrt(np.square(x1 - x2) + np.square(y1 - y2))


def action_denormalize(action_norm):
    action = np.clip(action_norm, -1.05, 1.05)
    steer_norm, a_x_norm = action[0], action[1]
    scaled_steer = Para.STEER_SCALE * steer_norm - Para.STEER_SHIFT
    scaled_acc = Para.ACC_SCALE * a_x_norm - Para.ACC_SHIFT
    scaled_action = np.array([scaled_steer, scaled_acc], dtype=np.float32)
    return scaled_action


def draw_rotate_rec(x, y, a, l, w):
    return matplotlib.patches.Rectangle((-l / 2 + x, -w / 2 + y),
                                        width=l, height=w,
                                        fill=False,
                                        facecolor=None,
                                        edgecolor='k',
                                        linewidth=1.0,
                                        transform=Affine2D().rotate_deg_around(*(x, y),
                                                                               a))


def rotate_coordination(orig_x, orig_y, orig_d, coordi_rotate_d):
    """
    :param orig_x: original x
    :param orig_y: original y
    :param orig_d: original degree
    :param coordi_rotate_d: coordination rotation d, positive if anti-clockwise, unit: deg
    :return:
    transformed_x, transformed_y, transformed_d(range:(-180 deg, 180 deg])
    """

    coordi_rotate_d_in_rad = coordi_rotate_d * math.pi / 180
    transformed_x = orig_x * math.cos(coordi_rotate_d_in_rad) + orig_y * math.sin(coordi_rotate_d_in_rad)
    transformed_y = -orig_x * math.sin(coordi_rotate_d_in_rad) + orig_y * math.cos(coordi_rotate_d_in_rad)
    transformed_d = orig_d - coordi_rotate_d
    # if transformed_d > 180:
    #     while transformed_d > 180:
    #         transformed_d = transformed_d - 360
    # elif transformed_d <= -180:
    #     while transformed_d <= -180:
    #         transformed_d = transformed_d + 360
    # else:
    #     transformed_d = transformed_d
    return transformed_x, transformed_y, transformed_d


def shift_coordination(orig_x, orig_y, coordi_shift_x, coordi_shift_y):
    """
    :param orig_x: original x
    :param orig_y: original y
    :param coordi_shift_x: coordi_shift_x along x axis
    :param coordi_shift_y: coordi_shift_y along y axis
    :return: shifted_x, shifted_y
    """
    shifted_x = orig_x - coordi_shift_x
    shifted_y = orig_y - coordi_shift_y
    return shifted_x, shifted_y


def rotate_and_shift_coordination(orig_x, orig_y, orig_d, coordi_shift_x, coordi_shift_y, coordi_rotate_d):
    shift_x, shift_y, transformed_d \
        = rotate_coordination(orig_x, orig_y, orig_d, coordi_rotate_d)
    transformed_x, transformed_y = shift_coordination(shift_x, shift_y, coordi_shift_x, coordi_shift_y)

    return transformed_x, transformed_y, transformed_d


def shift_and_rotate_coordination(orig_x, orig_y, orig_d, coordi_shift_x, coordi_shift_y, coordi_rotate_d):
    shift_x, shift_y = shift_coordination(orig_x, orig_y, coordi_shift_x, coordi_shift_y)
    transformed_x, transformed_y, transformed_d \
        = rotate_coordination(shift_x, shift_y, orig_d, coordi_rotate_d)
    return transformed_x, transformed_y, transformed_d


def deal_with_phi(phi):
    while phi > 180:
        phi -= 360
    while phi <= -180:
        phi += 360
    return phi