import numpy as np
from matplotlib.path import Path
import cv2
import os

# Landmarks for each point, obtained via https://github.com/google/mediapipe/issues/1615
FOREHEAD_POINTS = [251, 284, 332, 297, 338, 10, 109, 67, 103, 54, 21, 162, 139, 70, 63, 105, 66, 107,
                       9, 336, 296, 334, 293, 300, 383, 368, 389]
LCHEEK_POINTS = [31, 35, 143, 116, 123, 147, 213, 192, 214, 212, 216, 206, 203, 36, 101, 119, 229, 228]
RCHEEK_POINTS = [261, 265, 372, 345, 352, 376, 433, 434, 432, 436, 426, 423, 266, 330, 348, 449, 448]

# bounding variables for pixels to iterate over
x_left, x_right = float("inf"), -float("inf")
y_up, y_down = float("inf"), -float("inf")


# Calculate the perceived brightness of a single pixel, given RGB values, sourced from link below (ITU BT.709)
# https://stackoverflow.com/questions/596216/formula-to-determine-perceived-brightness-of-rgb-color#596243
def calculate_luminance(r, g, b):
    return round(0.2126 * r + 0.7152 * g + 0.0722 * b, 2)


# SREDS-sourced method for perceived brightness, assuming that a higher RGB leads to a brighter color
def estimate_luminance(r, g, b):
    return round((r + g + b) / 3, 2)


# Return the mean and stdevs for RGB values within the image, for select points
def get_stats(img, arr):
    r_vals, g_vals, b_vals = [], [], []

    for points in arr:
        for p0, p1 in points:
            temp = img[p0, p1]
            r_vals.append(temp[0])
            g_vals.append(temp[1])
            b_vals.append(temp[2])

    means = (np.mean(r_vals), np.mean(g_vals), np.mean(b_vals))
    stds = (np.std(r_vals), np.std(g_vals), np.std(b_vals))

    return means, stds


def get_range(pt, std):
    return tuple([pt - 2 * std, pt + 2 * std])


# Check if a point falls within a particular range
def point_in_range(point, ranges):
    for i in range(len(point)):
        if point[i] < ranges[i][0] or point[i] > ranges[i][1]:
            # point lies outside the range
            return False
    return True


# return a cleaned array of 3 patches, each patch represents points within the patch
def clean_patches(img, patches, use_stdevs, threshold):
    forehead_pts, lcheek_pts, rcheek_pts = patches

    # Check if cheeks don't have enough points - if so, then array becomes nullified
    if len(forehead_pts) < threshold:
        forehead_pts = np.empty()

    if len(lcheek_pts) < threshold:
        lcheek_pts = np.empty()

    if len(rcheek_pts) < threshold:
        rcheek_pts = np.empty()

    if use_stdevs:
        # Return all the points that are within 2 standard deviations of RGB values
        means, stds = get_stats(img, [forehead_pts, lcheek_pts, rcheek_pts])
        return np.array([filter_by_stdevs(img, forehead_pts, means, stds),
                         filter_by_stdevs(img, lcheek_pts, means, stds),
                         filter_by_stdevs(img, rcheek_pts, means, stds)])
    else:
        return np.array([forehead_pts, lcheek_pts, rcheek_pts], dtype=object)


# Given an image, means/stdevs, and points, return only the points within 2 stds
def filter_by_stdevs(img, points, means, stds):
    r_mean, g_mean, b_mean = means
    r_std, g_std, b_std = stds

    # Ranges for which points should be included
    r_range = get_range(r_mean, r_std)
    g_range = get_range(g_mean, g_std)
    b_range = get_range(b_mean, b_std)

    ranges = [r_range, g_range, b_range]

    # list of all points that fall within valid rgb ranges
    new_points = np.array([(y, x) for y, x in points if point_in_range(img[y, x], ranges)])
    return new_points

def generate_patches(img, landmarks, pointList):
    global x_left, x_right, y_down, y_up
    i_h, i_w, i_c = img.shape
    patch = []
    for i in pointList:
        point = landmarks[i]
        x_coord = int(i_w * point["x"])
        y_coord = int(i_h * point["y"])

        patch.append((x_coord, y_coord))
        x_left, x_right = min(x_left, x_coord), max(x_right, x_coord)
        y_up, y_down = min(y_up, y_coord), max(y_down, y_coord)
    return patch


# inner function to get patches
def get_patches(img, face_landmarks):
    # Setting up patches for each body part
    forehead_landmarks = generate_patches(img, face_landmarks, FOREHEAD_POINTS)
    lcheek_landmarks = generate_patches(img, face_landmarks, LCHEEK_POINTS)
    rcheek_landmarks = generate_patches(img, face_landmarks, RCHEEK_POINTS)

    # Generating MPL paths for each patch - used to iterate pixels
    forehead_path = Path(forehead_landmarks)
    lcheek_path = Path(lcheek_landmarks)
    rcheek_path = Path(rcheek_landmarks)

    # # Array of all pixels in the given area
    f_pts, r_pts, l_pts = [], [], []

    # Iterate through all pixels in image, check if pixel in path, then add
    for y in range(y_up, y_down + 1):
        for x in range(x_left, x_right + 1):
            # Check if point in the given shape - if so, add to array
            if forehead_path.contains_point((x, y)):
                f_pts.append((y, x))
            elif lcheek_path.contains_point((x, y)):
                l_pts.append((y, x))
            elif rcheek_path.contains_point((x, y)):
                r_pts.append((y, x))

    return [f_pts, l_pts, r_pts]


# Given an array of points, draw the points on the provided image and create a copy
def display_points(img, patches, name, diff):
    print(diff)
    shape = img.shape

    patches_img = np.zeros(shape, dtype=np.uint8)
    invert_img = np.zeros(shape, dtype=np.uint8)

    for face in patches:


        for i in range(len(diff)):
            diff[i] = min(255, int(diff[i]))

        for patch in points:
            for y, x in patch:
                temp = image[y, x].copy()
                image[y, x] = [0, 0, 0]
                invert[y, x] = temp
                diffuse[y, x] = diff.copy()

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    invert = cv2.cvtColor(invert, cv2.COLOR_BGR2RGB)
    diffuse = cv2.cvtColor(diffuse, cv2.COLOR_BGR2RGB)

    cv2.imwrite(f"./results/imgs/{name}_IMAGE.jpg", image)
    cv2.imwrite(f"./results/imgs/{name}_INVERT.jpg", invert)
    cv2.imwrite(f"./results/imgs/{name}_DIFFUSE.jpg", diffuse)
