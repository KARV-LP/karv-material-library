import argparse, hashlib, io, json, math, os, shutil, struct
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OFFICIAL = {
    "seat": ("ASSENTO", "Assento.webp"),
    "backrest-front": ("ENCOSTO_FRONTAL", "ENCOSTO_FRONTAL.webp"),
    "backrest-side": ("ENCOSTO_LATERAL", "ENCOSTO_LATERAL.webp"),
    "backrest-rear": ("ENCOSTO_TRASEIRO", "ENCOSTO_TRASEIRO.webp"),
    "side-outer": ("LATERAL_EXTERNA", "LATERAL_EXTERNA.webp"),
    "side-inner": ("LATERAL_INTERNA", "LATERAL_INTERNA.webp"),
    "side-rear": ("LATERAL_REAR", "LATERAL_REAR.webp"),
    "side-top": ("LATERAL_TOP", "LATERAL_TOP.webp"),
}
MAX_EDGE = 2048
WEBP_QUALITY = 90
NORMAL_STRENGTH = 2.25
AO_STRENGTH = 0.65
EXPECTED_REFERENCE_SHA256 = "be51f1f363aa7d230d74b55230be0fdc40d6398953eab28f00a3bc5caa700353"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def parse_glb(path):
    data = Path(path).read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError("reference.glb inválido")
    json_len = struct.unpack_from("<I", data, 12)[0]
    if data[16:20] != b"JSON":
        raise RuntimeError("chunk JSON ausente")
    gltf = json.loads(data[20:20 + json_len].decode("utf-8"))
    bin_header = 20 + json_len
    if data[bin_header + 4:bin_header + 8] != b"BIN\0":
        raise RuntimeError("chunk BIN ausente")
    bin_len = struct.unpack_from("<I", data, bin_header)[0]
    bin_blob = data[bin_header + 8:bin_header + 8 + bin_len]
    return data, gltf, bin_blob


def accessor_array(gltf, bin_blob, index):
    acc = gltf["accessors"][index]
    view = gltf["bufferViews"][acc["bufferView"]]
    dtype = {
        5121: np.uint8,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }[acc["componentType"]]
    comps = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"]
    stride = view.get("byteStride")
    if stride is None:
        return np.frombuffer(bin_blob, dtype=dtype, count=count * comps, offset=offset).reshape(count, comps)
    result = np.empty((count, comps), dtype=dtype)
    for i in range(count):
        result[i] = np.frombuffer(bin_blob, dtype=dtype, count=comps, offset=offset + i * stride)
    return result


