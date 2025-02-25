bl_info = {
    "name": "Align View to Plane",
    "author": "gssd",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > N-Panel > View",
    "description": "Aligns the viewport to a plane defined by 3 selected vertices.",
    "category": "View",
}

import bpy
from mathutils import Vector, Quaternion
import bmesh

class AlignViewOperator(bpy.types.Operator):
    """Align Viewport to Plane Defined by 3 Selected Vertices"""
    bl_idname = "object.align_view_to_plane"
    bl_label = "Align View to Plane"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.mode != 'EDIT':
            self.report({'ERROR_INVALID_CONTEXT'}, "Please be in Edit Mode with an active object.")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        selected_verts = [v for v in bm.verts if v.select]
        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

        if len(selected_verts) != 3:
            self.report({'ERROR_INVALID_INPUT'}, "Please select exactly 3 vertices.")
            return {'CANCELLED'}

        v1_world = obj.matrix_world @ selected_verts[0].co
        v2_world = obj.matrix_world @ selected_verts[1].co
        v3_world = obj.matrix_world @ selected_verts[2].co

        vec1 = v2_world - v1_world
        vec2 = v3_world - v1_world
        plane_normal = vec1.cross(vec2).normalized()

        region_3d = context.region_data
        if region_3d is None:
            self.report({'ERROR_INVALID_CONTEXT'}, "Not in a 3D viewport.")
            return {'CANCELLED'}

        rotation_quat = plane_normal.to_track_quat('-Z', 'Y')
        region_3d.view_rotation = rotation_quat

        return {'FINISHED'}

class PlaneAlignPanel(bpy.types.Panel):
    """Panel in the N-Panel to align view to plane"""
    bl_label = "Align View to Plane"
    bl_idname = "VIEW3D_PT_plane_align"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "View"

    def draw(self, context):
        layout = self.layout
        layout.operator(AlignViewOperator.bl_idname)

def register():
    bpy.utils.register_class(AlignViewOperator)
    bpy.utils.register_class(PlaneAlignPanel)

def unregister():
    bpy.utils.unregister_class(AlignViewOperator)
    bpy.utils.unregister_class(PlaneAlignPanel)

if __name__ == "__main__":
    register()