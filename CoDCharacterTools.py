#   Copyright (C) 2023  Kyle Wood
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import webbrowser
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pymel
import CoDMayaTools
import SEToolsPlugin

def error( message ):
    cmds.confirmDialog( title = "An error has occurred", message = message )

def confirm_dialog( message ):
    cmds.confirmDialog( title = "Confirmation", message = message )

def prompt_dialog( title, message ):
    result = cmds.promptDialog( title = title, message = message, button = ["Confirm", "Cancel"], defaultButton = "Confirm", cancelButton = "Cancel" )

    if result == "Confirm":
        return cmds.promptDialog( query = True, text = True )

    return None

def remove_namespaces():
    if pymel.listNamespaces( recursive = True, internal = False ):
        namespaces = []

        for namespace in pymel.listNamespaces( recursive = True, internal = False ):
            namespaces.append( namespace )

        for namespace in reversed( namespaces ):
            pymel.namespace( removeNamespace = namespace, mergeNamespaceWithRoot = True )

        namespaces[:] = []

def set_attribute( node, attribute, value ):
    if cmds.objExists( node ):
        if cmds.objExists( node + "." + attribute ):
            cmds.setAttr( node + "." + attribute, value )

def get_groups():
    groups = []

    for node in get_joints() + get_meshes():
        parent = cmds.listRelatives( node, parent = True, fullPath = True )

        if not parent == None:
            if len( parent ) > 0:
                parent = parent[0].split( "|" )[1]

                if parent not in groups:
                    groups.append( parent )

    return groups

def get_joints():
    return cmds.ls( type = "joint" )

def get_meshes():
    return cmds.ls( "*SEModelMesh*" )

def get_skinclusters():
    return cmds.ls( type = "skinCluster" )

def get_skincluster_for_mesh( mesh ):
    return mel.eval( "findRelatedSkinCluster " + mesh )

def get_selection():
    return cmds.ls( selection = True )

def enable_move_joints( enable = False ):
    for skinCluster in get_skinclusters():
        cmds.skinCluster( skinCluster, edit = True, moveJointsMode = enable )

def enable_x_ray( enable = True ):
    if enable:
        mel.eval( 'modelEditor -e -jointXray true modelPanel4' )
    else:
        mel.eval( 'modelEditor -e -jointXray false modelPanel4' )

def create_joint_attributes( joint ):
    joint_attributes = {
        "name": joint.split( "|" )[-1].split( ":" )[-1],
        "parent": cmds.listRelatives( joint, parent = True )[0],
        "translateX": cmds.getAttr( joint + ".translateX" ),
        "translateY": cmds.getAttr( joint + ".translateY" ),
        "translateZ": cmds.getAttr( joint + ".translateZ" ),
        "rotateX": cmds.getAttr( joint + ".rotateX" ),
        "rotateY": cmds.getAttr( joint + ".rotateY" ),
        "rotateZ": cmds.getAttr( joint + ".rotateZ" ),
        "jointOrientX": cmds.getAttr( joint + ".jointOrientX" ),
        "jointOrientY": cmds.getAttr( joint + ".jointOrientY" ),
        "jointOrientZ": cmds.getAttr( joint + ".jointOrientZ" ),
        "translateXWorld": cmds.xform( joint, query = True, worldSpace = True, translation = True )[0],
        "translateYWorld": cmds.xform( joint, query = True, worldSpace = True, translation = True )[1],
        "translateZWorld": cmds.xform( joint, query = True, worldSpace = True, translation = True )[2],
        "rotateXWorld": cmds.xform( joint, query = True, worldSpace = True, rotation = True )[0],
        "rotateYWorld": cmds.xform( joint, query = True, worldSpace = True, rotation = True )[1],
        "rotateZWorld": cmds.xform( joint, query = True, worldSpace = True, rotation = True )[2]
    }

    return joint_attributes

