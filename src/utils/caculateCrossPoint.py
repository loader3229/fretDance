import numpy as np


def get_cross_point(direction_line_start_point: np.ndarray, direction_line_vector: np.ndarray, guitar_suface_vector: np.ndarray, string_line_start_point: np.ndarray, string_line_vector: np.ndarray) -> np.ndarray:

    # 获得一个垂直于direction_line_vector和guitar_surface的向量
    normal_vector = np.cross(direction_line_vector, guitar_suface_vector)

    w = string_line_start_point - direction_line_start_point
    fac = -np.dot(normal_vector, w) / np.dot(normal_vector, string_line_vector)
    u = string_line_vector * fac
    return string_line_start_point + u
