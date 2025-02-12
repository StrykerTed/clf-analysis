import struct
from enum import Enum
import numpy as np
import io
import cv2
import shapely.geometry as geo
from matplotlib.path import Path

'''Utilities to read and display the content of CLF files 

Example: 
>> from pyarcam.clfutil import Build
>> from pyarcam.layqam import LayqamFiles
>> qamfiles = LayqamFiles("/path/to/layerqam/files") # Load LayerQam files
>> func = qamfiles.calibrate()  # Generate mapping from cartesian to image coordinates
>> build = Build("/some_path/some_file_base_name_{}.clf", range(1, 10)) + Build("/some_path/some_other_file_base_name_{}.clf", range(1, 12))
>> layer = build.find(20.0) # Find layer at 20 mm height
>> mask = layer.filter(ModelCluster).transform(func).mask((512, 512)) # filter out melt, transform to image and generate a 512x512 mask
'''

class Build: 
    '''Object type for loading builds

    A build is essentially a set of CLF files, and that set can be defined using string formatting and iterators.
    Builds can also be added to each other to produce compound builds if parts have different naming formats or are located in different folders.

    Example: 
    >> build = Build("/some_path/some_file_base_name_{}.clf", range(1, 10)) + Build("/some_path/some_other_file_base_name_{}.clf", range(1, 12))
    >> layer = build.find(20.0) # Find layer at 20 mm height
    >> func = build.box.toimage(height=512, width=512) # extract mapping from box to image
    >> mask = layer.filter(ModelCluster).transform(func).mask((512, 512)) # filter out melt, transform to image and generate a 512x512 mask
    '''
    def __init__(self, pattern=None, labels=None): 
        if type(pattern) is CLFFile: 
            self.files = pattern
        elif type(pattern) is str and labels is None: 
            self.files = [CLFFile(pattern, load=False)]
        elif type(pattern) is str: 
            self.files = [CLFFile(pattern % i, load=False) for i in labels]
        elif type(pattern) is list:
            self.files = [CLFFile(elem, load=False) for elem in pattern]
        else: 
            raise Exception("Not valid input format")
        
        # Box
        self.box = self.files[0].box
        for elem in self.files[1:]: self.box = self.box + elem.box
        
        # Thickness
        self.thickness = min([elem.thickness for elem in self.files])

    def find(self, z, merge=True): 
        
        if merge: 
            layer = None
            for elem in self.files:
                if layer is None: 
                    layer = elem.find(z)
                else: 
                    layer = layer + elem.find(z)
            return layer
        else: 
            return LayerList([elem.find(z) for elem in self.files])

    def forward(self, z0=None, dz=None, merge=False): 
        if dz is None: dz = self.thickness
        z = self.box.min[2] if z0 is None else z0
        while z < self.box.max[2]: 
            layer = self.find(z, merge=merge)
            z = z + dz
            yield layer
    
    def backward(self, z0=None, dz=None, merge=False): 
        if dz is None: dz = self.thickness
        z = self.box.max[2] if z0 is None else z0
        while z > self.box.min[2]: 
            z = z - dz
            yield self.find(z, merge=merge)

    def __iter__(self): 
        z = self.box.min[2]
        while z < self.box.max[2]: 
            layer = self.find(z)
            z = z + self.thickness
            yield layer

    def __add__(self, other): 
        out = Build()
        out.files = self.files + other.files
        out.box = self.box + other.box
        out.thickness = min(self.thickness, other.thickness)
        return out

def open(filename, load=False): 
    '''Open clf file
    '''
    return CLFFile(filename, load=load)

