import cv2
import mediapipe as mp
import numpy as np
from mediapipe.framework.formats.landmark_pb2 import NormalizedLandmarkList
from matplotlib.path import Path
from shapely.geometry import Polygon


mpDraw = mp.solutions.drawing_utils
mpFaceMesh = mp.solutions.face_mesh
faceMesh = mpFaceMesh.FaceMesh(max_num_faces=2)

FOREHEAD_POINTS = [251, 284, 332, 297, 338, 10, 109, 67, 103, 54, 21, 162, 139, 70, 63, 105, 66, 107,
                   9, 336, 296, 334, 293, 300, 383, 368, 389]
LCHEEK_POINTS = [31, 35, 143, 116, 123, 147, 213, 192, 214, 212, 216, 206, 203, 36, 101, 119, 229, 228]
RCHEEK_POINTS = [261, 265, 372, 345, 352, 376, 433, 434, 432, 436, 426, 423, 266, 330, 348, 449, 448]


def get_points(n_img, landmarks):
    i_h, i_w, i_c = n_img.shape
    for faceLms in landmarks[:1]:
        # List of all the landmark coordinates from the generated face
        forehead_landmarks = [(i_w * f.x, i_h * f.y) for f in [faceLms.landmark[i] for i in FOREHEAD_POINTS]]
        lcheek_landmarks = [(i_w * f.x, i_h * f.y) for f in [faceLms.landmark[i] for i in LCHEEK_POINTS]]
        rcheek_landmarks = [(i_w * f.x, i_h * f.y) for f in [faceLms.landmark[i] for i in RCHEEK_POINTS]]

        # Generating MPL paths for each body part - used to iterate pixels
        forehead_path = Path(forehead_landmarks)
        lcheek_path = Path(lcheek_landmarks)
        rcheek_path = Path(rcheek_landmarks)

        lcheek_area, rcheek_area = Polygon(lcheek_landmarks).area, Polygon(rcheek_landmarks).area

        points = set() # Set of all pixels to change

        # Iterate through all pixels in image, check if pixel in path, then add
        for i in range(i_h):
            for j in range(i_w):
                if forehead_path.contains_point((j, i)):
                    points.add((i, j))

                # Check if the left cheek is at least 1/2 the size of the right cheek - if so, add to points
                if lcheek_area/rcheek_area > 0.5 and lcheek_path.contains_point((j, i)):
                    points.add((i, j))

                # Same process ass mentioned above, but with right cheek
                if rcheek_area/lcheek_area > 0.5 and rcheek_path.contains_point((j, i)):
                    points.add((i, j))

    # Return all the points that are within 2 standard deviations of YUB values
    return clean_data(n_img, points)


# Given an image and a set of points, return only the points within 2 stds, for YUV values
def clean_data(n_img, points):
    y, u, b = [], [], []

    # Create lists of YUB values
    for p0, p1 in points:
        temp = n_img[p0, p1]
        y.append(temp[0])
        u.append(temp[1])
        b.append(temp[2])

    print("pre-cleaning", len(points))

    # Get means and ranges for each variable
    y_mean, u_mean, b_mean = np.mean(y), np.mean(u), np.mean(b)
    y_std, u_std, b_std = np.std(y), np.std(u), np.std(b)
    y_range, u_range, b_range = (y_mean - 2*y_std, y_mean + 2*y_std), (u_mean - 2*u_std, u_mean + 2*u_std), (b_mean - 2*b_std, b_mean + 2*b_std)

    new_points = set()
    for p0, p1 in points:
        temp = n_img[p0, p1]
        # Check if point is within given ranges -> if so, add to new set
        if (y_range[0] <= temp[0] <= y_range[1]) and (u_range[0] <= temp[1] <= u_range[1]) and (b_range[0] <= temp[2] <= b_range[1]):
            new_points.add((p0, p1))

    print("post-cleaning", len(new_points))

    return new_points


def display_points(n_img, points, n_name):
    invert = n_img.copy()
    i_h, i_w, i_c = n_img.shape
    for i in range(i_h):
        for j in range(i_w):
            if (i, j) in points:
                invert[i, j] = [0, 0, 0]
            else:
                n_img[i, j] = [0, 0, 0]

    cv2.imwrite(f"../results/{n_name}_IMAGE.jpg", n_img)
    cv2.imwrite(f"../results/{n_name}_INVERT.jpg", invert)


def process_image(n_img, n_name):
    imgRGB = cv2.cvtColor(n_img, cv2.COLOR_BGR2RGB)
    imgYUB = cv2.cvtColor(n_img, cv2.COLOR_BGR2YUV)
    results = faceMesh.process(imgRGB)

    if results.multi_face_landmarks:
        points = get_points(imgYUB, results.multi_face_landmarks)
        display_points(n_img, points, n_name)

    return imgYUB


name = "drake"
img = cv2.imread(f"../images/{name}.jpg")
img = process_image(img, name)