def create_new_rig( namespace, joints_with_attributes ):
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Abort if something goes wrong
    if len( cmds.ls( "*" + namespace + ":" + "*" ) ) > 0:
        error( "This namespace already exists!" )
        return

    if len( namespace ) < 1:
        error( "No namespace given!" )
        return

    if len( joints_with_attributes ) < 1:
        error( "No joint attributes given!" )
        return

    # Create namespace for combined joints
    cmds.namespace( add = namespace )

    # Create new joints
    for joint_with_attributes in joints_with_attributes:
        cmds.select( deselect = True )
        cmds.joint( name = namespace + ":" + joint_with_attributes["name"] )
        cmds.select( deselect = True )

    # Parent them
    for joint_with_attributes in joints_with_attributes:
        if "Joints" not in joint_with_attributes["parent"]:
            cmds.parent( namespace + ":" + joint_with_attributes["name"], namespace + ":" + joint_with_attributes["parent"] )
            cmds.select( deselect = True )

    # Group them
    for joint_with_attributes in joints_with_attributes:
        if "Joints" in joint_with_attributes["parent"]:
            cmds.group( namespace + ":" + joint_with_attributes["name"], name = namespace + ":Joints" )
    
    # Deselect after grouping
    cmds.select( deselect = True )

    # Set attributes
    for joint_with_attributes in joints_with_attributes:
        if cmds.objExists( namespace + ":" + joint_with_attributes["name"] ):
            set_attribute( namespace + ":" + joint_with_attributes["name"], "translateX", joint_with_attributes["translateX"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "translateY", joint_with_attributes["translateY"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "translateZ", joint_with_attributes["translateZ"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "rotateX", joint_with_attributes["rotateX"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "rotateY", joint_with_attributes["rotateY"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "rotateZ", joint_with_attributes["rotateZ"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "jointOrientX", joint_with_attributes["jointOrientX"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "jointOrientY", joint_with_attributes["jointOrientY"] )
            set_attribute( namespace + ":" + joint_with_attributes["name"], "jointOrientZ", joint_with_attributes["jointOrientZ"] )

def get_joints_with_attributes( input = [] ):
    joints_with_attributes = []

    if len( input ) > 0:
        joints = input
    else:
        joints = get_joints()

    # Add the ones that have tag_origin first, because those are correct rotations
    for joint in joints:
        joint_path = cmds.ls( joint, long = True )[0]

        if cmds.nodeType( joint_path ) == "joint":
            if "tag_origin" in cmds.listRelatives( joint_path, parent = True, fullPath = True )[0]:
                joint_attributes = create_joint_attributes( joint_path )

                # Only append this joint if it hasn't been already
                jointAdded = False

                for index in range( len( joints_with_attributes ) ):
                    if joints_with_attributes[index]["name"] == joint_path.split( "|" )[-1].split( ":" )[-1]:
                        jointAdded = True

                if not jointAdded:
                    joints_with_attributes.append( joint_attributes )

    # Do it again without the condition, rest will be added now
    for joint in joints:
        joint_path = cmds.ls( joint, long = True )[0]

        if cmds.nodeType( joint_path ) == "joint":
            joint_attributes = create_joint_attributes( joint_path )

            # Only append this joint if it hasn't been already
            jointAdded = False

            for index in range( len( joints_with_attributes ) ):
                if joints_with_attributes[index]["name"] == joint_path.split( "|" )[-1].split( ":" )[-1]:
                    jointAdded = True

            if not jointAdded:
                joints_with_attributes.append( joint_attributes )

    return joints_with_attributes

def get_mirror_joint_attributes( joint_to_mirror ):
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Stop if joint doesn't exist
    if not cmds.objExists( joint_to_mirror ):
        error( "That joint doesn't exist!" )
        return

    suffix = None

    # Store joint suffix
    if joint_to_mirror.endswith( "_le" ):
        suffix = "_le"
    elif joint_to_mirror.endswith( "_left" ):
        suffix = "_left"
    elif joint_to_mirror.endswith( "_ri" ):
        suffix = "_ri"
    elif joint_to_mirror.endswith( "_right" ):
        suffix = "_right"

    if suffix == None:
        error( "Can't mirror this joint!" )
        return

    # Create namespaces
    cmds.namespace( add = "ORIGINAL" )
    cmds.namespace( add = "MIRRORED" )

    # Add namespaces to joints
    for joint in get_joints():
        cmds.rename( joint, "ORIGINAL:" + joint )

    # Mirror the given joint
    cmds.select( "ORIGINAL:" + joint_to_mirror )
    mel.eval( 'mirrorJoint -mirrorXZ -mirrorBehavior -searchReplace "ORIGINAL:" "MIRRORED:"' )

    # Store mirrored joint
    mirrored_joint = cmds.ls( selection = True, long = True )[0]
    cmds.select( deselect = True )

    # Create array for mirrored joints
    joints = [ mirrored_joint ]

    # Store all mirrored joints
    for joint in cmds.listRelatives( mirrored_joint, allDescendents = True, fullPath = True ):
        joint_path = cmds.ls( joint, long = True )[0]
        joints.append( joint_path )

    # Store attributes for mirrored joints
    joints_with_attributes = get_joints_with_attributes( joints )

    # Delete mirrored joints
    cmds.delete( mirrored_joint )

    # Remove namespaces
    remove_namespaces()

    # Flip the names
    for joint_with_attributes in joints_with_attributes:
        if suffix == "_le":
            joint_with_attributes["name"] = joint_with_attributes["name"].replace( "_le", "_ri" )
        elif suffix == "_left":
            joint_with_attributes["name"] = joint_with_attributes["name"].replace( "_left", "_right" )
        elif suffix == "_ri":
            joint_with_attributes["name"] = joint_with_attributes["name"].replace( "_ri", "_le" )
        elif suffix == "_right":
            joint_with_attributes["name"] = joint_with_attributes["name"].replace( "_right", "_left" )

    return joints_with_attributes

def get_rig_name( semodel ):
    semodel_name = os.path.splitext( semodel )[0]
    type = semodel_name.split( "_" )

    rig_types = {
        "male": "Male",
        "female": "Female",
        "fb": "[Fullbody]",
        "vh": "[Viewhands]",
        "vl": "[Viewlegs]",
        "t6": "Black Ops 2",
        "iw6": "Ghosts",
        "s1": "Advanced Warfare",
        "t7": "Black Ops 3",
        "iw7": "Infinite Warfare",
        "h1": "ModernWarfareRemastered",
        "s2": "World War 2",
        "t8": "Black Ops 4",
        "iw8": "Modern Warfare 2019",
        "h2": "ModernWarfare2CR",
        "t9": "Cold War",
        "s4": "Vanguard",
        "iw9": "Modern Warfare 2"
    }

    for index in range( len( type ) ):
        for rig_type in rig_types:
            if type[index] == rig_type:
                type[index] = rig_types[rig_type]

    return " ".join( type )

def get_animations_dir():
    return cmds.internalVar( userScriptDir = True ) + "CoDCharacterTools/Animations/"

def get_targets_dir():
    return cmds.internalVar( userScriptDir = True ) + "CoDCharacterTools/Targets/"

def import_target_rig( file_name ):
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Create array for joints
    joints = []

    # Store current groups in outliner
    existing_groups = get_groups()

    # File path
    file_path = get_targets_dir() + file_name

    # Make sure the directory exists
    if not os.path.isdir( get_targets_dir() ):
        error( "Path: " + get_targets_dir() + "\n\nDoesn't exist." )
        return

    # Make sure the file exists
    if not os.path.isfile( file_path ):
        error( "File: " + file_path + "\n\nDoesn't exist." )
        return

    # Import the rig
    cmds.file( file_path, i = True )
    remove_namespaces()

    # Delete the empty group that was created for meshes
    if cmds.objExists( os.path.splitext( file_name )[0] ):
        cmds.delete( os.path.splitext( file_name )[0] )
        cmds.select( deselect = True )

    # Store joints attributes for the target rig
    for group in get_groups():
        if group not in existing_groups:
            for joint in cmds.listRelatives( group, allDescendents = True, fullPath = True ):
                joints.append( cmds.ls( joint, long = True )[0] )

    # Store joints with attributes
    joints_with_attributes = get_joints_with_attributes( joints )

    # Delete after storing joints with attributes
    for group in get_groups():
        if group not in existing_groups:
            if cmds.objExists( group ):
                cmds.delete( group )

    return joints_with_attributes

def is_in_a_skincluster( input ):
    # Checks if a joint or an array of joints is in a skincluster
    if isinstance( input, list ):
        for joint in input:
            for skinCluster in get_skinclusters():
                if joint in cmds.skinCluster( skinCluster, query = True, influence = True ):
                    return True
    else:
        for skinCluster in get_skinclusters():
            if input in cmds.skinCluster( skinCluster, query = True, influence = True ):
                return True

    return False

def is_joint_in_rig( joints_with_attributes, joint ):
    for joint_with_attributes in joints_with_attributes:
        if joint_with_attributes["name"] == joint:
            return True

    return False

def mirror_joint( joint_to_mirror ):
    # Make sure the joint exists
    if not cmds.objExists( joint_to_mirror ):
        error( joint_to_mirror + " doesn't exist." )
        return
    
    # Get mirrored joint rotations for the given joint
    joints_with_attributes = get_mirror_joint_attributes( joint_to_mirror )

    # Rotate them
    for joint_with_attributes in joints_with_attributes:
        if cmds.objExists( joint_with_attributes["name"] ):
            set_attribute( joint_with_attributes["name"], "rotateX", joint_with_attributes["rotateX"] )
            set_attribute( joint_with_attributes["name"], "rotateY", joint_with_attributes["rotateY"] )
            set_attribute( joint_with_attributes["name"], "rotateZ", joint_with_attributes["rotateZ"] )

def lock_all_weights( enable = True ):
    for joint in get_joints():
        set_attribute( joint, "lockInfluenceWeights", enable )

def rotate_models():
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    for joint_with_attributes in get_joints_with_attributes():
        for joint in get_joints():
            if joint_with_attributes["name"] == joint.split( "|" )[-1].split( ":" )[-1]:
                # Exclude tag_origin, we don't want to move it
                if "tag_origin" not in joint_with_attributes["name"]:
                    # If it's parent isn't a joint, we know it's a root joint. This is what we need to rotate & move
                    if not cmds.nodeType( cmds.listRelatives( joint, parent = True, path = True )[-1] ) == "joint":
                        cmds.select( joint )
                        cmds.rotate( joint_with_attributes["rotateXWorld"], joint_with_attributes["rotateYWorld"], joint_with_attributes["rotateZWorld"] )
                        cmds.move( joint_with_attributes["translateXWorld"], joint_with_attributes["translateYWorld"], joint_with_attributes["translateZWorld"] )
                        cmds.select( deselect = True )

def semodel_unique_names():
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    num = 0

    for mesh in get_meshes():
        num += 1

        cmds.rename( mesh, "SEModelMesh_" + str( num ) )

def set_cosmetic_parent( show_message = True ):
    if not cmds.objExists( "head" ):
        error( "\"head\" does not exist." )
        return
    
    if not cmds.objExists( "XModelExporterInfo.Cosmeticbone" ):
        CoDMayaTools.ShowWindow( "xmodel" )

    if cmds.getAttr( "XModelExporterInfo.Cosmeticbone", "head" ) != "head":
        cmds.setAttr( "XModelExporterInfo.Cosmeticbone", "head", type = "string" )

        if show_message:
            confirm_dialog( "\"head\" has now been set as the cosmetic parent." )
    else:
        error( "\"head\" is already the cosmetic parent." )

def set_skincluster_attributes():
    for skinCluster in get_skinclusters():
        set_attribute( skinCluster, "normalizeWeights", 1 )
        set_attribute( skinCluster, "weightDistribution", 0 )
        set_attribute( skinCluster, "maintainMaxInfluences", 1 )
        set_attribute( skinCluster, "maxInfluences", 15 )

def set_vertex_colors():
    for mesh in get_meshes():
        cmds.select( mesh )
        cmds.polyColorPerVertex( alpha = 1, rgb = ( 1, 1, 1 ), colorDisplayOption = True )
        cmds.select( deselect = True )

def set_zero_rotations( nodes ):
    if len( nodes ) < 1:
        error( "Nothing to rotate!" )
        return

    for node in nodes:
        set_attribute( node, "rotateX", 0 )
        set_attribute( node, "rotateY", 0 )
        set_attribute( node, "rotateZ", 0 )

def transfer_weight( source, target ):
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Make sure no animation is in the scene
    if len( cmds.ls( "*SENotes*" ) ) > 0:
        error( "You have an animation in the scene,\n\nReset scene first." )
        return

    if not cmds.objExists( source ):
        error( source + " doesn't exist!" )
        return
    
    if not cmds.objExists( target ):
        error( target + " doesn't exist!" )
        return

    # Set skincluster attributes
    set_skincluster_attributes()

    # Check we're in painting mode, if not switch to it.
    if cmds.currentCtx() != "artAttrSkinContext":
        mel.eval( "ArtPaintSkinWeightsTool" )

    # Transfer weight
    for mesh in get_meshes():
        influences = cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True )

        if source not in influences:
            continue

        # Add target to skincluster if it isn't already
        if target not in influences:
            # Lock all weights
            lock_all_weights( True )

            # Add target to skincluster
            cmds.skinCluster( get_skincluster_for_mesh( mesh ), edit = True, addInfluence = target )

            # Unlock all weights
            lock_all_weights( False )

        mel.eval( "changeSelectMode -object; select " + mesh )
        mel.eval( "artSkinSelectInfluence artAttrSkinPaintCtx " + source )
        mel.eval( "skinCluster -edit -selectInfluenceVerts " + source + " " + get_skincluster_for_mesh( mesh ) )
        mel.eval( "skinPercent -transformMoveWeights " + source + " -transformMoveWeights " + target + " " + get_skincluster_for_mesh( mesh ) )
        mel.eval( "skinCluster -e -ri " + source + " " + get_skincluster_for_mesh( mesh ) )

    # Set tool back to select
    cmds.setToolTo( "selectSuperContext" )
    enable_x_ray( False )
    cmds.select( deselect = True )

def rig_combiner( show_message = True ):
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No SEModels could be found!" )
        return

    # Remove existing namespaces first
    remove_namespaces()

    # Set skincluster attributes
    set_skincluster_attributes()

    # Store joints attributes
    joints_with_attributes = get_joints_with_attributes()

    # Give the semodels unique names so we don't clash
    semodel_unique_names()

    # Rotate models to correct positions
    rotate_models()

    # Copy & paste meshes, to make duplicates
    for group in get_groups():
        if "COMBINED" not in group and "Joints" not in group and "group" not in group:
            cmds.select( group )
            mel.eval( "CopySelected" )
            mel.eval( "PasteSelected copy" )
            cmds.select( deselect = True )

    # Create new rig
    create_new_rig( "COMBINED", joints_with_attributes )
    
    # Delete construction history for original meshes
    for group in get_groups():
        if "COMBINED" not in group and "Joints" not in group and "group" not in group:
            # Assume it's this group
            for node in cmds.listRelatives( group, allDescendents = True ):
                if node in get_meshes():
                    cmds.delete( node, constructionHistory = True )

    # Remove original joints
    for group in get_groups():
        if "Joints" in group:
            if "COMBINED" not in group and "group" not in group:
                cmds.delete( group )

    # Bind combined joints
    for mesh in get_meshes():
        cmds.select( deselect = True )

        if( "pasted__" in mesh ):
            for joint in cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True ):
                cmds.select( "COMBINED:" + joint.split( "pasted__" )[-1], add = True )
                cmds.select( mesh.split("pasted__")[-1], add = True )

            cmds.skinCluster( get_selection(), mesh.split("pasted__")[-1], toSelectedBones = True, maximumInfluences = 15, obeyMaxInfluences = True, dropoffRate = 5.0, removeUnusedInfluence = False, normalizeWeights = 1 )
        
        cmds.select( deselect = True )

    # Copy skinweights from old rigs to combined rig
    for mesh in get_meshes():
        if( "pasted__" in mesh ):
            cmds.copySkinWeights( sourceSkin = get_skincluster_for_mesh( mesh ), destinationSkin = get_skincluster_for_mesh( mesh.split( "pasted__" )[-1] ), noMirror = True, surfaceAssociation = "closestPoint", influenceAssociation = "oneToOne" )

    # Delete pasted groups
    for group in get_groups():
        if "group" in group:
            cmds.delete( group )

    # Remove namespaces
    remove_namespaces()

    # Delete unused nodes in hypershade
    mel.eval( "MLdeleteUnused" )

    # Set vertex colors
    #set_vertex_colors()

    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Done
    if show_message:
        print( "Combined SEModels." )
        confirm_dialog( "Combined SEModels." )

def rig_converter( target_rig, rig_name ):
    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No SEModels could be found!" )
        return

    # Set skincluster attributes
    set_skincluster_attributes()

    # Combine if the model is in parts and hasn't been combined
    if len( cmds.ls( "Joints*" ) ) > 1:
        rig_combiner( False )

    # Joints to rename
    rename_joints = {
        "j_wristfronttwist1_le": "j_wristtwist_le",
        "j_wristfronttwist1_ri": "j_wristtwist_ri",
        "j_metaindex_le_1": "j_indexbase_le",
        "j_metaindex_ri_1": "j_indexbase_ri",
        "j_metaring_le_1": "j_ringbase_le",
        "j_metaring_ri_1": "j_ringbase_ri",
        "j_metapinky_le_1": "j_pinkybase_le",
        "j_metapinky_ri_1": "j_pinkybase_ri"
    }

    # Rename joints
    for joint in rename_joints:
        if cmds.objExists( joint ):
            cmds.rename( joint, rename_joints[joint] )
            cmds.select( deselect = True )

    # Get rid of useless joints for viewhands
    if "Viewhands" in rig_name:
        if cmds.objExists( "j_clavicle_le" ) and cmds.objExists( "j_shoulder_le" ) and cmds.objExists( "j_clavicle_ri" ) and cmds.objExists( "j_shoulder_ri" ):
            # Take them out of groups
            cmds.select( deselect = True )
            cmds.parent( "j_shoulder_le", world = True )

            cmds.select( deselect = True )
            cmds.parent( "j_shoulder_ri", world = True )

            # Deleting like this using mel will transfer the weights, because sometimes we have weights on clavicle joints
            cmds.select( deselect = True )
            cmds.select( "j_clavicle_le" )
            mel.eval( "Delete" )

            cmds.select( deselect = True )
            cmds.select( "j_clavicle_ri" )
            mel.eval( "Delete" )

            # Get rid of everything else
            cmds.select( deselect = True )
            for group in get_groups():
                if "Joints" in group:
                    cmds.delete( group )

            # Create this again now and group because it's expected to be there
            cmds.select( deselect = True )
            cmds.select( "j_shoulder_le", add = True )
            cmds.select( "j_shoulder_ri", add = True )
            cmds.group( name = "Joints" )
            cmds.select( deselect = True )

    # Source rig
    source_rig = get_joints_with_attributes()

    # Move joints mode
    enable_move_joints( True )

    # Move all joints to world
    for joint in get_joints():
        cmds.parent( joint, world = True )
        cmds.select( deselect = True )

    # Create T7 joints which don't exist
    for joint_with_attributes in target_rig:
        if not cmds.objExists( joint_with_attributes["name"] ):
            # We don't need all of the T7 face joints
            if not joint_with_attributes["parent"] == "head":
                cmds.joint( name = joint_with_attributes["name"] )

        cmds.select( deselect = True )

    # Parent target joints
    for joint_with_attributes in target_rig:
        if cmds.objExists( joint_with_attributes["name"] ):
            if "Joints" not in joint_with_attributes["parent"]:
                cmds.parent( joint_with_attributes["name"], joint_with_attributes["parent"] )
                cmds.select( deselect = True )

    # Set translations, rotations for target joints
    for joint_with_attributes in target_rig:
        if cmds.objExists( joint_with_attributes["name"] ):
            set_attribute( joint_with_attributes["name"], "translateX", joint_with_attributes["translateX"] )
            set_attribute( joint_with_attributes["name"], "translateY", joint_with_attributes["translateY"] )
            set_attribute( joint_with_attributes["name"], "translateZ", joint_with_attributes["translateZ"] )
            set_attribute( joint_with_attributes["name"], "rotateX", joint_with_attributes["rotateX"] )
            set_attribute( joint_with_attributes["name"], "rotateY", joint_with_attributes["rotateY"] )
            set_attribute( joint_with_attributes["name"], "rotateZ", joint_with_attributes["rotateZ"] )
            set_attribute( joint_with_attributes["name"], "jointOrientX", joint_with_attributes["jointOrientX"] )
            set_attribute( joint_with_attributes["name"], "jointOrientY", joint_with_attributes["jointOrientY"] )
            set_attribute( joint_with_attributes["name"], "jointOrientZ", joint_with_attributes["jointOrientZ"] )

    # Parent source joints
    for joint_with_attributes in source_rig:
        for joint in get_joints():
            if joint_with_attributes["name"] == joint:
                if cmds.listRelatives( joint, parent = True ) == None:
                    if "Joints" not in joint_with_attributes["parent"]:
                        # For fullbody, the head joints need to be under "head" instead of "j_head"
                        if "Fullbody" in rig_name:
                            if joint_with_attributes["parent"] == "j_head":
                                joint_with_attributes["parent"] = "head"

                        # Parent them
                        if cmds.objExists( joint_with_attributes["parent"] ):
                            cmds.parent( joint_with_attributes["name"], joint_with_attributes["parent"] )
                            cmds.select( deselect = True )

    # Move eyes back to source positions
    for joint_with_attributes in source_rig:
        if "j_eyeball" in joint_with_attributes["name"]:
            if not cmds.listRelatives( joint_with_attributes["name"], parent = True ) == None:
                parent = cmds.listRelatives( joint_with_attributes["name"], parent = True )[0]

                cmds.parent( joint_with_attributes["name"], world = True )
                cmds.move( joint_with_attributes["translateXWorld"], joint_with_attributes["translateYWorld"], joint_with_attributes["translateZWorld"] )
                cmds.parent( joint_with_attributes["name"], parent )
                cmds.select( deselect = True )

    # Array for useless joints that we don't need to keep
    useless = []

    # Get rid of useless non-t7 joints with no weights
    for joint in get_joints():
        if cmds.listRelatives( joint, allDescendents = True ) == None:
            if not is_joint_in_rig( target_rig, joint ):
                if not is_in_a_skincluster( joint ):
                    if joint not in useless:
                        useless.append( joint )

    # Delete them
    if len( useless ) > 0:
        for joint in useless:
            if cmds.objExists( joint ):
                cmds.delete( joint )

    # Move joints mode
    enable_move_joints( False )

    # Zero all rotations
    set_zero_rotations( get_joints() )

    # Put them back in group
    if "Viewhands" in rig_name:
        set_attribute( "tag_view", "translateX", 0 )
        set_attribute( "tag_view", "translateY", 0 )
        set_attribute( "tag_view", "translateZ", 0 )

        set_attribute( "tag_ads", "translateX", 0 )
        set_attribute( "tag_ads", "translateY", 0 )
        set_attribute( "tag_ads", "translateZ", 0 )

        set_attribute( "tag_torso", "translateX", 0 )
        set_attribute( "tag_torso", "translateY", 0 )
        set_attribute( "tag_torso", "translateZ", 0 )

        set_attribute( "j_shoulder_le", "translateX", -2.652 )
        set_attribute( "j_shoulder_le", "translateY", 20.266 )
        set_attribute( "j_shoulder_le", "translateZ", -10.853 )

        set_attribute( "j_shoulder_ri", "translateX", -2.652 )
        set_attribute( "j_shoulder_ri", "translateY", -20.266 )
        set_attribute( "j_shoulder_ri", "translateZ", -10.853 )

        set_attribute( "tag_weapon_left", "translateX", 35.329 )
        set_attribute( "tag_weapon_left", "translateY", 45.914 )
        set_attribute( "tag_weapon_left", "translateZ", -44.023 )
        set_attribute( "tag_weapon_left", "jointOrientX", 41.248 )
        set_attribute( "tag_weapon_left", "jointOrientY", 23.941 )
        set_attribute( "tag_weapon_left", "jointOrientZ", 20.443 )

        set_attribute( "tag_weapon_right", "translateX", 35.240 )
        set_attribute( "tag_weapon_right", "translateY", -45.670 )
        set_attribute( "tag_weapon_right", "translateZ", -44.124 )
        set_attribute( "tag_weapon_right", "jointOrientX", -41.887 )
        set_attribute( "tag_weapon_right", "jointOrientY", 24.888 )
        set_attribute( "tag_weapon_right", "jointOrientZ", -21.812 )

        cmds.parent( "tag_view", "Joints" )
    elif "Fullbody" in rig_name:
        cmds.parent( "tag_origin", "Joints" )
        set_cosmetic_parent( False )

    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Joints we're going to delete, need to be handled differently because these have weights
    joints_to_delete = []

    # Add joints that we need to get rid of that are still in a skincluster to array
    if cmds.objExists( "j_wrist_le" ) and cmds.objExists( "j_wrist_ri" ):
        for joint in get_joints():
            if cmds.objExists( joint ):
                if not is_joint_in_rig( target_rig, joint ):
                    if joint not in joints_to_delete:
                        # For viewhands, get rid of everything that isn't a t7 joint
                        if "Viewhands" in rig_name:
                            joints_to_delete.append( joint )
                        # For fullbody get rid of anything under wrist, as some tags are used on the body for accessories and if we transfer those weights it might offset them
                        elif "Fullbody" in rig_name:
                            if joint in cmds.listRelatives( "j_wrist_le", allDescendents = True ) or joint in cmds.listRelatives( "j_wrist_ri", allDescendents = True ):
                                joints_to_delete.append( joint )

    # Delete them
    if len( joints_to_delete ) > 0:
        # Keep doing this until none of them are influences
        while is_in_a_skincluster( joints_to_delete ):
            for joint_to_delete in joints_to_delete:
                if cmds.objExists( joint_to_delete ):
                    if cmds.listRelatives( joint_to_delete, allDescendents = True ) == None:
                        parent = cmds.listRelatives( joint_to_delete, parent = True )[0]

                        if "j_wrist_" in parent:
                            # Lock all weights
                            lock_all_weights( True )

                            set_attribute( joint_to_delete, "lockInfluenceWeights", 0 )
                            set_attribute( parent, "lockInfluenceWeights", 0 )

                        cmds.select( joint_to_delete )
                        mel.eval( "Delete" )
                        cmds.select( deselect = True )

                        if "j_wrist_" in parent:
                            # Unlock all weights
                            lock_all_weights( False )

    # Deselect anything that's already selected
    cmds.select( deselect = True )

    # Delete leftovers
    for joint_to_delete in joints_to_delete:
        if cmds.objExists( joint_to_delete ):
            cmds.delete( joint_to_delete )

    # Done
    print( "Converted." )
    confirm_dialog( "Converted." )

def add_wristtwist_influences():
    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No SEModels could be found!" )
        return
    
    # Make sure no animation is in the scene
    if len( cmds.ls( "*SENotes*" ) ) > 0:
        error( "You have an animation in the scene,\n\nReset scene first." )
        return

    suffixes = ["le", "ri"]

    # Make sure wristtwists exist
    for suffix in suffixes:
        for index in range( 1, 7 ):
            if not cmds.objExists( "j_wristtwist" + str( index ) + "_" + suffix ):
                error( "Can't find wristtwists\n\nDid you forget to convert first?\n\nOperation cancelled..." )
                return

            # Make sure they're not already attached
            if is_in_a_skincluster( "j_wristtwist" + str( index ) + "_" + suffix ):
                error( "The wristtwists are already attached to a skincluster!\n\nOperation cancelled..." )
                return

    # Set skincluster attributes
    set_skincluster_attributes()

    # Lock weights for joints that we don't want to be affected by these new influences
    for joint in get_joints():
        if "shoulder" not in joint:
            if "elbow" not in joint:
                if "wristtwist" not in joint:
                    if "wrist" not in joint:
                        set_attribute( joint, "lockInfluenceWeights", 1 )

    # Add influences for the wristtwists
    for suffix in suffixes:
        for mesh in get_meshes():
            for index in range( 1, 7 ):
                # Make sure skincluster is suitable for this operation
                influences = cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True )

                if ( "j_wristtwist_" + suffix ) in influences:
                    # Don't add the influence if there's fingers in this skincluster
                    if ( "j_thumb_" + suffix + "_3" ) in influences or ( "j_index_" + suffix + "_3" ) in influences or ( "j_mid_" + suffix + "_3" ) in influences or ( "j_ring_" + suffix + "_3" ) in influences or ( "j_pinky_" + suffix + "_3" ) in influences:
                        continue

                    cmds.skinCluster( get_skincluster_for_mesh( mesh ), edit = True, addInfluence = "j_wristtwist" + str( index ) + "_" + suffix, weightDistribution = 1, smoothWeights = 0.5, smoothWeightsMaxIterations = 2 )

    # Unlock all weights
    for joint in get_joints():
        set_attribute( joint, "lockInfluenceWeights", 0 )

    # Done
    confirm_dialog( "Added influences" )

    cmds.select( deselect = True )

def edit_wristtwist_influences():
    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No SEModels could be found!" )
        return
    
    # Make sure no animation is in the scene
    if len( cmds.ls( "*SENotes*" ) ) > 0:
        error( "You have an animation in the scene,\n\nReset scene first." )
        return

    # Get user input
    operation = cmds.promptDialog( title = "Select operation", message = "Do you want to scale or smooth the weights?\n\nEnter the paint value (Default is 1.0)\n\nMake sure you test with animations to see if it looks good", button = ["Scale", "Smooth", "Cancel"], cancelButton = "Cancel" )
    value = cmds.promptDialog( query = True, text = True )

    # Cancel
    if operation == "Cancel":
        return

    # Make sure it's a number
    if not value.isnumeric():
        error( "Invalid input!\n\nPlease enter a number\n\nOperation cancelled..." )
        return

    # Make sure wristtwists exist
    for index in range( 1, 7 ):
        if not cmds.objExists( "j_wristtwist" + str( index ) + "_le" ) or not cmds.objExists( "j_wristtwist" + str( index ) + "_ri" ):
            error( "Can't find wristtwists\n\nDid you forget to convert first?\n\nOperation cancelled..." )
            return

        # Make sure they're attached
        if not is_in_a_skincluster( "j_wristtwist" + str( index ) + "_le" ) or not is_in_a_skincluster( "j_wristtwist" + str( index ) + "_ri" ):
            error( "The wristtwists are not attached to a skincluster...\n\nYou need to add them as influences first!\n\nOperation cancelled..." )
            return

    # Set skincluster attributes
    set_skincluster_attributes()

    # Check we're in painting mode, if not switch to it.
    if cmds.currentCtx() != "artAttrSkinContext":
        mel.eval( "ArtPaintSkinWeightsTool" )

    # Gets current weight painting settings
    current_operation = cmds.artAttrSkinPaintCtx( cmds.currentCtx(), query = 1, selectedattroper = True )
    current_value = cmds.artAttrSkinPaintCtx( cmds.currentCtx(), query = 1, value = True )

    # Edit weights
    cmds.artAttrSkinPaintCtx( cmds.currentCtx(), edit = 1, selectedattroper = operation.lower(), value = float( value ), maxvalue = float( value ) )

    # Perform operation
    for mesh in get_meshes():
        influences = cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True )

        if "j_index_le_3" in influences or "j_index_ri_3" in influences:
            continue

        for joint in influences:
            if "j_wristtwist" in joint:
                mel.eval( "changeSelectMode -object; select " + mesh )
                mel.eval( "artSkinSelectInfluence artAttrSkinPaintCtx " + joint )
                cmds.artAttrSkinPaintCtx( cmds.currentCtx(), edit = 1, clear = 1 )

        for joint in influences:
            if "j_shoulder" in joint:
                mel.eval( "changeSelectMode -object; select " + mesh )
                mel.eval( "artSkinSelectInfluence artAttrSkinPaintCtx " + joint )
                cmds.artAttrSkinPaintCtx( cmds.currentCtx(), edit = 1, clear = 1 )

    # Sets weight painting settings back to what they were
    cmds.artAttrSkinPaintCtx( cmds.currentCtx(), e = 1, selectedattroper = current_operation )
    cmds.artAttrSkinPaintCtx( cmds.currentCtx(), e = 1, value = current_value )

    # Set tool back to select
    cmds.setToolTo( "selectSuperContext" )
    enable_x_ray( False )
    cmds.select( deselect = True )

    # Cleanup
    if operation == "Smooth":
        for mesh in get_meshes():
            mel.eval( "select " + mesh )

            def merge_verts():
                # Mesh cleanup
                mel.eval( 'polyCleanupArgList 4 { "0","1","1","0","0","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };' )

                # Delete all non-deformer history
                mel.eval( "BakeAllNonDefHistory" )

                # Merge vertices
                mel.eval( 'polyMergeVertex  -d 0.01 -am 1 -ch 1 ' + mesh )

            # Don't ask, this never works on the first try (Probably a Maya 2018 bug)
            for index in range( 1, 5 ):
                merge_verts()
                cmds.select( deselect = True )

    confirm_dialog( "Operation completed" )

def menu_mirror_rotations():
    joint_to_mirror = prompt_dialog( "Mirror rotations", "Which joint do you want to mirror rotations from?\n\nThis is useful when making a conversion rig as you will only need to rotate one side\n\nAfter that, you can mirror those rotations to the opposite side\n\nThe rotations for every joint under it will also be mirrored" )

    if not joint_to_mirror == None:
        if not cmds.objExists( joint_to_mirror ):
            error( "That joint doesn't exist!" )
            return

        if not cmds.nodeType( joint_to_mirror ) == "joint":
            error( "That is not a valid joint!" )
            return

        mirror_joint( joint_to_mirror )

def menu_new_target_rig( name ):
    cmds.menuItem( label = get_rig_name( name ), command = lambda x: rig_converter( import_target_rig( name ), get_rig_name( name ) ) )

def menu_new_test_animation( name ):
    cmds.menuItem( label = name, command = lambda x: SEToolsPlugin.__load_seanim__( get_animations_dir() + name ) )

def menu_transfer_weight():    
    weights = prompt_dialog( "Transfer weight", "Input your source joint, followed by your target joint\n\nSeparated by a hyphen (-)\n\nExample below:\n\nj_midbase_le-j_wrist_le" )

    if not weights == None:
        if "-" in weights:
            source = weights.split( "-" )[0]
            target = weights.split( "-" )[1]

            transfer_weight( source, target )
        else:
            error( "Invalid input!" )
            return

def menu_zero_rotations():
    result = cmds.confirmDialog( title = "Zero rotations", message = "Do you want to zero the rotations of all nodes or only the selected nodes?", button = ["All", "Selected", "Cancel"], defaultButton = "All", cancelButton = "Cancel" )

    if result == "All":
        set_zero_rotations( get_joints() )
    elif result == "Selected":
        set_zero_rotations( get_selection() )

def menu_items():
    cmds.setParent( mel.eval( "$temp1=$gMainWindow" ) )

    # Get rid of it, if it already exists
    if cmds.control( "CoDCharacterTools", exists = True ):
        cmds.deleteUI( "CoDCharacterTools", menu = True )

    # Create the menu
    main_menu = cmds.menu( "CoDCharacterTools", label = "CoDCharacterTools", tearOff = True )

    # Misc
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Miscellaneous" )
    cmds.menuItem( parent = main_menu, label = "Reload plugin", command = "reload(CoDCharacterTools)" )
    cmds.menuItem( parent = main_menu, label = "Remove all namespaces", command = lambda x: remove_namespaces() )

    # Utilities
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Utilities" )
    cmds.menuItem( parent = main_menu, label = "Transfer weight", command = lambda x: menu_transfer_weight() )
    cmds.menuItem( parent = main_menu, label = "Add wristtwists influences", command = lambda x: add_wristtwist_influences() )
    cmds.menuItem( parent = main_menu, label = "Edit all wristtwists weights", command = lambda x: edit_wristtwist_influences() )
    cmds.menuItem( parent = main_menu, label = "Mirror rotations", command = lambda x: menu_mirror_rotations() )
    cmds.menuItem( parent = main_menu, label = "Zero rotations", command = lambda x: menu_zero_rotations() )

    # CoDMayaTools
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "CoDMayaTools" )
    cmds.menuItem( parent = main_menu, label = "Set \"head\" as the cosmetic parent", command = lambda x: set_cosmetic_parent() )

    # SEToolsPlugin
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "SEToolsPlugin" )
    cmds.menuItem( parent = main_menu, label = "Reset scene", command = lambda x: SEToolsPlugin.__scene_resetanim__() )

    # Rig combiner
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Rig combiner" )
    cmds.menuItem( parent = main_menu, label = "Rig combiner", command = lambda x: rig_combiner() )

    # Rig converter
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Rig converter" )
    cmds.menuItem( parent = main_menu, label = "Convert from:", subMenu = True )

    # Create new target rig entry
    if os.path.isdir( get_targets_dir() ):
        for target_rig in os.listdir( get_targets_dir() ):
            if not os.path.isdir( target_rig ):
                if target_rig.endswith( ( ".ma", ".mb", ".semodel" ) ):
                    menu_new_target_rig( target_rig )

    # Test animations
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Test animations" )
    cmds.menuItem( parent = main_menu, label = "Import animation:", subMenu = True )

    # Create test animation entry
    if os.path.isdir( get_animations_dir() ):
        for seanim in os.listdir( get_animations_dir() ):
            if not os.path.isdir( seanim ):
                if seanim.endswith( ".seanim" ):
                    menu_new_test_animation( seanim )

    # Donate
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Say thanks" )
    cmds.menuItem( parent = main_menu, label = "Donate", command = lambda x: webbrowser.open( "https://paypal.me/kingslayerkyle" ) )

menu_items()