class CLFFile: 
    '''Object type for loading CLF files 

    Example - Read all layers: 
    >> file = CLFFile(filename, load=True)
    >> print(file) // print file information
    Name: Arcam Layer File
    Version: 1.0
    Number of Layers: 100
    Comment: This is a Test.

    >> file.layer[0].show() // plot first layer

    Example - Load each layer when requesting it: 
    >> file = CLFFile(filename, load=False)
    >> layer = file.layer[0].load() 
    '''

    def __init__(self, filename, load=False): 
        
        self.buffer = ByteStream(filename)

        self.name = "no name"
        self.comment = ""
        self.version = "?"
        self.nlayers = 0

        # Header
        sid = self.buffer.lf_int()
        assert(sid == 0)
        self._read_header()

        # Layers
        self.layers = []

        if load: 
            while True: 
                sid = self.buffer.lf_int()
                if sid == 1: 
                    self.buffer.skip()
                elif sid == 2:
                    self.layers += [self.buffer.layer(self)]
                elif sid == 3: # End Of File
                    break
                else: 
                    raise UknownSectionException(sid)
            self.buffer.close()
        else: 
            self.buffer.seek(self.iseek)
            sid = self.buffer.lf_int()
            assert(sid == 1)
            self._read_seek_table()
 
        self.layers.sort(key = lambda elem: elem.z)

    def find(self, z): 
        if z > self.box.max[2] or z < self.box.min[2]: return Layer(z, [], self)
        layer = min(self.layers, key=lambda elem:abs(elem.z - z))
        if abs(layer.z - z) > self.thickness: 
            return Layer(z, [], self)
        else: 
            return layer.load()

    def _read_header(self): 

        f = self.buffer
        ilast = f.last()

        self.models = {}
        self.thickness = np.Inf

        while f.tell() < ilast: 
            sid, nbytes = f.header()
            if sid == 0: 
                self.name = f.read(nbytes)[0:-1].decode("utf-8")
            elif sid == 1: 
                self.version = str(f.lf_int()) + '.' + str(f.lf_int())
            elif sid == 2: 
                self.nlayers = f.lf_int()
            elif sid == 3: 
                self.box = Box(f)
            elif sid == 4: 
                model = ModelInfo(f, nbytes)
                self.thickness = min(self.thickness, model.thickness)
                self.models[model.id] = model
            elif sid == 5: 
                self.iseek = f.lf_int()
            elif sid == 6: 
                self.comment = f.read(nbytes).decode("utf-16")
            else: 
                raise UknownSectionException(sid)

    def _read_seek_table(self): 
        
        f = self.buffer
        ilast = f.last()

        while f.tell() < ilast: 
            sid = f.lf_int()
            assert(sid == 0)
            self.layers += [LayerPointer(self)]

    def __str__(self): 
        return "Name: {}\nVersion: {}\nNumber of Layers: {}\nComment: {}\nBox: \n{}\n".format(self.name, self.version, self.nlayers, self.comment, self.box) 


class PolygonType(Enum): 
    OUTLOOP = 0
    INLOOP = 1
    SUPPORT = 2 

class PolygonFormat(Enum):
    CLOSED = 0
    OPEN = 1
    DASHED = 2

    def construct(self, model, points): 

        return {
            PolygonFormat.CLOSED: ClosedLine, 
            PolygonFormat.OPEN: OpenLine,
            PolygonFormat.DASHED: DashedLine
            }[self](model, [points])


class ClusterType(Enum): 
    MODEL = 0
    SUPPORT = 1
    WEB = 2

    def construct(self, model, polygons, buffer): 

        if self == ClusterType.MODEL: 
            poly_type, _, n = polygons.pop(0)
            assert(poly_type == PolygonType.OUTLOOP)
            points = [buffer.get(n)] + [buffer.get(n) for poly_type, poly_format, n in polygons]
            return [ModelCluster(model, points)]
        elif self == ClusterType.WEB:
            return [poly_format.construct(model, buffer.get(n)) for poly_type, poly_format, n in polygons]
        else: 
            raise Exception("Does not yet support type {}".format(self)) 

