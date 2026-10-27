import argparse, hashlib, io, json, math, shutil, struct
from pathlib import Path

import numpy as np
from PIL import Image

EXPECTED_REFERENCE_SHA256 = "be51f1f363aa7d230d74b55230be0fdc40d6398953eab28f00a3bc5caa700353"
MESH_NAME = "LATERAL_INTERNA"
FACE_KEY = "side-inner"
CROP = (220, 30, 1120, 320)
NORMAL_STRENGTH = 2.25
AO_STRENGTH = 0.65
WEBP_QUALITY = 90


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


def embedded_side_inner(gltf, bin_blob):
    mesh = next((m for m in gltf.get("meshes", []) if m.get("name") == MESH_NAME), None)
    if not mesh or len(mesh.get("primitives", [])) != 1:
        raise RuntimeError("LATERAL_INTERNA ausente ou ambígua no Scale Master")
    primitive = mesh["primitives"][0]
    material = gltf["materials"][primitive["material"]]
    base = material["pbrMetallicRoughness"]["baseColorTexture"]
    texture = gltf["textures"][base["index"]]
    source = texture.get("extensions", {}).get("EXT_texture_webp", {}).get("source", texture.get("source"))
    image = gltf["images"][source]
    if image.get("mimeType") != "image/webp" or image.get("uri"):
        raise RuntimeError("LATERAL_INTERNA deve ser WebP embutida")
    view = gltf["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    payload = bin_blob[start:start + view["byteLength"]]
    return Image.open(io.BytesIO(payload)).convert("RGBA"), image.get("name"), int(base.get("texCoord", 0))


def mirror_texture(source, size):
    clean = source.crop(CROP).convert("RGB")
    flip_x = clean.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    flip_y = clean.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    flip_xy = flip_x.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    cw, ch = clean.size

    tiles = [
        [clean, flip_x, clean, flip_x],
        [flip_y, flip_xy, flip_y, flip_xy],
        [clean, flip_x, clean, flip_x],
        [flip_y, flip_xy, flip_y, flip_xy],
    ]
    canvas = Image.new("RGB", (cw * 4, ch * 4))
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            canvas.paste(tile, (x * cw, y * ch))

    width, height = size
    left = (canvas.width - width) // 2
    top = (canvas.height - height) // 2
    return canvas.crop((left, top, left + width, top + height)).convert("RGBA")


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


def info(path, media_type, uri):
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
    args = parser.parse_args()

    raw, gltf, bin_blob = parse_glb(args.reference_glb)
    if sha256_bytes(raw) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("reference.glb não corresponde ao Málaga 03 aprovado")

    source, image_name, source_uv = embedded_side_inner(gltf, bin_blob)
    if source_uv != 2:
        raise RuntimeError(f"LATERAL_INTERNA esperada em UV2, recebeu UV{source_uv}")

    repo = Path(__file__).resolve().parents[1]
    face_root = repo / "public" / "v1" / "assets" / "fabric-kv-009" / "face-set"
    dest = face_root / FACE_KEY
    dest.mkdir(parents=True, exist_ok=True)

    # Preserva a dimensão publicada atual para não alterar o contrato dimensional da face.
    old = Image.open(dest / "base-color.webp")
    target_size = old.size

    corrected = mirror_texture(source, target_size)
    base_path = dest / "base-color.webp"
    normal_path = dest / "normal.png"
    ao_path = dest / "ao.webp"
    corrected.save(base_path, "WEBP", quality=WEBP_QUALITY, method=6)

    normal, ao = generate_maps(corrected)
    Image.fromarray(normal).save(normal_path, "PNG", compress_level=9)
    Image.fromarray(ao).save(ao_path, "WEBP", quality=WEBP_QUALITY, method=6)

    metadata_path = face_root / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    face = metadata["faces"][FACE_KEY]
    face["source_filename"] = "LATERAL_INTERNA.webp"
    face["base_color"] = info(base_path, "image/webp", "./side-inner/base-color.webp")
    face["normal"] = info(normal_path, "image/png", "./side-inner/normal.png")
    face["ambient_occlusion"] = info(ao_path, "image/webp", "./side-inner/ao.webp")

    generation = metadata.setdefault("generation", {})
    generation["side_inner_correction"] = {
        "reference_glb_sha256": EXPECTED_REFERENCE_SHA256,
        "source_image": image_name,
        "source_uv_set": source_uv,
        "method": "clean-weave-mirror-fill",
        "crop_px": list(CROP),
        "scope": FACE_KEY,
    }

    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("fabric-kv-009/side-inner: corrigido sem alterar as demais faces")


if __name__ == "__main__":
    main()
