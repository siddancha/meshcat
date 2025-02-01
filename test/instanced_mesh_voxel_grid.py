from typing import List
import meshcat
import meshcat.geometry as g
import numpy as np
import time
import umsgpack


class InstancedMesh(g.Object):
    def __init__(
            self, 
            geometry: g.Geometry, 
            material: g.Material,
            instance_matrices: List[np.ndarray],
        ):
        super(InstancedMesh, self).__init__(geometry, material)
        self._type = "InstancedMesh"

        self.instance_matrices = instance_matrices

        # Convert list of matrices to a single numpy array
        self.instances_matrices_data = []
        for matrix in instance_matrices:
            self.instances_matrices_data.extend(matrix.flatten(order='F'))

        self.instances_matrices_data = np.array(self.instances_matrices_data, dtype=np.float32)

        typename, extcode = g.threejs_type(self.instances_matrices_data.dtype)
        self.instances_matrices_msg = umsgpack.Ext(extcode, self.instances_matrices_data.tobytes('F'))

        # Create color data
        self.instance_colors_data = np.ones((len(self.instance_matrices) * 3,), dtype=np.float32)
        typename, extcode = g.threejs_type(self.instance_colors_data.dtype)
        self.instance_colors_msg = umsgpack.Ext(extcode, self.instance_colors_data.tobytes('F'))

    def lower(self):
        data = {
            u"metadata": {
                u"version": 4.5,
                u"type": u"Object",
            },
            u"geometries": [],
            # Do not set color of the material
            u"materials": [
                {
                    u"uuid": self.material.uuid, 
                    u"type": self.material._type,
                    u"side": self.material.side,
                    u"transparent": self.material.transparent,
                    u"opacity": self.material.opacity,
                }
            ],
            u"object": {
                u"uuid": self.uuid,
                u"type": self._type,
                u"geometry": self.geometry.uuid,
                u"material": self.material.uuid,
                u"instanceMatrix": {
                    u"type": u"InstancedBufferAttribute",
                    u"array": self.instances_matrices_msg
                },
                u"instanceColor": {
                    u"type": u"InstancedBufferAttribute",
                    u"itemSize": 3,
                    u"array": self.instance_colors_msg,
                    u"needsUpdate": True,
                },
                u"count": len(self.instance_matrices)
            }
        }
        self.geometry.lower_in_object(data)
        # self.material.lower_in_object(data)
        return data

# Create a visualizer
vis = meshcat.Visualizer()

# Create a 3x3x3 grid of cubes using instanced mesh
# Each cube is 0.2 units in size with 0.2 unit spacing

# Create the instance matrices for 27 cubes (3x3x3 grid)
instance_matrices = []
for z in range(3):  # 3 layers
    z_pos = z * 0.3
    for y in range(3):  # 3 rows
        y_pos = y * 0.3
        for x in range(3):  # 3 columns
            x_pos = x * 0.3

            # Create 4x4 transformation matrix for each cube
            matrix = np.eye(4)
            matrix[0:3, 3] = [x_pos, y_pos, z_pos]
            instance_matrices.append(matrix)


# Create the instanced mesh object

geometry = g.Box([0.2, 0.2, 0.2])
material = g.MeshPhongMaterial(side=2, transparent=True, opacity=0.5)
instanced_mesh = InstancedMesh(geometry, material, instance_matrices)

vis["sid"].set_object(instanced_mesh)

instance_colors = np.vstack([
    np.repeat([[1.0, 0.0, 0.0]], 9, axis=0),
    np.repeat([[0.0, 1.0, 0.0]], 9, axis=0),
    np.repeat([[0.0, 0.0, 1.0]], 9, axis=0),
])

instance_colors = np.array(instance_colors, dtype=np.float32)
instance_colors = instance_colors.ravel()
# instance_colors = umsgpack.Ext(0x17, instance_colors.tobytes('F'))
packed_array = g.pack_numpy_array(instance_colors.T)
packed_array['needsUpdate'] = True

vis["sid/<object>"].set_property(u"instanceColor.array", packed_array['array'])
vis["sid/<object>"].set_property(u"instanceColor.needsUpdate", True)
vis["sid/<object>"].set_property(u"needsUpdate", True)


time.sleep(10)

# The visualization will be available at http://localhost:7000/static/
