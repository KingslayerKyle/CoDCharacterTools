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
import castplugin

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
    if value == None:
        return

    if cmds.objExists( node ):
        if attribute == "castRestPosition":
            if not cmds.objExists( node + "." + "castRestPosition" ):
                cmds.addAttr( node, longName = attribute, dataType = "matrix" )
                
            cmds.setAttr( node + "." + attribute, value, type = "matrix" )
        else:
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
    return cmds.ls( "*CastMesh*" )

def get_skinclusters():
    return cmds.ls( type = "skinCluster" )

def get_skincluster_for_mesh( mesh ):
    return mel.eval( "findRelatedSkinCluster " + mesh )

def get_blendshapes_for_mesh( mesh ):
    blendshapes = []

    for blendshape in cmds.ls( type = "blendShape" ):
        blendshapes.append( blendshape )

    for blendshape_target in cmds.listRelatives( mesh, allDescendents = True, fullPath = True ):
        if "CastShape" not in blendshape_target:
            blendshapes.append( blendshape_target )

    return blendshapes

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

def reset_bind_pose():
    # Get all skinclusters in the scene
    skinclusters = cmds.ls( type = "skinCluster" )

    # Make sure they exist
    if not skinclusters:
        error( "No skinclusters found in the scene." )
        return

    # Get all joints influencing this skincluster
    for skin in skinclusters:
        joints = cmds.skinCluster( skin, query = True, influence = True )

        if not joints:
            continue

        # Delete existing bind poses connected to this skincluster
        bindposes = cmds.listConnections( skin + ".bindPose", type = "dagPose" ) or []

        for bindpose in bindposes:
            cmds.delete( bindpose )

        # Create a new dagPose node from current pose
        dag_pose_name = cmds.dagPose( joints, name = skin + "_currentBindPose", save = True, bindPose = True )[0]

def create_joint_attributes( joint, is_target ):
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
        "rotateZWorld": cmds.xform( joint, query = True, worldSpace = True, rotation = True )[2],
        "castRestPosition": None
    }

    if is_target:
        # Don't add eyeballs from target rigs
        if "j_eyeball_" in joint_attributes["name"]:
            return None

        # Set cast rest position for target rig
        if cmds.objExists( joint + ".castRestPosition" ):
            joint_attributes["castRestPosition"] = cmds.getAttr( joint + ".castRestPosition" )

    return joint_attributes

def create_new_rig( namespace, joints_with_attributes ):
    # Deselect anything that's already selected
    cmds.select( clear = True )

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
        cmds.select( clear = True )
        cmds.joint( name = namespace + ":" + joint_with_attributes["name"] )
        cmds.select( clear = True )

    # Parent them
    for joint_with_attributes in joints_with_attributes:
        if "Joints" not in joint_with_attributes["parent"]:
            cmds.parent( namespace + ":" + joint_with_attributes["name"], namespace + ":" + joint_with_attributes["parent"] )
            cmds.select( clear = True )

    # Group them
    for joint_with_attributes in joints_with_attributes:
        if "Joints" in joint_with_attributes["parent"]:
            cmds.group( namespace + ":" + joint_with_attributes["name"], name = namespace + ":Joints" )
    
    # Deselect after grouping
    cmds.select( clear = True )

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

def get_joints_with_attributes( input = [], is_target = False ):
    joints_with_attributes = []
    joints = []

    if len( input ) > 0:
        joints = input
    else:
        joints = get_joints()

    # Add the ones that have tag_origin first, because those are correct rotations
    for joint in joints:
        joint_path = cmds.ls( joint, long = True )[0]

        if cmds.nodeType( joint_path ) == "joint":
            if "tag_origin" in cmds.listRelatives( joint_path, parent = True, fullPath = True )[0]:
                joint_attributes = create_joint_attributes( joint_path, is_target )

                # Make sure it didn't return None
                if joint_attributes == None:
                    continue

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
            joint_attributes = create_joint_attributes( joint_path, is_target )

            # Make sure it didn't return None
            if joint_attributes == None:
                continue

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
    cmds.select( clear = True )

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
    cmds.select( clear = True )

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

