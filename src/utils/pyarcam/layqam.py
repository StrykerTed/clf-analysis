from __future__ import annotations
import cv2
import os
import glob
import numpy as np
from shapely.geometry import MultiPoint
from ctypes import Union
from typing import Callable, Iterator, List

class Image: 
    """
    Pointer to image file

    """
    def __init__(self, filename : str):
        """Constructor

        Parameters
        ----------
        filename : str
            Image file full path
        """
        self.filename = filename

    def exists(self) -> bool:
        """File exists true/false

        Returns
        ----------
        True if file exists, false otherwise
        """
        return os.path.isfile(self.filename)

    def load(self, rgb : bool = False) -> np.array:
        """load file and return as numpy array

        Parameters
        ----------
        rgb : bool
            Return with three bands

        Returns
        ----------
        Image data as a numpy array
        """
        img = cv2.imread(self.filename, 0)
        if img is None: raise FileNotFoundError(self.filename)
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB) if rgb else img

class CalibrationPattern: 
    """
    Points arranged in a matrix represtenting a calibration pattern

    """
    def __init__(self, X : np.array, Y : np.array):
        """Constructor

        Parameters
        ----------
        X : np.array
            Calibration pattern X coordinates
        Y : np.array
            Calibration pattern Y coordinates
        """
        assert(X.shape[0] == X.shape[1])
        assert(X.shape == Y.shape)
        self.X = X
        self.Y = Y
        self.shape = X.shape

    def toarray(self) -> tuple[np.array, np.array]:
        """
        Returning points as tuple of arrays

        Returns
        ----------
        x-coordinates
        y-coordinates
        """
        return self.X.flatten(), self.Y.flatten()
    
    def points(self) -> Points:
        """
        Returning points as Points object

        Returns
        ----------
        points
        """
        x, y = self.toarray()
        return Points([elem for elem in zip(x, y) if not np.nan in elem])

    def polyfit(self, other : np.array) -> Callable[[float, float], tuple[float, float]]:
        assert(self.shape == other.shape)

        x, y = self.toarray()
        u, v = other.toarray()
        index = np.logical_and(~np.isnan(x), ~np.isnan(u)) 
        x = x[index]
        y = y[index]
        u = u[index]
        v = v[index]

        A = np.stack((x**3, x**2 * y, x * y**2, y**3, x**2, x * y, y**2, x, y, np.ones(x.shape)), axis = 1)
        AT = A.transpose()
        ATA = AT.dot(A)

        coeff = ( np.linalg.solve(ATA, AT.dot(u)), np.linalg.solve(ATA, AT.dot(v)) )
        return lambda x, y: polymap(coeff, x, y)

class CartesianPattern(CalibrationPattern): 
    """
    Calibration pattern in machine cartesian coordinates

    """
    def __init__(self, num : int, spacing : float = 3.0):
        """Constructor

        Parameters
        ----------
        num : int
            Number of points
        spacing : float
            Spacing between points [mm]
        """
        val = np.linspace(-(num - 1) / 2. * spacing, (num - 1) / 2.0 * spacing, num=num)
        X, Y = np.meshgrid(-val, val)
        super().__init__(Y, X)


def polymap(coefficients : Union[np.array, list[float]], x : Union[np.array, float], y : Union[np.array, float]) -> Union[tuple[np.array, np.array], tuple[float, float]]:
    """
    Map two dimensional points using a third degreen polynomial

    Paramters
    ----------
    coefficients : np.array
        Polynomial coefficients
    x : np.array
        Incoming x-coordinates
    y : np.array
        Incoming y-coordinates

    Returns
    ----------
    Transformed x-coordinates
    Transformed y-coordinates
    """
    c = coefficients[0] 
    u = c[0] * x**3 + c[1] * x**2 * y + c[2] * x * y**2 + c[3] * y**3 + c[4] * x**2 + c[5] * x * y + c[6] * y**2 + c[7] * x + c[8] * y + c[9]
    c = coefficients[1]
    v = c[0] * x**3 + c[1] * x**2 * y + c[2] * x * y**2 + c[3] * y**3 + c[4] * x**2 + c[5] * x * y + c[6] * y**2 + c[7] * x + c[8] * y + c[9]
    return u, v

