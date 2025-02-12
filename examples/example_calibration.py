from pyarcam.layqam import LayqamFiles, CartesianPoints

files = LayqamFiles("WaferSupport.py")  # Open folder with Layercam  
uvpoints = files.calibration[0].points()  # Extract calibration points from image
xypoints = CartesianPoints(num=58, delta=0.003)  # Set calibration pattern in cartesian coordinates 

# Estimate transformation from cartesian to image as polynomial and
# apply transformation and calculate root mean squared error in pixels
xy2uv = xypoints.polyfit(uvpoints) 
rmse = xypoints.transform(xy2uv).rmse(uvpoints) 
print("rmse: ", rmse, " [pixel]")

# Estimate transformation from image to cartesian as polynomial and
# apply transformation and calculate root mean squared error in meters
uv2xy = uvpoints.polyfit(xypoints) 
rmse = uvpoints.transform(uv2xy).rmse(xypoints) 
print("rmse: ", rmse, " [meter]")

# Plots calibration file and overlay cartesian points after applied transform
plt = files.calibration[0].plot()
points = xypoints.transform(xy2uv).round().tolist()
plt.circles(points=points, color=(0, 255, 0), size=5)
plt.show(scale=.6)