def get_rig_name( cast_model ):
    cast_model_name = os.path.splitext( cast_model )[0]
    type = cast_model_name.split( "_" )

    rig_types = {
        "male": "Male",
        "female": "Female",
        "fb": "[Fullbody]",
        "vh": "[Viewhands]",
        "vl": "[Viewlegs]",
        "t5": "Black Ops 1",
        "iw5": "Modern Warfare 3",
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
    cmds.select( clear = True )

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
        cmds.select( clear = True )

    # Store joints attributes for the target rig
    for group in get_groups():
        if group not in existing_groups:
            for joint in cmds.listRelatives( group, allDescendents = True, fullPath = True ):
                joints.append( cmds.ls( joint, long = True )[0] )

    # Store joints with attributes
    joints_with_attributes = get_joints_with_attributes( joints, True )

    # Delete after storing joints with attributes
    for group in get_groups():
        if group not in existing_groups:
            if cmds.objExists( group ):
                cmds.delete( group )

    return joints_with_attributes

def any_node_exists( nodes ):
    for node in nodes:
        if cmds.objExists( node ):
            return True

    return False

def is_in_a_skincluster( input ):
    # Checks if a joint or any joint in an array of joints is in a skincluster
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
    cmds.select( clear = True )

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
                        cmds.select( clear = True )

def cast_model_unique_names():
    # Deselect anything that's already selected
    cmds.select( clear = True )

    num = 0

    for mesh in get_meshes():
        num += 1

        cmds.rename( mesh, "CastMesh_" + str( num ) )

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
        cmds.select( clear = True )

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
    cmds.select( clear = True )

    # Make sure no animation is in the scene
    if len( cmds.ls( "*CastNotetracks*" ) ) > 0:
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

    # Remove unused influences
    for mesh in get_meshes():
        # Remove unused influences
        cmds.skinCluster( get_skincluster_for_mesh( mesh ), edit = True, removeUnusedInfluence = True )

    # Transfer weight
    for mesh in get_meshes():
        # Query influences
        influences = cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True )

        # Skip if source isn't in this skincluster
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

        # Deselect anything that's already selected
        cmds.select( clear = True )

        # Move the weights
        mel.eval( "changeSelectMode -object; select " + mesh )
        mel.eval( "artSkinSelectInfluence artAttrSkinPaintCtx " + source )
        mel.eval( "skinCluster -edit -selectInfluenceVerts " + source + " " + get_skincluster_for_mesh( mesh ) )
        mel.eval( "skinPercent -transformMoveWeights " + source + " -transformMoveWeights " + target + " " + get_skincluster_for_mesh( mesh ) )
        mel.eval( "skinCluster -e -ri " + source + " " + get_skincluster_for_mesh( mesh ) )

    # Set tool back to select
    cmds.setToolTo( "selectSuperContext" )
    enable_x_ray( False )
    cmds.select( clear = True )

def merge_verts( mesh ):
    if mesh not in get_meshes():
        error( "This is not a valid mesh!" )
        return

    # Don't ask, this never works on the first try (Probably a Maya 2018 bug)
    for index in range( 1, 5 ):
        cmds.select( clear = True )

        mel.eval( "select " + mesh )

        # Mesh cleanup
        mel.eval( 'polyCleanupArgList 4 { "0","1","1","0","0","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","-1","0","0" };' )

        # Delete all non-deformer history
        mel.eval( "BakeAllNonDefHistory" )

        # Merge vertices
        mel.eval( 'polyMergeVertex  -d 0.01 -am 1 -ch 1 ' + mesh )

        cmds.select( clear = True )

