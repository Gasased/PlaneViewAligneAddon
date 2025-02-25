bl_info = {
    "name": "Plane Align View and Empty",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > N-Panel > Your Panel",
    "description": "Aligns viewport to a plane defined by 3 selected vertices and creates a parent Empty.",
    "category": "Object",
}

import bpy
from mathutils import Vector, Matrix, Quaternion
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

        # Store original view rotation
        context.scene.plane_align_original_view_rotation = region_3d.view_rotation[:]

        rotation_quat = plane_normal.to_track_quat('-Z', 'Y')
        region_3d.view_rotation = rotation_quat

        return {'FINISHED'}

class PlaneAlignOperator(bpy.types.Operator):
    """Align Viewport and Create Empty based on 3 Vertices"""
    bl_idname = "object.plane_align_view_empty"
    bl_label = "Plane Align View & Empty"
    bl_options = {'REGISTER', 'UNDO'}

    reset_empty: bpy.props.BoolProperty(
        name="Reset Empty Loc/Rot",
        description="Reset the Empty's location and rotation after creation",
        default=False
    )

    parent_type: bpy.props.EnumProperty(
        name="Parent Type",
        description="Type of parenting to use",
        items=[
            ('OBJECT', "Object", "Standard parenting, keeps world transform"),
            ('KEEP_TRANSFORM', "Object (Keep Transform)", "Same as Object, keeps world transform"),
            ('WITHOUT_INVERSE', "Object (Without Inverse)", "Parent without applying inverse, changes world transform"),
            ('KEEP_TRANSFORM_WITHOUT_INVERSE', "Object (Keep Transform Without Inverse)", "Parent without inverse but adjust to keep world transform"),
        ],
        default='OBJECT'
    )

    def execute(self, context):
        # Get the active object and ensure it's in Edit Mode
        obj = context.active_object
        if obj is None or obj.mode != 'EDIT':
            self.report({'ERROR_INVALID_CONTEXT'}, "Please be in Edit Mode with an active object.")
            return {'CANCELLED'}

        # Access the mesh and selected vertices
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        selected_verts = [v for v in bm.verts if v.select]
        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

        # Check for exactly 3 selected vertices
        if len(selected_verts) != 3:
            self.report({'ERROR_INVALID_INPUT'}, "Please select exactly 3 vertices.")
            return {'CANCELLED'}

        # Calculate world positions of the selected vertices
        v1_world = obj.matrix_world @ selected_verts[0].co
        v2_world = obj.matrix_world @ selected_verts[1].co
        v3_world = obj.matrix_world @ selected_verts[2].co

        # Calculate the plane normal and center
        vec1 = v2_world - v1_world
        vec2 = v3_world - v1_world
        plane_normal = vec1.cross(vec2).normalized()
        plane_center = (v1_world + v2_world + v3_world) / 3

        # Set the 3D cursor to the average location of the selected vertices
        context.scene.cursor.location = plane_center

        # Ensure we're in a 3D viewport
        region_3d = context.region_data
        if region_3d is None:
            self.report({'ERROR_INVALID_CONTEXT'}, "Not in a 3D viewport.")
            return {'CANCELLED'}

        # Store the original view rotation for potential restoration
        context.scene.plane_align_original_view_rotation = region_3d.view_rotation[:]

        # Align the view to the plane
        rotation_quat = plane_normal.to_track_quat('-Z', 'Y')
        region_3d.view_rotation = rotation_quat

        # Switch to Object Mode and create the Empty at the 3D cursor
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD')
        empty = context.active_object
        empty.rotation_euler = rotation_quat.to_euler()

        # Parent the original object to the Empty
        if obj != empty:  # Safety check to avoid parenting the Empty to itself
            if self.parent_type in ('OBJECT', 'KEEP_TRANSFORM'):
                obj.parent = empty
            elif self.parent_type == 'WITHOUT_INVERSE':
                obj.parent = empty
                obj.matrix_parent_inverse = Matrix.Identity(4)
            elif self.parent_type == 'KEEP_TRANSFORM_WITHOUT_INVERSE':
                world_matrix = obj.matrix_world.copy()
                obj.parent = empty
                obj.matrix_parent_inverse = Matrix.Identity(4)
                obj.matrix_basis = empty.matrix_world.inverted() @ world_matrix

        # Optionally reset the Empty's location and rotation
        if self.reset_empty:
            empty.location = (0, 0, 0)
            empty.rotation_euler = (0, 0, 0)

        return {'FINISHED'}

class RestoreViewOperator(bpy.types.Operator):
    """Restore Viewport to Original Rotation"""
    bl_idname = "object.restore_view_rotation"
    bl_label = "Restore View Rotation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        original_rotation = context.scene.plane_align_original_view_rotation
        if original_rotation and sum(original_rotation) != 0:
            context.region_data.view_rotation = Quaternion(original_rotation)
        else:
            self.report({'WARNING'}, "Original view rotation not set.")
        return {'FINISHED'}

class PlaneAlignPanel(bpy.types.Panel):
    """Panel in the N-Panel to run the Plane Align Operators"""
    bl_label = "Plane Align Tools"
    bl_idname = "VIEW3D_PT_plane_align"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MyTools"

    def draw(self, context):
        layout = self.layout
        layout.operator(AlignViewOperator.bl_idname)
        layout.prop(context.scene, "plane_align_parent_type", text="Parent Type")
        layout.prop(context.scene, "plane_align_reset_empty", text="Reset Empty")
        op = layout.operator(PlaneAlignOperator.bl_idname)
        op.reset_empty = context.scene.plane_align_reset_empty
        op.parent_type = context.scene.plane_align_parent_type
        layout.operator(RestoreViewOperator.bl_idname)

def register():
    bpy.utils.register_class(AlignViewOperator)
    bpy.utils.register_class(PlaneAlignOperator)
    bpy.utils.register_class(RestoreViewOperator)
    bpy.utils.register_class(PlaneAlignPanel)
    bpy.types.Scene.plane_align_reset_empty = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.plane_align_parent_type = bpy.props.EnumProperty(
        name="Parent Type",
        description="Type of parenting to use",
        items=[
            ('OBJECT', "Object", "Standard parenting, keeps world transform"),
            ('KEEP_TRANSFORM', "Object (Keep Transform)", "Same as Object, keeps world transform"),
            ('WITHOUT_INVERSE', "Object (Without Inverse)", "Parent without applying inverse, changes world transform"),
            ('KEEP_TRANSFORM_WITHOUT_INVERSE', "Object (Keep Transform Without Inverse)", "Parent without inverse but adjust to keep world transform"),
        ],
        default='OBJECT'
    )
    bpy.types.Scene.plane_align_original_view_rotation = bpy.props.FloatVectorProperty(size=4, default=(1.0, 0.0, 0.0, 0.0))

def unregister():
    bpy.utils.unregister_class(AlignViewOperator)
    bpy.utils.unregister_class(PlaneAlignOperator)
    bpy.utils.unregister_class(RestoreViewOperator)
    bpy.utils.unregister_class(PlaneAlignPanel)
    del bpy.types.Scene.plane_align_reset_empty
    del bpy.types.Scene.plane_align_parent_type
    del bpy.types.Scene.plane_align_original_view_rotation

if __name__ == "__main__":
    register()