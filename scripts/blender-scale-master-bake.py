import bpy
import json
import os
import sys

FACE_TO_MESH = {
    "seat": "ASSENTO",
    "backrest-front": "ENCOSTO_FRONTAL",
    "backrest-side": "ENCOSTO_LATERAL",
    "backrest-rear": "ENCOSTO_TRASEIRO",
    "side-outer": "LATERAL_EXTERNA",
    "side-inner": "LATERAL_INTERNA",
    "side-rear": "LATERAL_REAR",
    "side-top": "LATERAL_TOP",
}

def argv_after_double_dash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def parse_args():
    args = argv_after_double_dash()
    values = {}
    i = 0
    while i < len(args):
        key = args[i]
        if not key.startswith("--") or i + 1 >= len(args):
            raise RuntimeError(f"Argumento inválido: {key}")
        values[key[2:]] = args[i + 1]
        i += 2
    required = ["canonical-glb", "reference-glb", "audit-json", "output-dir"]
    for key in required:
        if key not in values:
            raise RuntimeError(f"Argumento obrigatório ausente: --{key}")
    return values

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.name != "Render Result":
            bpy.data.images.remove(block)

def import_glb(filepath, prefix):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    imported = [obj for obj in bpy.data.objects if obj not in before]
    result = {}
    for obj in imported:
        if obj.type != "MESH":
            continue
        original = obj.name
        obj.name = f"{prefix}::{original}"
        result[original] = obj
    return result

def find_base_color_image(material):
    if not material or not material.use_nodes:
        return None
    principled = None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            principled = node
            break
    if not principled:
        return None
    socket = principled.inputs.get("Base Color")
    if not socket or not socket.is_linked:
        return None
    pending = [link.from_node for link in socket.links]
    visited = set()
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        if node.type == "TEX_IMAGE" and node.image:
            return node.image
        for inp in node.inputs:
            if inp.is_linked:
                pending.extend(link.from_node for link in inp.links)
    return None

def build_target_material(obj, image):
    material = bpy.data.materials.new(name=f"BAKE::{obj.name}")
    material.use_nodes = True
    tree = material.node_tree
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.select = True
    tree.nodes.active = tex
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)
    return material

def bake_face(face_key, source, target, source_uv_set, output_dir):
    if source_uv_set >= len(source.data.uv_layers):
        raise RuntimeError(
            f"{face_key}: reference.glb não possui UV layer {source_uv_set}"
        )
    if len(target.data.uv_layers) < 1:
        raise RuntimeError(f"{face_key}: base.glb não possui UV0")

    source.data.uv_layers.active_index = source_uv_set
    source.data.uv_layers[source_uv_set].active_render = True
    target.data.uv_layers.active_index = 0
    target.data.uv_layers[0].active_render = True

    source_material = source.data.materials[0] if source.data.materials else None
    source_image = find_base_color_image(source_material)
    if not source_image:
        raise RuntimeError(f"{face_key}: imagem Base Color não encontrada no Scale Master")

    width, height = int(source_image.size[0]), int(source_image.size[1])
    if width < 1 or height < 1:
        raise RuntimeError(f"{face_key}: dimensões inválidas da imagem fonte")

    target_image = bpy.data.images.new(
        name=f"SCALE_MASTER::{face_key}",
        width=width,
        height=height,
        alpha=True,
        float_buffer=False,
    )
    target_image.generated_color = (0.0, 0.0, 0.0, 0.0)
    build_target_material(target, target_image)

    bpy.ops.object.select_all(action="DESELECT")
    source.hide_render = False
    target.hide_render = False
    source.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.margin = 16
    scene.render.bake.use_clear = True
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True

    # O bake de DIFFUSE/COLOR transfere a leitura visual do material do Scale Master
    # para o UV0 do GLB canônico. A geometria final não é exportada nem alterada.
    bpy.ops.object.bake(type="DIFFUSE")

    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, f"{face_key}.png")
    target_image.filepath_raw = output
    target_image.file_format = "PNG"
    target_image.save()
    return {
        "face": face_key,
        "source_uv_set": source_uv_set,
        "target_uv_set": 0,
        "width_px": width,
        "height_px": height,
        "intermediate": os.path.basename(output),
    }

def main():
    args = parse_args()
    clear_scene()

    canonical = import_glb(args["canonical-glb"], "CANONICAL")
    reference = import_glb(args["reference-glb"], "REFERENCE")

    with open(args["audit-json"], "r", encoding="utf-8") as handle:
        audit = json.load(handle)

    outputs = []
    for face_key, mesh_name in FACE_TO_MESH.items():
        if mesh_name not in canonical:
            raise RuntimeError(f"{face_key}: mesh canônica ausente: {mesh_name}")
        if mesh_name not in reference:
            raise RuntimeError(f"{face_key}: mesh de referência ausente: {mesh_name}")
        face_audit = audit["faces"][face_key]
        outputs.append(
            bake_face(
                face_key,
                reference[mesh_name],
                canonical[mesh_name],
                int(face_audit["source_uv_set"]),
                args["output-dir"],
            )
        )

    manifest = {
        "schema": "karv.scale-master-bake/1",
        "reference_glb_sha256": audit["reference_glb"]["sha256"],
        "target_geometry": "karv-chair@2",
        "target_uv_set": 0,
        "runtime_geometry_unchanged": True,
        "runtime_uv_unchanged": True,
        "faces": outputs,
    }
    with open(
        os.path.join(args["output-dir"], "scale-master-bake.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

if __name__ == "__main__":
    main()