def delete_non_target_joints_preserve_all_weights( rig_name ):
    # Deletes any joint not in the target rig and transfers the weights to the closest parent
    target_rig = None

    # Set target rig type
    if "Viewhands" in rig_name:
        target_rig = import_target_rig( "vh_t8.mb" )
    elif "Fullbody" in rig_name:
        target_rig = import_target_rig( "fb_t8_male_and_female.mb" )

    # Rig not recognised
    if target_rig == None:
        error( "Rig not recognised" )
        return
    
    # Joints to delete
    joints_to_delete = []
    
    # Add the joints we want to delete to the array (non-t7-joints)
    for joint in get_joints():
        if not is_joint_in_rig( target_rig, joint ):
            if joint not in joints_to_delete:
                joints_to_delete.append( joint )

    # Loop them until they're done
    while any_node_exists( joints_to_delete ):
        for joint_to_delete in joints_to_delete:
            if cmds.objExists( joint_to_delete ):
                if cmds.listRelatives( joint_to_delete, allDescendents = True ) == None:
                    parent = cmds.listRelatives( joint_to_delete, parent = True )[0]

                    # Lock all weights
                    lock_all_weights( True )

                    # Make sure parent is also in the skincluster, if not then add it
                    for mesh in get_meshes():
                        influences = cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True )

                        for joint in influences:
                            if joint == joint_to_delete:
                                if parent not in influences:
                                    cmds.skinCluster( get_skincluster_for_mesh( mesh ), edit = True, addInfluence = parent, weightDistribution = 1, smoothWeights = 0.5, smoothWeightsMaxIterations = 2 )

                    # Unlock weights for joint and it's parent
                    set_attribute( parent, "lockInfluenceWeights", False )
                    set_attribute( joint_to_delete, "lockInfluenceWeights", False )

                    # Delete the joint
                    mel.eval( "select " + joint_to_delete )
                    mel.eval( "Delete" )
                    cmds.select( clear = True )

                    # Unlock all weights
                    lock_all_weights( False )

def delete_non_target_joints_preserve_hand_weights( rig_name ):
    # Deletes any joint not in the target rig and transfers the weights to the closest parent
    target_rig = None

    # Set target rig type
    if "Viewhands" in rig_name:
        target_rig = import_target_rig( "vh_t8.mb" )
    elif "Fullbody" in rig_name:
        target_rig = import_target_rig( "fb_t8_male_and_female.mb" )

    # Rig not recognised
    if target_rig == None:
        error( "Rig not recognised" )
        return

    # Joints to delete
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
                        cmds.select( clear = True )

                        if "j_wrist_" in parent:
                            # Unlock all weights
                            lock_all_weights( False )

    # Delete leftovers
    for joint_to_delete in joints_to_delete:
        if cmds.objExists( joint_to_delete ):
            cmds.delete( joint_to_delete )

    # Deselect anything that's already selected
    cmds.select( clear = True )

def rig_combiner( show_message = True ):
    # Deselect anything that's already selected
    cmds.select( clear = True )

    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No Cast models could be found!" )
        return

    # If there's any blendshapes, delete them
    for mesh in get_meshes():
        blendshapes = get_blendshapes_for_mesh( mesh )

        if len( blendshapes ) > 0:
            for blendshape in blendshapes:
                cmds.delete( blendshape )

    # Remove existing namespaces first
    remove_namespaces()

    # Set skincluster attributes
    set_skincluster_attributes()

    # Store joints attributes
    joints_with_attributes = get_joints_with_attributes()

    # Give the cast models unique names so we don't clash
    cast_model_unique_names()

    # Rotate models to correct positions
    rotate_models()

    # Copy & paste meshes, to make duplicates
    for group in get_groups():
        if "COMBINED" not in group and "Joints" not in group and "group" not in group:
            cmds.select( group )
            mel.eval( "CopySelected" )
            mel.eval( "PasteSelected copy" )
            cmds.select( clear = True )

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
        cmds.select( clear = True )

        if( "pasted__" in mesh ):
            for joint in cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True ):
                cmds.select( "COMBINED:" + joint.split( "pasted__" )[-1], add = True )
                cmds.select( mesh.split("pasted__")[-1], add = True )

            cmds.skinCluster( get_selection(), mesh.split("pasted__")[-1], toSelectedBones = True, maximumInfluences = 15, obeyMaxInfluences = True, dropoffRate = 5.0, removeUnusedInfluence = False, normalizeWeights = 1 )
        
        cmds.select( clear = True )

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
    cmds.select( clear = True )

    # Done
    if show_message:
        print( "Combined Cast models." )
        confirm_dialog( "Combined Cast models." )

