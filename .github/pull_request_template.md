## Material

- ID canônico:
- Nome público:
- Tipo: novo / atualização

## Checklist obrigatório

- [ ] Os arquivos finais estão em `public/v1/assets/<material-id>/`.
- [ ] Os mapas por face estão em `public/v1/assets/<material-id>/face-set/`.\n- [ ] O `reference.glb` foi auditado como Scale Master e, quando necessário, a Base Color foi bakeada para UV0.
- [ ] `public/v1/catalog.json` foi incluído na mesma alteração.
- [ ] O vivo foi derivado por cópia binária de `LATERAL_TOP.webp`.
- [ ] Conversões de formato foram autorizadas e documentadas.
- [ ] Nenhum metadado privado foi publicado.
- [ ] `node scripts/validate-public-catalog.mjs` passou.