class Shape: 

    def __init__(self, model, points):
        self.model = model 
        self.points = points

    def transform(self, func): 
        return type(self)(
            self.model, 
            [np.stack(func(elem[:, 0], elem[:, 1]), axis=1) for elem in self.points]
            )

    def asint(self):
        return type(self)( 
            self.model, 
            [np.round(elem).astype(np.int32) for elem in self.points]
            )

    def box(self): 

        minval = (
            min([elem[:, 0].min() for elem in self.points]),
            min([elem[:, 1].min() for elem in self.points]), 
            0.0
        )

        maxval = (
            max([elem[:, 0].max() for elem in self.points]),
            max([elem[:, 1].max() for elem in self.points]), 
            0.0
        )

        return Box(min=minval, max=maxval)

    def mask(self, res, color=False, filled=True): 
        output = np.zeros((res[0], res[1]), dtype=np.uint8)
        self.asint().plot(output, 255, filled=filled)
        if color: return cv2.cvtColor(output, cv2.COLOR_GRAY2RGB)
        return output


class ModelCluster(Shape): 

    def plot(self, img, color, filled=True):
        if filled: 
            cv2.fillPoly(img, self.points, color)
        else:
            cv2.polylines(img, self.points, True, color)

    def shapely(self): 
        return geo.Polygon(self.points[0], self.points[1:])

    def path(self): 
        gen = ([Path.MOVETO] + [Path.LINETO] * (elem.shape[0] - 1) + [Path.CLOSEPOLY] for elem in self.points)
        p = [np.concatenate([elem, np.expand_dims(elem[-1, :], axis=0)]) for elem in self.points]
        return Path(np.concatenate(p), [elem for vec in gen for elem in vec])
       

class ClosedLine(Shape): 

    def plot(self, img, color, filled):
        cv2.polylines(img, self.points[0], True, color)

class OpenLine(Shape): 

    def plot(self, img, color, filled):
        for p in self.points[0]: 
            cv2.circle(img, (p[0], p[1]), 1, color) 

class DashedLine(Shape): 

    def plot(self, img, color, filled):
        for i in range(0, len(self.points[0]), 2):
            cv2.polylines(img, [self.points[0][i:i + 2]], False, color)


class LayerList(list): 

    def __init__(self, *argv):
        super().__init__(*argv)
        self.z = None
        for elem in self: 
            self.z = elem.z
            break

    def append(self, element): 
        super().append(element)
        if self.z is None: self.z = element.z

    def transform(self, func): 
        return LayerList([elem.transform(func) for elem in self])
        
    def asint(self): 
        return LayerList([elem.asint() for elem in self])

    def filter(self, *argv): 
        return LayerList([elem.filter(*argv) for elem in self])

    def mask(self, res): 
        output = np.zeros((res[0], res[1]), dtype=np.uint8)
        for index, part in enumerate(self): 
            for elem in part.shapes: elem.asint().plot(output, color=(index + 1), filled=True)
        return output