def rig_converter( target_rig, rig_name ):
    # Deselect anything that's already selected
    cmds.select( clear = True )

    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No Cast models could be found!" )
        return

    # If there's any blendshapes, delete them
    for mesh in get_meshes():
        blendshapes = get_blendshapes_for_mesh( mesh )

        if len( blendshapes ) > 0:
            for blendshape in blendshapes:
                cmds.delete( blendshape )

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
        "j_metapinky_ri_1": "j_pinkybase_ri",
        "jnt_eyeball_l": "j_eyeball_le",
        "jnt_eyeball_r": "j_eyeball_ri"
    }

    # Rename joints
    for joint in rename_joints:
        if cmds.objExists( joint ):
            cmds.rename( joint, rename_joints[joint] )
            cmds.select( clear = True )

    # Get rid of useless joints for viewhands
    if "Viewhands" in rig_name:
        if cmds.objExists( "j_clavicle_le" ) and cmds.objExists( "j_shoulder_le" ) and cmds.objExists( "j_clavicle_ri" ) and cmds.objExists( "j_shoulder_ri" ):
            # Take them out of groups
            cmds.select( clear = True )
            cmds.parent( "j_shoulder_le", world = True )

            cmds.select( clear = True )
            cmds.parent( "j_shoulder_ri", world = True )

            # Deleting like this using mel will transfer the weights, because sometimes we have weights on clavicle joints
            cmds.select( clear = True )
            cmds.select( "j_clavicle_le" )
            mel.eval( "Delete" )

            cmds.select( clear = True )
            cmds.select( "j_clavicle_ri" )
            mel.eval( "Delete" )

            # Get rid of everything else
            cmds.select( clear = True )
            for group in get_groups():
                if "Joints" in group:
                    cmds.delete( group )

            # Create this again now and group because it's expected to be there
            cmds.select( clear = True )
            cmds.select( "j_shoulder_le", add = True )
            cmds.select( "j_shoulder_ri", add = True )
            cmds.group( name = "Joints" )
            cmds.select( clear = True )

    # Source rig
    source_rig = get_joints_with_attributes()

    # Move joints mode
    enable_move_joints( True )

    # Move all joints to world
    for joint in get_joints():
        cmds.parent( joint, world = True )
        cmds.select( clear = True )

    # Create T7 joints which don't exist
    for joint_with_attributes in target_rig:
        if not cmds.objExists( joint_with_attributes["name"] ):
            # We don't need all of the T7 face joints
            if not joint_with_attributes["parent"] == "head":
                cmds.joint( name = joint_with_attributes["name"] )

        cmds.select( clear = True )

    # Parent target joints
    for joint_with_attributes in target_rig:
        if cmds.objExists( joint_with_attributes["name"] ):
            if "Joints" not in joint_with_attributes["parent"]:
                cmds.parent( joint_with_attributes["name"], joint_with_attributes["parent"] )
                cmds.select( clear = True )

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
            set_attribute( joint_with_attributes["name"], "castRestPosition", joint_with_attributes["castRestPosition"] )

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
                            cmds.select( clear = True )

    # Fix leftover weights on viewhands
    if "Viewhands" in rig_name:
        question = (
            "Please choose how to handle leftover joint weights:\n\n"
            "Preserve Hand Weights: Removes non-target joints while preserving hand and wrist weighting.\n\n"
            "Preserve All Weights: Removes non-target joints and redistributes all remaining weights to parent joints.\n\n"
            "Notes:\n\n"
            "The target rig is the BO3 rig.\n\n"
            "You may experiment with either method to determine which produces the best results for your model.\n\n"
            "After converting the model, use the Import Animation menu to verify its behavior with animations.\n\n"
            "Important: BO3, BO4, and BOCW rigs use linear skinning for viewmodel arms and already include the necessary twist joints.\n\n"
            "Older COD games also use linear skinning but do not include twist joints, relying on simpler animations and careful weight painting to avoid deformation.\n\n"
            "Newer COD games use dual quaternion skinning, which does not require twist joints because the skinning method preserves volume and prevents twisting artifacts automatically.\n\n"
            "When re-targeting models from games that lack twist joints to the BO3 rig, twist joints must be manually added and weight-painted, as they are not included by default.\n\n"
            "Failure to do so may result in deformations-such as extremely thin arms-during animation playback (e.g., reloads).\n\n"
            "While helper functions like \"Add wrist twist influences\" and \"Edit wrist twist influences\" are provided in the menu, perfect results cannot be guaranteed due to variations between individual models."
        )

        result = cmds.confirmDialog( title = "Delete Non-Target Joints", message = question, button = ["Preserve Hand Weights", "Preserve All Weights"], defaultButton = "Preserve Hand Weights" )

        if result == "Preserve Hand Weights":
            delete_non_target_joints_preserve_hand_weights( rig_name )
        elif result == "Preserve All Weights":
            delete_non_target_joints_preserve_all_weights( rig_name )
        else:
            error( "Something went wrong with converting viewhands." )
            return

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

    # Reset scene
    castplugin.utilityClearAnimation()

    # Put them back in group
    if "Viewhands" in rig_name:
        set_attribute( "tag_view", "translateX", 0.0 )
        set_attribute( "tag_view", "translateY", 0.0 )
        set_attribute( "tag_view", "translateZ", 0.0 )

        set_attribute( "tag_ads", "translateX", 0.0 )
        set_attribute( "tag_ads", "translateY", 0.0 )
        set_attribute( "tag_ads", "translateZ", 0.0 )

        set_attribute( "tag_torso", "translateX", 0.0 )
        set_attribute( "tag_torso", "translateY", 0.0 )
        set_attribute( "tag_torso", "translateZ", 0.0 )

        set_attribute( "j_shoulder_le", "translateX", -2.65154147148 )
        set_attribute( "j_shoulder_le", "translateY", 20.2655353546 )
        set_attribute( "j_shoulder_le", "translateZ", -10.8532037735 )

        set_attribute( "j_shoulder_ri", "translateX", -2.65154147148 )
        set_attribute( "j_shoulder_ri", "translateY", -20.2655353546 )
        set_attribute( "j_shoulder_ri", "translateZ", -10.8532037735 )

        set_attribute( "tag_weapon_left", "translateX", 35.3286743164 )
        set_attribute( "tag_weapon_left", "translateY", 45.913860321 )
        set_attribute( "tag_weapon_left", "translateZ", -44.0232429504 )
        set_attribute( "tag_weapon_left", "rotateX", 41.2484810387 )
        set_attribute( "tag_weapon_left", "rotateY", 23.9407359736 )
        set_attribute( "tag_weapon_left", "rotateZ", 20.4425301212 )

        set_attribute( "tag_weapon_right", "translateX", 35.239654541 )
        set_attribute( "tag_weapon_right", "translateY", -45.6697502136 )
        set_attribute( "tag_weapon_right", "translateZ", -44.1238937378 )
        set_attribute( "tag_weapon_right", "rotateX", -41.8867336396 )
        set_attribute( "tag_weapon_right", "rotateY", 24.887949571 )
        set_attribute( "tag_weapon_right", "rotateZ", -21.8123152033 )

        # Reset bind pose
        reset_bind_pose()

        # Group joints
        cmds.parent( "tag_view", "Joints" )
    elif "Fullbody" in rig_name:
        # Move j_mainroot back
        set_attribute( "j_mainroot", "translateX", -3.18260717392 )
        set_attribute( "j_mainroot", "translateY", 0.000215000065509 )
        set_attribute( "j_mainroot", "translateZ", 94.5591583252 )

        # Set correct eyeball rotations for BO1/AW
        if ("Black Ops 1" in rig_name) or ("Advanced Warfare" in rig_name):
            enable_move_joints( True )
            set_attribute( "j_eyeball_le", "rotateX", 172.427775929 )
            set_attribute( "j_eyeball_le", "rotateY", -90.0 )
            set_attribute( "j_eyeball_le", "rotateZ", 0.0 )
            set_attribute( "j_eyeball_ri", "rotateX", 172.427775929 )
            set_attribute( "j_eyeball_ri", "rotateY", -90.0 )
            set_attribute( "j_eyeball_ri", "rotateZ", 0.0 )
            enable_move_joints( False )

        # Remove joints inside head for BO1
        if "Black Ops 1" in rig_name:
            # Lock all weights
            lock_all_weights( True )

            # Add head influence to meshes that don't have it, that do have "j_jaw" or "j_tongue"
            for mesh in get_meshes():
                # Get influences
                influences = cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True )

                # Remove tag_origin from influences if it's in there, so it doesn't interfere
                if "tag_origin" in influences:
                    cmds.skinCluster( get_skincluster_for_mesh( mesh ), edit = True, removeInfluence = "tag_origin" )

                # Skip if it's already in there
                if "head" in influences:
                    continue

                # Add head influence
                if ("j_jaw" not in influences) or ("j_tongue" not in influences):
                    cmds.skinCluster( get_skincluster_for_mesh( mesh ), edit = True, addInfluence = "head", weightDistribution = 1, smoothWeights = 0.5, smoothWeightsMaxIterations = 2 )

            # Unlock head joint
            set_attribute( "head", "lockInfluenceWeights", False )

            # Loop joints inside head and delete them
            for joint in cmds.listRelatives( "head", allDescendents = True ):
                # Skip these ones
                if "j_helmet" in joint or "tag_eye" in joint or "j_eyeball_le" in joint or "j_eyeball_ri" in joint:
                    continue

                # Unlock joint
                set_attribute( joint, "lockInfluenceWeights", False )

                # Delete the joint
                mel.eval( "select " + joint )
                mel.eval( "Delete" )
                cmds.select( clear = True )

            # Unlock all weights
            lock_all_weights( False )

        # Set cosmetic parent
        set_cosmetic_parent( False )

        # Fix leftover weights
        delete_non_target_joints_preserve_hand_weights( rig_name )

        # Group joints
        cmds.parent( "tag_origin", "Joints" )

    # Set vertex colors
    #set_vertex_colors()

    # Deselect anything that's already selected
    cmds.select( clear = True )

    # Done
    print( "Converted." )
    confirm_dialog( "Converted." )