def embedded_texture(gltf, bin_blob, texture_index):
    texture = gltf["textures"][texture_index]
    source = texture.get("extensions", {}).get("EXT_texture_webp", {}).get("source", texture.get("source"))
    image = gltf["images"][source]
    if image.get("uri"):
        raise RuntimeError("Scale Master exige Base Color embutida")
    if image.get("mimeType") != "image/webp":
        raise RuntimeError("Scale Master exige Base Color WebP")
    view = gltf["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    payload = bin_blob[start:start + view["byteLength"]]
    return np.array(Image.open(io.BytesIO(payload)).convert("RGBA")), image, payload


def raster_bake(source, indices, target_uv, source_uv):
    height, width = source.shape[:2]
    output = np.zeros((height, width, 4), dtype=np.uint8)
    hit = np.zeros((height, width), dtype=np.uint8)
    source_px = np.column_stack([
        source_uv[:, 0] * width,
        (1.0 - source_uv[:, 1]) * height,
    ]).astype(np.float32)

    for tri in indices.reshape(-1, 3):
        target = target_uv[tri]
        sample = source_px[tri]
        umin, vmin = target.min(axis=0)
        umax, vmax = target.max(axis=0)

        for du in range(math.floor(-umax), math.ceil(1 - umin) + 1):
            for dv in range(math.floor(-vmax), math.ceil(1 - vmin) + 1):
                shifted = target + np.array([du, dv], dtype=np.float32)
                if shifted[:, 0].max() < 0 or shifted[:, 0].min() > 1:
                    continue
                if shifted[:, 1].max() < 0 or shifted[:, 1].min() > 1:
                    continue

                dst = np.column_stack([
                    shifted[:, 0] * width,
                    (1.0 - shifted[:, 1]) * height,
                ]).astype(np.float32)

                x0 = max(0, int(np.floor(dst[:, 0].min())))
                x1 = min(width - 1, int(np.ceil(dst[:, 0].max())))
                y0 = max(0, int(np.floor(dst[:, 1].min())))
                y1 = min(height - 1, int(np.ceil(dst[:, 1].max())))
                if x1 < x0 or y1 < y0:
                    continue

                matrix = np.column_stack([dst, np.ones(3, dtype=np.float32)])
                try:
                    cx = np.linalg.solve(matrix, sample[:, 0])
                    cy = np.linalg.solve(matrix, sample[:, 1])
                except np.linalg.LinAlgError:
                    continue

                xs = np.arange(x0, x1 + 1, dtype=np.float32)
                ys = np.arange(y0, y1 + 1, dtype=np.float32)
                xx, yy = np.meshgrid(xs, ys)
                map_x = cx[0] * xx + cx[1] * yy + cx[2]
                map_y = cy[0] * xx + cy[1] * yy + cy[2]
                sampled = cv2.remap(source, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

                mask = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=np.uint8)
                polygon = np.round(dst - np.array([x0, y0], dtype=np.float32)).astype(np.int32)
                cv2.fillConvexPoly(mask, polygon, 255, lineType=cv2.LINE_8)

                selected = mask > 0
                output[y0:y1 + 1, x0:x1 + 1][selected] = sampled[selected]
                hit[y0:y1 + 1, x0:x1 + 1][selected] = 255

    dilation = cv2.dilate(hit, np.ones((33, 33), dtype=np.uint8))
    fill = (dilation > 0) & (hit == 0)
    if fill.any():
        rgb = cv2.inpaint(output[:, :, :3], fill.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
        output[fill, :3] = rgb[fill]
        output[fill, 3] = 255
    return output


def optimize(image):
    image = Image.fromarray(image)
    width, height = image.size
    scale = min(1.0, MAX_EDGE / max(width, height))
    if scale < 1.0:
        image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    return image


def generate_maps(image):
    arr = np.array(image.convert("RGBA"))
    rgb = arr[:, :, :3].astype(np.float32)
    lum = (rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722) / 255.0
    hpad = np.pad(lum, ((0, 0), (1, 1)), mode="edge")
    vpad = np.pad(lum, ((1, 1), (0, 0)), mode="edge")
    left, right = hpad[:, :-2], hpad[:, 2:]
    top, bottom = vpad[:-2, :], vpad[2:, :]
    dx = (right - left) * NORMAL_STRENGTH
    dy = (bottom - top) * NORMAL_STRENGTH
    inv = 1 / np.sqrt(dx * dx + dy * dy + 1)

    normal = np.empty_like(arr)
    normal[:, :, 0] = np.clip(np.rint((-dx * inv * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    normal[:, :, 1] = np.clip(np.rint((-dy * inv * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    normal[:, :, 2] = np.clip(np.rint((inv * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    normal[:, :, 3] = arr[:, :, 3]

    neighbors = (left + right + top + bottom) / 4
    ao_value = np.clip(
        np.rint((1 - np.maximum(0, neighbors - lum) * AO_STRENGTH) * 255),
        0,
        255,
    ).astype(np.uint8)
    ao = np.stack([ao_value, ao_value, ao_value, arr[:, :, 3]], axis=2)
    return normal, ao


def file_info(path, media_type, uri):
    payload = Path(path).read_bytes()
    image = Image.open(path)
    return {
        "uri": uri,
        "media_type": media_type,
        "sha256": sha256_bytes(payload),
        "width_px": image.width,
        "height_px": image.height,
        "bytes": len(payload),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-glb", required=True)
    parser.add_argument("--material-id", default="fabric-kv-009")
    args = parser.parse_args()

    raw, gltf, bin_blob = parse_glb(args.reference_glb)
    if sha256_bytes(raw) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("reference.glb não corresponde ao Scale Master aprovado do Málaga 03")

    repo = Path(__file__).resolve().parents[1]
    root = repo / "public" / "v1" / "assets" / args.material_id
    face_root = root / "face-set"
    meshes = {mesh["name"]: mesh for mesh in gltf.get("meshes", [])}

    faces = {}
    for face_key, (mesh_name, source_filename) in OFFICIAL.items():
        mesh = meshes.get(mesh_name)
        if not mesh or len(mesh.get("primitives", [])) != 1:
            raise RuntimeError(f"{face_key}: mesh/primitive inválida")
        primitive = mesh["primitives"][0]
        material = gltf["materials"][primitive["material"]]
        base = material["pbrMetallicRoughness"]["baseColorTexture"]
        if base.get("extensions", {}).get("KHR_texture_transform"):
            raise RuntimeError(f"{face_key}: KHR_texture_transform não suportado")
        source_uv_set = int(base.get("texCoord", 0))
        if source_uv_set == 0:
            raise RuntimeError(f"{face_key}: Scale Master esperado em UV1/UV2, recebeu UV0")

        indices = accessor_array(gltf, bin_blob, primitive["indices"]).reshape(-1).astype(np.int64)
        target_uv = accessor_array(gltf, bin_blob, primitive["attributes"]["TEXCOORD_0"]).astype(np.float32)
        source_attr = f"TEXCOORD_{source_uv_set}"
        if source_attr not in primitive["attributes"]:
            raise RuntimeError(f"{face_key}: {source_attr} ausente")
        source_uv = accessor_array(gltf, bin_blob, primitive["attributes"][source_attr]).astype(np.float32)
        source, image_meta, _ = embedded_texture(gltf, bin_blob, base["index"])

        baked = raster_bake(source, indices, target_uv, source_uv)
        image = optimize(baked)
        dest = face_root / face_key
        dest.mkdir(parents=True, exist_ok=True)
        base_path = dest / "base-color.webp"
        normal_path = dest / "normal.png"
        ao_path = dest / "ao.webp"
        image.save(base_path, "WEBP", quality=WEBP_QUALITY, method=4)
        normal, ao = generate_maps(image)
        Image.fromarray(normal).save(normal_path, "PNG", compress_level=9)
        Image.fromarray(ao).save(ao_path, "WEBP", quality=WEBP_QUALITY, method=4)

        faces[face_key] = {
            "source_filename": source_filename,
            "surface_ids": [face_key],
            "base_color": file_info(base_path, "image/webp", f"./{face_key}/base-color.webp"),
            "normal": file_info(normal_path, "image/png", f"./{face_key}/normal.png"),
            "ambient_occlusion": file_info(ao_path, "image/webp", f"./{face_key}/ao.webp"),
        }

    piping = face_root / "piping"
    piping.mkdir(parents=True, exist_ok=True)
    for filename in ["base-color.webp", "normal.png", "ao.webp"]:
        shutil.copyfile(face_root / "side-top" / filename, piping / filename)
    faces["piping"] = {
        "source_filename": "LATERAL_TOP.webp",
        "derivation": "byte-copy-from-side-top",
        "surface_ids": ["piping-seat", "piping-backrest"],
        "base_color": {**faces["side-top"]["base_color"], "uri": "./piping/base-color.webp"},
        "normal": {**faces["side-top"]["normal"], "uri": "./piping/normal.png"},
        "ambient_occlusion": {**faces["side-top"]["ambient_occlusion"], "uri": "./piping/ao.webp"},
    }

    seat = Image.open(face_root / "seat" / "base-color.webp").convert("RGBA")
    seat.thumbnail((512, 512), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.alpha_composite(seat, ((512 - seat.width) // 2, (512 - seat.height) // 2))
    thumbnail_path = face_root / "thumbnail.webp"
    canvas.save(thumbnail_path, "WEBP", quality=88, method=4)
    thumbnail = file_info(thumbnail_path, "image/webp", "./thumbnail.webp")

    shutil.copyfile(thumbnail_path, root / "preview.webp")
    shutil.copyfile(face_root / "seat" / "base-color.webp", root / "base-color.webp")
    shutil.copyfile(face_root / "seat" / "normal.png", root / "normal.png")
    shutil.copyfile(face_root / "seat" / "ao.webp", root / "ao.webp")

    metadata = {
        "schema": "karv.fabric-face-set/1",
        "fabric_id": args.material_id,
        "face_count": 9,
        "map_count": 27,
        "thumbnail": {"source_face": "seat", **thumbnail},
        "generation": {
            "source_optimization": {"max_edge_px": MAX_EDGE, "format": "webp", "quality": WEBP_QUALITY},
            "normal_convention": "opengl",
            "normal_strength": NORMAL_STRENGTH,
            "ao_strength": AO_STRENGTH,
            "scale_master": {
                "reference_glb_sha256": EXPECTED_REFERENCE_SHA256,
                "target_uv_set": 0,
                "method": "uv-remap-bake",
            },
        },
        "faces": faces,
    }
    (face_root / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    catalog_path = repo / "public" / "v1" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    material = next((item for item in catalog["materials"] if item["id"] == args.material_id), None)
    if not material:
        raise RuntimeError(f"{args.material_id}: entrada ausente no catálogo")
    material["asset_integrity"] = {
        "base_color": {k: v for k, v in file_info(root / "base-color.webp", "image/webp", "") .items() if k in {"sha256", "width_px", "height_px", "bytes"}},
        "normal": {k: v for k, v in file_info(root / "normal.png", "image/png", "") .items() if k in {"sha256", "width_px", "height_px", "bytes"}},
        "ao": {k: v for k, v in file_info(root / "ao.webp", "image/webp", "") .items() if k in {"sha256", "width_px", "height_px", "bytes"}},
    }
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{args.material_id}: Scale Master bake concluído para 8 faces")


if __name__ == "__main__":
    main()