class Layer: 

    def __init__(self, z, shapes, part=None):
        self.z = z
        self.shapes = shapes
        self.part = part

    def __add__(self, other):
        if other is None: return self 
        return Layer(self.z, self.shapes + other.shapes)

    def transform(self, func): 
        return Layer(self.z, [elem.transform(func) for elem in self.shapes], self.part)

    def asint(self): 
        return Layer(self.z, [elem.asint() for elem in self.shapes])

    def filter(self, *argv): 
        include = set(argv)
        return Layer(self.z, [elem for elem in self.shapes if type(elem) in include], self.part)

    def __iter__(self): 
        for elem in self.shapes: yield elem

    def __getitem__(self, key): 
        return self.shapes[key]

    def mask(self, res, color=False, filled=True): 
        output = np.zeros((res[0], res[1]), dtype=np.uint8)
        for elem in self.shapes: elem.asint().plot(output, color=255, filled=filled)
        if color: return cv2.cvtColor(output, cv2.COLOR_GRAY2RGB)
        return output

    def plot(self, img, color, filled=False): 
        for elem in self.shapes: elem.asint().plot(img, color=color, filled=filled)

    def show(self, res):
        img = self.mask(res, color=True)
        cv2.putText(img, "%.2f" % self.z, (0, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,  (255, 255, 255), 1, cv2.LINE_AA, False)
        cv2.imshow("Layer", img)

class LayerPointer: 

    def __init__(self, parent): 

        f = parent.buffer
        self.parent = parent
        ilast = f.last()

        while f.tell() < ilast: 
            sid, nbytes = f.header()
            if sid == 0: 
                self.z = f.lf_float()
            elif sid == 1: 
                self.index = f.lf_int()
            else: 
                raise UknownSectionException(sid)

    def load(self): 
        self.parent.buffer.seek(self.index)
        sid = self.parent.buffer.lf_int()
        assert(sid == 2)
        return self.parent.buffer.layer(self.parent)

    def show(self): 
        self.load().show()

class Box: 

    def __init__(self, f=None, min=None, max=None):
        if f is None: 
            self.min = min
            self.max = max 
        else: 
            self.min = np.array(f.lf_float(3))
            self.max = np.array(f.lf_float(3))

    def copy(self): 
        return Box(min=self.min.copy(), max=self.max.copy())

    def __str__(self): 
        return "x: {} --> {} \ny: {} --> {} \nz: {} --> {}".format(self.min[0], self.max[0], self.min[1], self.max[1], self.min[2], self.max[2])

    def __add__(self, other): 
        return Box(min=np.minimum(self.min, other.min), max=np.maximum(self.max, other.max))

    def toimage(self, height=None, width=None): 
        
        if height is None and width is None: 
            raise Exception("Either height or width must be defined")
        if height is None: 
            dx = width / (self.max[0] - self.min[0])
            dy = dx
            pixels = (int(dx * (self.max[1] - self.min[1])), width)
        elif width is None: 
            dy = height / (self.max[1] - self.min[1])
            dx = dy
            pixels = (height, int(dy * (self.max[0] - self.min[0])))
        else: 
            dx = width / (self.max[0] - self.min[0])
            dy = height / (self.max[1] - self.min[1])
            pixels = (height, width)
     
        return lambda x, y: ( dx * (x - self.min[0]), pixels[0] - dy * (y - self.min[1]) ), pixels

    def transform(self, func): 

        x1, y1 = func(self.min[0], self.min[1])
        z1 = self.min[2]

        x2, y2 = func(self.max[0], self.max[1])
        z2 = self.max[2]

        x = sorted([x1, x2])
        y = sorted([y1, y2])
        return Box(min=np.array([x[0], y[0], z1]), max=np.array([x[1], y[1], z2]))


class ModelInfo: 

    def __init__(self, f, nbytes): 

        ilast = f.tell() + nbytes

        while f.tell() < ilast: 
            sid, nbytes = f.header()
            if sid == 0: 
                self.id = f.lf_int()
            elif sid == 1: 
                self.name = f.read(nbytes).decode("utf-16")
            elif sid == 2: 
                self.box = Box(f)
            elif sid == 3: 
                assert(nbytes == 4)
                self.thickness = f.lf_float()
            else: 
                raise UknownSectionException(sid)

    def __str__(self):  
        return "Name: {}\nIdentifier: {}\nLayer Thickness: {}\nBox: \n{}\n".format(self.name, self.id, self.thickness, self.box) 

class ByteStream(io.BufferedReader): 
    '''Utility to read clf file datatypes

    The CLF file format features some strange data format features. 
    This utility can be used to read raw bytes but also to read out lf_number and lf_float types. 
    
    Example: 
    >> stream = ByteStream(filename)
    >> sid, num = stream.header() # read section identifier and number of bytes
    >> my_int = stream.lf_int() # read lf_number type
    >> print(stream.nread) # see number of bytes read
    >> stream.close() 
    '''

    def __init__(self, filename, buffer=1024): 
        if type(filename) is str: 
            file = io.FileIO(filename)
        elif type(filename) is io.BytesIO: 
            file = filename
        elif type(filename) is bytes: 
            file = io.BytesIO(filename)
        else: 
            raise Exception('Unsupported input type')
        super().__init__(file, buffer * 8)

    def lf_int(self, n=None):

        if n is None:  
            b0 = self.read(1)
            n = b0[0] >> 5
            b = bytes([b0[0] & 0x1F]) + self.read(n)
            return int.from_bytes(b, "big")
        else: 
            return [self.lf_int() for i in range(n)]

    def lf_float(self, n=None):
        if n is None: 
            b = self.read(4)
            output = struct.unpack('f', b)[0]
            return output
        else: 
            return [self.lf_float() for i in range(n)]

    def skip(self): 
        n = self.lf_int()
        self.seek(self.tell() + n)

    def header(self): 
        tag = self.lf_int()
        num = self.lf_int() 
        return tag, num

    def last(self): 
        return self.lf_int() + self.tell()

    def polygon(self): 

         # Type
        sid, nbytes = self.header()
        assert(sid == 0)
        poly_type = PolygonType(self.lf_int())

        # Format
        sid, nbytes = self.header()
        assert(sid == 1)
        poly_format = PolygonFormat(self.lf_int())

        # Compression
        sid, nbytes = self.header()
        if sid == 2: 
            self.lf_int()
            sid, nbytes = self.header()

        # Number of Points
        assert(sid == 3)
        n = self.lf_int()

        return poly_type, poly_format, n

    def cluster(self): 

        ilast = self.last()

        # Model
        sid, nbytes = self.header()
        assert(sid == 0)
        i_model = self.lf_int()

        # Type
        sid, nbytes = self.header()
        assert(sid == 1)
        cluster_type = ClusterType(self.lf_int())

        # Polygons
        polygons = []
        while self.tell() < ilast: 
            sid, nbytes = self.header()
            assert(sid == 2)
            polygons += [self.polygon()]

        return i_model, cluster_type, polygons

    def layer(self, parent): 

        ilast = self.last()

        n = None
        
        clusters = []
        points = None
        while self.tell() < ilast: 
            sid = self.lf_int()
            if sid == 0: 
                nbytes = self.lf_int()
                z = self.lf_float()
            elif sid == 1: 
                nbytes = self.lf_int()
                n = self.lf_int()
            elif sid == 2: 
                clusters.append(self.cluster())
            elif sid == 3: 
                if n is None: raise Exception("Number of points not set")
                points = PointBuffer(self, n)
            else: 
                raise UknownSectionException(sid)

        if points is None: raise Exception("Points not read")
        shapes = [elem for i_model, cluster_type, polygons in clusters for elem in cluster_type.construct(parent.models[i_model], polygons, points)] 
        return Layer(z, shapes, parent)

class UknownSectionException(Exception): 
    def __init__(self, sid): 
        super().__init__("Uknown section identifier: " + str(sid))

class PointBuffer: 

    def __init__(self, f, n): 
        self.nread = 0
        ilast = f.last()
        self.points = [(f.lf_float(), f.lf_float()) for i in range(n)]
        assert(f.tell() == ilast)
    
    def get(self, n): 
        iend = self.nread + n
        out = np.array(self.points[self.nread:iend])
        self.nread = iend
        return out

if __name__ == "__main__": 
    #filename = sys.argv[1]
    build = Build("C:/Data/Cups/Models/Cup body Voronoi_%i/Part.clf", range(1, 49))
    (func, res) = build.box.toimage(1024)
    for layer in build:
        layer.filter(ModelCluster).transform(func).show(res)
        if cv2.waitKey(20) and 0xFF == ord('q'):
            break
     
    cv2.destroyAllWindows()