class Points: 
    """
    Base class for points

    """

    def __init__(self, coords : List[tuple[float, float]]):
        """Constructor

        Parameters
        ----------
        points : List[Tuple[float, float]]
            Point coordinates as tuples of floats
        """
        self.coords = coords

    def transform(self, func : Callable[[float, float], tuple[float, float]]) -> Points:
        """transform points using transformation function

        Parameters
        ----------
        func : Callable[[float, float], Tuple[float, float]]
            Transformation function
        
        Returns
        ----------
        Tranformed points

        """ 
        return Points([func(*elem) for elem in self.coords])

    def rmse(self, other : Points) -> float:
        """Returning root mean squared error between two set of points

        Parameters
        ----------
        other : Points
            Other set of points
        
        Returns
        ----------
        Root mean squared error

        """ 
        assert(len(self.coords) == len(other.coords))
        out = 0.0
        for (p, q) in zip(self.coords, other.coords): 
            out += ((p.x - q.x)**2 + (p.x - q.x)**2) / len(self)
        return np.sqrt(out)
    
    def plot(self, img : np.array, color : tuple[int, int, int] = (255, 0, 0), size : int = 3):
        """Returning root mean squared error between two set of points

        Parameters
        ----------
        img : np.array
            The image at which to plot the points
        color : tuple[int, int, int]
            The point color
        size : int
            The point size in pixels

        """ 
        for p in self.coords: 
            if np.isnan(p[0]): continue
            cv2.circle(img, (int(p[0]), int(p[1])), size, color, size)

