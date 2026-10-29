# Maia 10 — Vinho: fontes técnicas

Os oito WebPs são cópias lossless dos PNGs originais. Ainda não são Base Colors bakeadas para UV0.

O conector GitHub limita requisições a 16 MiB. O GLB técnico de 20.992.820 bytes está dividido em 3 partes binárias sem transformação. Para recompô-lo e verificar SHA-256:

```sh
python scale-masters/fabric-kv-010/assemble-reference.py
node scripts/scale-master-audit.mjs scale-masters/fabric-kv-010/reference.glb
```

`transport.json` registra os hashes das partes e do arquivo completo. Não é necessário Blender para recompor o GLB.

**Bake/publicação bloqueados:** a referência tem somente um lado de cinco superfícies; veja `geometry-comparison.json` e `docs/maia-10-vinho-preflight.md`. É necessário receber o GLB completo. Nada nesta pasta deve ser consumido pelo configurador como asset publicado.