def add_wristtwist_influences( suffix ):
    # Make sure something is selected
    if len( get_selection() ) < 1:
        error( "Nothing selected!" )
        return

    # Make sure the selection is a valid mesh
    for selection in get_selection():
        if selection not in get_meshes():
            error( "This is not a valid mesh!" )
            return
    
    # Make sure no animation is in the scene
    if len( cmds.ls( "*CastNotetracks*" ) ) > 0:
        error( "You have an animation in the scene,\n\nReset scene first." )
        return

    # Make sure wristtwists exist
    for index in range( 1, 7 ):
        if not cmds.objExists( "j_wristtwist" + str( index ) + "_" + suffix ):
            error( "Can't find wristtwists\n\nDid you forget to convert first?\n\nOperation cancelled..." )
            return

    # Set skincluster attributes
    set_skincluster_attributes()

    # Add influences for the wristtwists
    for selection in get_selection():
        if selection in get_meshes():
            for index in range( 1, 7 ):
                cmds.skinCluster( get_skincluster_for_mesh( selection ), edit = True, addInfluence = "j_wristtwist" + str( index ) + "_" + suffix, weightDistribution = 1, smoothWeights = 0.5, smoothWeightsMaxIterations = 2 )

    # Reset bind pose
    reset_bind_pose()

    # Done
    confirm_dialog( "Added influences" )

    cmds.select( clear = True )