class CalibrationPoints(Points): 
    """
    Points extracted from calibration image

    """

    def __init__(self, points : List[tuple[float, float]]):
        """Constructor

        Parameters
        ----------
        points : List[Tuple[float, float]]
            Point coordinates as tuples of floats
        """
        super().__init__(points)
        if not points: raise Exception("No point detected")
        rectangle = MultiPoint(self.coords).minimum_rotated_rectangle.exterior.coords

        p00 = np.array(min(rectangle, key=lambda elem: elem[0] + elem[1]))
        p01 = np.array(min(rectangle, key=lambda elem:-elem[0] + elem[1]))
        p10 = np.array(min(rectangle, key=lambda elem: elem[0] - elem[1]))

        uhat = p01 - p00
        vhat = p10 - p00
        self.dimensions = [np.linalg.norm(uhat), np.linalg.norm(vhat)]

        uhat = uhat / self.dimensions[0]
        vhat = vhat / self.dimensions[1]

        self.origin = p00
        self.rotation = np.stack((uhat, vhat))

    def local2image(self, x : float, y : float) -> tuple[float, float]:
        """Linear transform from point matrix to image coordinates

        Parameters
        ----------
        x : float
            Matrix row coordinate
        y : float
            Matrix column coordinate

        Returns
        ----------
        Corresponding image coordinates

        """
        u = self.rotation[0, 0] * x + self.rotation[1, 0] * y + self.origin[0]
        v = self.rotation[0, 1] * x + self.rotation[1, 1] * y + self.origin[1]
        return u, v

    def image2local(self, x : float, y : float) -> tuple[float, float]:
        """Linear transform from image coordinates to point matrix coordinates

        Parameters
        ----------
        x : float
            Image row
        y : float
            Image column

        Returns
        ----------
        Corresponding point matrix coordinates

        """
        u = self.rotation[0, 0] * (x - self.origin[0]) + self.rotation[0, 1] * (y - self.origin[1])
        v = self.rotation[1, 0] * (x - self.origin[0]) + self.rotation[1, 1] * (y - self.origin[1]) 
        return u, v

    def sorted(self, precision : float = 0.5) -> tuple[CalibrationPattern, float]:
        """Sort the points into a matrix

        Parameters
        ----------
        precision : float
            Accepted relative deviation from prediction

        Returns
        ----------
        Corresponding cartesian coordinates

        """
        uv = np.array(self.coords).transpose()
        x, y = self.image2local(uv[0,:], uv[1,:])

        index = [np.argsort(np.sqrt(np.square(xi - x) + np.square(yi - y)))[1:12] for xi, yi in zip(x, y)]
        dx = np.array([np.median(np.abs(xi - x[i])) for (xi, i) in zip(x, index)])
        dy = np.array([np.median(np.abs(yi - y[i])) for (yi, i) in zip(y, index)])

        A = np.stack((x, y, np.ones(x.shape)), axis = 1)
        AT = A.transpose()
        ATA = AT.dot(A)
        dxcoeff = np.linalg.solve(ATA, AT.dot(dx))
        dycoeff = np.linalg.solve(ATA, AT.dot(dy))

        Nx = int(self.dimensions[0] / np.median(dx)) + 1
        Ny = int(self.dimensions[1] / np.median(dy)) + 1

        X = np.zeros((Nx, Ny))
        Y = np.zeros((Nx, Ny))
        U = np.full((Nx, Ny), np.nan)
        V = np.full((Nx, Ny), np.nan)

        for i in range(Nx): 
            for j in range(Ny):
                n = 0

                if i > 0:  
                    dx = X[i - 1, j] * dxcoeff[0] + Y[i - 1, j] * dxcoeff[1] + dxcoeff[2]
                    X[i, j] += X[i - 1, j] + dx
                    Y[i, j] += Y[i - 1, j]
                    n += 1

                if j > 0: 
                    dy = X[i, j - 1] * dycoeff[0] + Y[i, j - 1] * dycoeff[1] + dycoeff[2]
                    X[i, j] += X[i, j - 1]
                    Y[i, j] += Y[i, j - 1] + dy
                    n += 1

                if n > 0: 
                    X[i, j] = X[i, j] / n
                    Y[i, j] = Y[i, j] / n

                dx = X[i, j] * dxcoeff[0] + Y[i, j] * dxcoeff[1] + dxcoeff[2]
                dy = X[i, j] * dycoeff[0] + Y[i, j] * dycoeff[1] + dycoeff[2]

                xdiff = X[i, j] - x
                ydiff = Y[i, j] - y
                imin = np.argmin(np.square(xdiff) + np.square(ydiff))
                ok = np.abs(xdiff[imin]) / dx < precision and np.abs(ydiff[imin]) / dy < precision

                if not ok: continue
                X[i, j] = x[imin] 
                Y[i, j] = y[imin]
                U[i, j] = uv[0, imin] 
                V[i, j] = uv[1, imin]
                

        while True:
            if np.isnan(U[-1, :]).all(): 
                U = U[0:-1, :]
                V = V[0:-1, :]
            elif np.isnan(U[:,-1]).all(): 
                U = U[:, 0:-1]
                V = V[:, 0:-1]
            else: 
                break

        return CalibrationPattern(U, V), 1.0 - np.isnan(U).sum() / U.size 

