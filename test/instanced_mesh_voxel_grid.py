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
            instance_colors: List[np.ndarray] | None = None,
        ):
        """
        Args:
            geometry: The geometry of the instanced mesh.
            material: The material of the instanced mesh.
            instance_matrices (np.ndarray, dtype=float, shape=(N, 4, 4)): The instance transformation matrices.
            instance_colors (np.ndarray, dtype=float, shape=(N, 3)): The instance colors.
        """
        super(InstancedMesh, self).__init__(geometry, material)
        self._type = "InstancedMesh"

        # Convert list of matrices to msgpack
        self.instance_matrices = instance_matrices
        self.instances_matrices_msg = self.ConvertMatricesNumpyToMsgpack(self.instance_matrices)

        # Create color data to msgpack
        if instance_colors is None:
            # Default color to all white
            instance_colors: np.ndarray = np.ones((len(self.instance_matrices), 3), dtype=np.float32)  # (N, 3)
        self.instance_colors_msg = self.ConvertColorsNumpyToMsgpack(instance_colors)

    @staticmethod
    def ConvertMatricesNumpyToMsgpack(matrices: List[np.ndarray]) -> umsgpack.Ext:
        matrices_data = []
        for matrix in matrices:
            matrices_data.extend(matrix.flatten(order='F'))
        matrices_data = np.array(matrices_data, dtype=np.float32)
        typename, extcode = g.threejs_type(matrices_data.dtype)
        return umsgpack.Ext(extcode, matrices_data.tobytes('F'))

    @staticmethod
    def ConvertColorsNumpyToMsgpack(colors: np.ndarray) -> umsgpack.Ext:
        colors_data = colors.ravel()
        typename, extcode = g.threejs_type(colors_data.dtype)
        return umsgpack.Ext(extcode, colors_data.tobytes('F'))

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
instance_matrices = np.empty((27, 4, 4), dtype=np.float32)
i = 0
for z in range(3):  # 3 layers
    z_pos = z * 0.3
    for y in range(3):  # 3 rows
        y_pos = y * 0.3
        for x in range(3):  # 3 columns
            x_pos = x * 0.3

            # Create 4x4 transformation matrix for each cube
            instance_matrices[i] = np.eye(4)
            instance_matrices[i, 0:3, 3] = [x_pos, y_pos, z_pos]
            i += 1

instance_colors = np.vstack([
    np.repeat([[1.0, 0.0, 0.0]], 9, axis=0),  # (9, 3)
    np.repeat([[0.0, 1.0, 0.0]], 9, axis=0),  # (9, 3)
    np.repeat([[0.0, 0.0, 1.0]], 9, axis=0),  # (9, 3)
])  # (27, 3)

instance_colors = np.array(instance_colors, dtype=np.float32)
instance_colors_msg = InstancedMesh.ConvertColorsNumpyToMsgpack(instance_colors)

# Create the instanced mesh object

geometry = g.Box([0.2, 0.2, 0.2])
material = g.MeshPhongMaterial(side=2, transparent=True, opacity=0.5)
instanced_mesh = InstancedMesh(geometry, material, instance_matrices, instance_colors=None)

vis[u"instanced_cubes"].set_object(instanced_mesh)

time.sleep(1)

vis[u"instanced_cubes/<object>"].set_property("array", instance_colors_msg)

time.sleep(100)
exit()
# The visualization will be available at http://localhost:7000/static/