def edit_wristtwist_influences():
    # Make sure the scene isn't empty
    if len( get_joints() + get_meshes() ) < 1:
        error( "No Cast models could be found!" )
        return
    
    # Make sure no animation is in the scene
    if len( cmds.ls( "*CastNotetracks*" ) ) > 0:
        error( "You have an animation in the scene,\n\nReset scene first." )
        return

    # Get user input
    operation = cmds.promptDialog( title = "Select operation", message = "Do you want to scale or smooth the weights?\n\nEnter the paint value (Default is 1.0)\n\nMake sure you test with animations to see if it looks good\n\nNote: Only selected meshes will be processed.", button = ["Scale", "Smooth", "Cancel"], cancelButton = "Cancel" )
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
    for selection in get_selection():
        if selection not in get_meshes():
            continue

        influences = cmds.skinCluster( get_skincluster_for_mesh( selection ), query = True, influence = True )

        for joint in influences:
            if "j_wristtwist" in joint:
                mel.eval( "changeSelectMode -object; select " + selection )
                mel.eval( "artSkinSelectInfluence artAttrSkinPaintCtx " + joint )
                cmds.artAttrSkinPaintCtx( cmds.currentCtx(), edit = 1, clear = 1 )

        for joint in influences:
            if "j_shoulder" in joint:
                mel.eval( "changeSelectMode -object; select " + selection )
                mel.eval( "artSkinSelectInfluence artAttrSkinPaintCtx " + joint )
                cmds.artAttrSkinPaintCtx( cmds.currentCtx(), edit = 1, clear = 1 )

    # Sets weight painting settings back to what they were
    cmds.artAttrSkinPaintCtx( cmds.currentCtx(), e = 1, selectedattroper = current_operation )
    cmds.artAttrSkinPaintCtx( cmds.currentCtx(), e = 1, value = current_value )

    # Set tool back to select
    cmds.setToolTo( "selectSuperContext" )
    enable_x_ray( False )
    cmds.select( clear = True )

    # Cleanup
    if operation == "Smooth":
        for selection in get_selection():
            if selection not in get_meshes():
                continue

            # Smoothing can tear the mesh, so let's merge the vertices
            merge_verts( selection )

    confirm_dialog( "Operation completed" )