class CalibrationImage(Image): 
    """
    An image taken for calibration purpose

    """

    def points(self, threshold : int = 20, window : int = 11, background : int = 30) -> CalibrationPoints: 
        """Find calibration points in image

        Parameters
        ----------
        threshold : int
            Intensity threshold for point detection
        window : int
            Gaussian blur window size
        background : int
            Kernel size for background estimation

        Returns
        ----------
        Points extracted from image

        """
        img = self.load()

        kernel = np.ones((background, background), np.float32) / background**2
        bg = cv2.filter2D(img, -1, kernel)

        img = img.astype(np.float32) - bg
        img[img < 0] = 0.
        img = (img / img.max() * 255).astype(np.uint8)

        blurred = cv2.GaussianBlur(img, (window, window), 0)
        thresh = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.erode(thresh, None, iterations=1)

        output = cv2.connectedComponentsWithStats(thresh)
        stats = output[2]
        points = []
        for elem in stats:
            if elem[4] > 100: continue
            val = img[elem[1]:elem[1] + elem[3], elem[0]:elem[0] + elem[2]]
            V, U = np.meshgrid(np.arange(elem[2]), np.arange(elem[3]))
            u = elem[1] + (val * U).sum() / val.sum()
            v = elem[0] + (val * V).sum() / val.sum()
            points.append((v, u)) 

        return CalibrationPoints(points)

    def calibrate(self, precision : float = 0.3, spacing : float = 3.0) -> tuple[Callable[[float, float], tuple[float, float]], Callable[[float, float], tuple[float, float]], float]: 
        """Calibrate for distortion and mounting

        Parameters
        ----------
        precision : float
            Accepted relative deviation when sorting out points.
        spacing : float
            Point pattern spacing [mm]

        Returns
        ----------
        cartesian to image function
        image to cartesian function
        calibration score between 0.0 and 1.0

        """
        impattern, confidence = self.points().sorted(precision)
        if impattern.shape[0] != impattern.shape[1]: raise Exception(f"Calibration points shape {impattern.shape} is not valid")
        xypattern = CartesianPattern(impattern.shape[0], spacing=spacing)
        return xypattern.polyfit(impattern), impattern.polyfit(xypattern), confidence

class Layer: 
    """
    Holds all images of one layer

    Attributes
    ----------
    z : float
        Layer height
    images : list[Image]
        List of potential images in layer
    """

    def __init__(self, path : str, height : str):
        """Constructor

        Parameters
        ----------
        path : str
            The folder in which the layerqam files resides
        height : str
            The height string
        """
        self.z = float(height)
        self.images = [Image(os.path.join(path, f"Layer{height}Image_{i}.png")) for i in range(3)]

    def __iteritem__(self) -> Iterator[Image]:
        """Iterate over all existing images for this layer

        Returns
        ----------
        Image iterator

        """
        for elem in self.images: 
            if elem.exists(): yield elem

class LayqamFiles: 
    """
    Holds all layerqam files produced for one build

    Attributes
    ----------
    calibration : list[CalibrationImage]
        List of calibration images in build
    layers : list[Layer]
        List of layers in build
    """

    def __init__(self, path : str): 
        """Constructor

        Parameters
        ----------
        path : str
            The folder in which the layerqam files resides

        """
        # Calibration
        names = glob.glob(os.path.join(path, "CameraCalibrationPattern*.png"))
        self.calibration = [CalibrationImage(elem) for elem in names]

        # Layers
        names = glob.glob(os.path.join(path, "Layer*.png"))
        elements = set()
        self.layers = []
        for elem in names:
            path, name = os.path.split(elem) 
            height = name[5:name.find("Image")]
            if height in elements: continue
            self.layers.append(Layer(path, height))
        self.layers.sort(key = lambda elem: elem.z)

    def find(self, z : float) -> Layer:
        """Find the layer closest to height z

        Parameters
        ----------
        z : float
            The requested height

        Returns
        ----------
        Layer : The closest layer

        """
        return min(self.layers, key=lambda elem:abs(elem.z - z))

    def __getitem__(self, index : int) -> Layer:
        """Return layer at index

        Parameters
        ----------
        index : int
            The requested index

        Returns
        ----------
        Layer: The layer at that index

        """
        return self.layers[index]

    def __iteritem__(self) -> Iterator[Layer]:
        """layer iterator

        Returns
        ----------
        Layer iterator

        """
        for elem in self.layers: 
            yield elem

    def __len__(self) -> int:
        """Number of layers

        Returns
        ----------
        Number of layers

        """
        return len(self.layers)