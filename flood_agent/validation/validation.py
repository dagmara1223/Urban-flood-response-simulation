import numpy as np
import rasterio
from rasterio import features
import cv2
import shapely.geometry
from rasterio.warp import reproject, Resampling
import rasterio.features
from rasterio.transform import array_bounds

def mask_to_polygons(mask, transform):
    # Extract polygons from mask
    shapes_generator = rasterio.features.shapes(mask.astype(np.uint8), transform=transform)
    polygons = []
    for geom, val in shapes_generator:
        if val == 1:
            polygons.append(shapely.geometry.shape(geom))
    return polygons

from rasterio.warp import reproject, Resampling

def reproject_mask_to_model(mask, src_transform, src_crs, dst_transform, dst_crs, dst_shape):
    dst = np.zeros(dst_shape, dtype=np.uint8)
    reproject(
        source=mask.astype(np.uint8),
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest
    )
    return dst.astype(bool)


def load_georef_map(path):
    """
    Loads georeferenced flood map and returns:
    - RGB array
    - transform
    - CRS
    """
    with rasterio.open(path) as src:
        bands = src.count

        if bands == 1:
            # grayscale tif
            img = src.read(1)
            img = np.expand_dims(img, axis=-1)  # shape: H, W, 1
        elif bands >= 3:
            # RGB or RGBA
            img = src.read([1,2,3])
            img = np.transpose(img, (1,2,0))  # CHW → HWC
        else:
            raise ValueError(f"Unsupported number of bands: {bands}")
        transform = src.transform
        crs = src.crs
    return img, transform, crs

def extract_flood_mask_from_png(rgb_img):
    """
    Takes either:
        - grayscale image (H, W, 1)
        - RGB image (H, W, 3)
    Returns:
        Boolean flood mask
    """

    # GRAYSCALE --------------------------------------------------------------
    if rgb_img.ndim == 2 or rgb_img.shape[-1] == 1:
        if rgb_img.ndim == 3:
            gray = rgb_img[:, :, 0]
        else:
            gray = rgb_img

        # Threshold for flood on grayscale
        # Adjust this based on your map
        # If flooded areas are dark: use < 128
        mask = gray < 128
        return mask.astype(bool)

    # RGB --------------------------------------------------------------------
    if rgb_img.shape[-1] == 3:
        hsv = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)

        # blue-ish flood color (tune!)
        lower = np.array([90, 40, 40])
        upper = np.array([140, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

        return mask.astype(bool)

    raise ValueError(f"Unsupported number of channels: {rgb_img.shape}")

def rasterize_reference_mask(
    flood_mask_bool,
    map_transform,
    model_transform,
    model_shape
):
    """
    Resamples georeferenced image mask into the same raster grid as the model.
    """

    # Create shapes (polygons) for flood cells inside the map image
    # Each flood pixel becomes a small polygon
    shapes = []

    height, width = flood_mask_bool.shape
    for i in range(height):
        for j in range(width):
            if flood_mask_bool[i, j]:
                shapes.append((
                    rasterio.transform.xy(map_transform, i, j, offset='center'),
                    1
                ))

    # If you prefer faster → polygonize + transform → rasterize.
    # This direct pixel-to-point approach is simpler but slower.

    # Convert point shapes into a raster matching the model grid
    # Better: polygonize the flood mask once in QGIS.
    out = features.rasterize(
        shapes=[((x, y), 1) for (x, y) in shapes],
        out_shape=model_shape,
        transform=model_transform,
        fill=0
    )
    return out.astype(bool)


def compute_binary_validation(model_mask, reference_mask):
    """
    Computes binary classification metrics.
    """

    tp = np.logical_and(model_mask, reference_mask).sum()
    fp = np.logical_and(model_mask, ~reference_mask).sum()
    fn = np.logical_and(~model_mask, reference_mask).sum()

    iou = tp / (tp + fp + fn + 1e-12)
    precision = tp / (tp + fp + 1e-12)
    recall = tp / (tp + fn + 1e-12)

    return {
        "TP": int(tp),
        "FP": int(fp),
        "FN": int(fn),
        "IoU": float(iou),
        "Precision": float(precision),
        "Recall": float(recall)
    }


# -------------------------
# MAIN VALIDATION PIPELINE
# -------------------------

def validate_model_flood(
    map_path,
    model_height,
    model_water,
    model_transform
):

    # 1. Load georeferenced flood map
    rgb, map_transform, map_crs = load_georef_map(map_path)

    # 2. Extract flood mask from RGB map
    map_mask_bool = extract_flood_mask_from_png(rgb)

    # 3. Rasterize map mask onto model grid
    polygons = mask_to_polygons(map_mask_bool, map_transform)
    shapes = [(polygon, 1) for polygon in polygons]

    with rasterio.open('Data/krakow_merged.tif') as src:
        model_crs = src.crs

    reference_mask = reproject_mask_to_model(
        mask=map_mask_bool,
        src_transform=map_transform,
        src_crs=map_crs,
        dst_transform=model_transform,
        dst_crs=model_crs,
        dst_shape=model_height.shape
    )
    # 4. Model binary mask (choose threshold)
    model_mask = (model_water > 0.05)  # water deeper than 5 cm

    # 5. Compute validation
    metrics = compute_binary_validation(model_mask, reference_mask)



    print("Model mask sum:", model_mask.sum())
    print("Reference mask sum (after reprojection):", reference_mask.sum())
    print("Original PNG mask sum:", map_mask_bool.sum())

    print("map_transform:", map_transform)
    print("model_transform:", model_transform)
    print("map_crs:", map_crs)
    print("model_crs:", model_crs)

    map_height, map_width = map_mask_bool.shape
    map_bounds = array_bounds(map_height, map_width, map_transform)
    print("Map bounds:", map_bounds)

    # Model raster info
    model_height_, model_width_ = model_height.shape
    model_bounds = array_bounds(model_height_, model_width_, model_transform)
    print("Model bounds:", model_bounds)


    return model_mask, reference_mask, metrics