def set_non_target_joints_as_cosmetics():
    # Marks any joints that aren't in the target rig as cosmetics
    target_rig = import_target_rig( "fb_t8_male_and_female.mb" )

    cmds.namespace( add = "cosmetic_bone" )

    for joint in get_joints():
        if not is_joint_in_rig( target_rig, joint ):
            if cmds.listRelatives( joint, allDescendents = True ) == None:
                cmds.rename( joint, "cosmetic_bone:" + joint )

def remove_cosmetics_from_mesh( mesh ):
    if not cmds.objExists( mesh ):
        error( mesh + " doesn't exist" )
        return
    
    for joint in cmds.skinCluster( get_skincluster_for_mesh( mesh ), query = True, influence = True ):
        if "cosmetic_bone" in joint:
            cmds.rename( joint, joint.split( ":" )[-1] )

def pin_ik_handle():
    selection = get_selection()

    if selection:
        ik = selection[0]
        loc = cmds.spaceLocator( name = "wrist_pin_loc" )[0]
        cmds.delete( cmds.parentConstraint( ik, loc ) )
        cmds.pointConstraint( loc, ik, mo = False )
        error( "Wrist pinned successfully." )
    else:
        error( "Select the IK handle first." )

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
    cmds.menuItem( label = os.path.splitext( name )[0], command = lambda x: menu_import_test_animation( name ) )

def menu_import_test_animation( name ):
    # Import, reset scene and import again
    # Due to an issue in the cast plugin
    cmds.file( str( get_animations_dir() + name ), i = True, itr = "override" )
    castplugin.utilityClearAnimation()
    cmds.file( str( get_animations_dir() + name ), i = True, itr = "override" )

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

def menu_transfer_weight_prompt( source, target ):
    transfer_weight( source, target )
    confirm_dialog( "Transferred: " + source + " > " + target + "\n\nDone." )

def menu_merge_verts_all():
    if len( get_meshes() ) < 1:
        error( "No Cast models could be found!" )
        return

    for mesh in get_meshes():
        merge_verts( mesh )

    confirm_dialog( "Operation completed" )

def menu_merge_verts_selected():
    if len( get_meshes() ) < 1:
        error( "No Cast models could be found!" )
        return
    
    if len( get_selection() ) > 1:
        error( "Select one mesh!" )
        return
    
    mesh = get_selection()[0]

    if mesh not in get_meshes():
        error( "This is not a valid mesh!" )
        return
    
    merge_verts( mesh )

    confirm_dialog( "Operation completed" )

