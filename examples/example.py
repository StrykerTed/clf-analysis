import cv2
from pyarcam import clf, qam

# Read clf file and find the correct layer
part = clf.open("Net.clf")
layer = part.find(20.0)

# Load image files
files = qam.LayqamFiles("/path/to/image/folder")

# Use the calibration file to get a transform function
for elem in files.calibration:
    if not elem.exists(): continue
    try: 
        xy2uv, uv2xy, confidence = elem.calibrate()
        if confidence < 0.95: continue
    except Exception as e: 
        print(e)

# Open an image from the same height as the clf
for elem in files.find(20.0).images:
    if not elem.exists(): continue
    img = elem.load(rgb=True)
    break

# choose those polygons that represent melted areas and transform using the calibration
layer = layer.filter(clf.ModelCluster).transform(xy2uv)

# plot the parts on top of the image
layer.plot(img, color=(255, 0, 0), filled=True)

cv2.imshow("Layer 20.0", img)
cv2.waitKey(0)