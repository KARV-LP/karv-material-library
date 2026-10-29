# Maia 10 — Vinho: fontes técnicas

Os oito WebPs são cópias lossless dos PNGs originais, também organizadas em `fabrics/VELUDO/MAIA/maia-10-vinho/`. Ainda não são Base Colors bakeadas para UV0.

O GLB técnico está em três partes binárias. Para recompô-lo e verificar SHA-256:

```sh
python scale-masters/fabric-kv-010/assemble-reference.py
node scripts/scale-master-audit.mjs scale-masters/fabric-kv-010/reference.glb
```

`transport.json` registra os hashes das partes e do arquivo completo.

A diferença de quantidade de triângulos entre referência e canônico não constitui bloqueador isolado: a geometria oficial contém os lados simétricos. É preciso validar o reaproveitamento dos UVs e a escala nos dois lados antes de publicar. A antiga exigência de faces duplicadas foi corrigida; veja `docs/maia-10-vinho-preflight.md`.

Organização aprovada: **Tecidos → VELUDO → MAIA → Maia 10 — Vinho**. O Revestimento ainda aguarda bake, mapas e aprovação visual para publicação.