def menu_zero_rotations():
    result = cmds.confirmDialog( title = "Zero rotations", message = "Do you want to zero the rotations of all joints or only the selected ones?", button = ["All", "Selected", "Cancel"], defaultButton = "All", cancelButton = "Cancel" )

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

    # General
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "General" )
    cmds.menuItem( parent = main_menu, label = "Reload plugin", command = "reload(CoDCharacterTools)" )
    cmds.menuItem( parent = main_menu, label = "Remove all namespaces", command = lambda x: remove_namespaces() )
    cmds.menuItem( parent = main_menu, label = "Weld detached vertices (All meshes)", command = lambda x: menu_merge_verts_all() )
    cmds.menuItem( parent = main_menu, label = "Weld detached vertices (Selected mesh)", command = lambda x: menu_merge_verts_selected() )
    cmds.menuItem( parent = main_menu, label = "Mirror joint rotations", command = lambda x: menu_mirror_rotations() )
    cmds.menuItem( parent = main_menu, label = "Zero joint rotations", command = lambda x: menu_zero_rotations() )

    # Rigging
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Rigging" )
    cmds.menuItem( parent = main_menu, label = "Transfer weight (user input)", command = lambda x: menu_transfer_weight() )
    cmds.menuItem( parent = main_menu, label = "Transfer weight (presets)", subMenu = True )
    cmds.menuItem( divider = True, dividerLabel = "Fullbody" )
    cmds.menuItem( label = "j_shouldertwist_le>j_shoulder_le", command = lambda x: menu_transfer_weight_prompt( "j_shouldertwist_le", "j_shoulder_le" ) )
    cmds.menuItem( label = "j_shouldertwist_ri>j_shoulder_ri", command = lambda x: menu_transfer_weight_prompt( "j_shouldertwist_ri", "j_shoulder_ri" ) )
    cmds.menuItem( divider = True, dividerLabel = "Viewlegs" )
    cmds.menuItem( label = "j_spine4>j_mainroot", command = lambda x: menu_transfer_weight_prompt( "j_spine4", "j_mainroot" ) )
    cmds.menuItem( label = "j_spineupper>j_mainroot", command = lambda x: menu_transfer_weight_prompt( "j_spineupper", "j_mainroot" ) )
    cmds.menuItem( label = "j_spinelower>j_mainroot", command = lambda x: menu_transfer_weight_prompt( "j_spinelower", "j_mainroot" ) )
    cmds.menuItem( parent = main_menu, label = "Add left wrist twist influences to selected mesh", command = lambda x: add_wristtwist_influences( "le" ) )
    cmds.menuItem( parent = main_menu, label = "Add right wrist twist influences to selected mesh", command = lambda x: add_wristtwist_influences( "ri" ) )
    cmds.menuItem( parent = main_menu, label = "Edit wrist twist influences", command = lambda x: edit_wristtwist_influences() )
    cmds.menuItem( parent = main_menu, label = "Pin IK handle", command = lambda x: pin_ik_handle() )

    # CoDMayaTools
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "CoDMayaTools" )
    cmds.menuItem( parent = main_menu, label = "Set \"head\" as the cosmetic parent", command = lambda x: set_cosmetic_parent() )

    # Cast
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Cast" )
    cmds.menuItem( parent = main_menu, label = "Reset scene", command = lambda x: castplugin.utilityClearAnimation() )

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
                if target_rig.endswith( ( ".ma", ".mb", ".cast" ) ):
                    menu_new_target_rig( target_rig )

    # Test animations
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Test animations" )
    cmds.menuItem( parent = main_menu, label = "Import animation:", subMenu = True )

    # Create test animation entry
    if os.path.isdir( get_animations_dir() ):
        for cast_anim in os.listdir( get_animations_dir() ):
            if not os.path.isdir( cast_anim ):
                if cast_anim.endswith( ".cast" ):
                    menu_new_test_animation( cast_anim )

    # Donate
    cmds.menuItem( parent = main_menu, divider = True, dividerLabel = "Say thanks" )
    cmds.menuItem( parent = main_menu, label = "Donate", command = lambda x: webbrowser.open( "https://paypal.me/kingslayerkyle" ) )

menu_items()
