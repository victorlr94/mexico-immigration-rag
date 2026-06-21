# Corpus de muestra

Conjunto pequeño de documentos **públicos** de trámites migratorios de México,
versionado a propósito en el repositorio para que el demo funcione tras un
`git clone` sin pasos manuales de descarga.

> Este corpus es solo para **demostración**. No es exhaustivo ni necesariamente
> la versión vigente de cada trámite. Para información oficial y actualizada,
> consulta directamente al [Instituto Nacional de Migración (INM)](https://www.gob.mx/inm)
> y las fuentes oficiales del Gobierno de México.

## Procedencia y licencia

Los documentos provienen de portales oficiales del Gobierno de México
(`gob.mx` / INM), que son información pública gubernamental. Cada archivo
se lista abajo con su fuente para trazabilidad.

| Archivo | Tema | Páginas | Fuente oficial |
|---|---|---|---|
| `Ley_de_Migracion.pdf` | Ley de Migración (marco legal migratorio) | 72 | Gobierno de México / DOF _(confirmar URL)_ |
| `Reg_LNac.pdf` | Reglamento de la Ley de Nacionalidad | 15 | Gobierno de México / DOF _(confirmar URL)_ |
| `lineamientos-visas-25-jul-2025.pdf` | Lineamientos para la expedición de visas (25-jul-2025) | 41 | Gobierno de México / INM _(confirmar URL)_ |
| `Lin_tramites_y_procedimentos.pdf` | Lineamientos para trámites y procedimientos migratorios | 84 | Gobierno de México / INM _(confirmar URL)_ |

> _Las URLs exactas de descarga quedan por confirmar para trazabilidad completa._

## Cómo indexar este corpus

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python scripts/ingest.py data/samples/*.pdf
```

Esto carga cada PDF, lo divide en chunks, calcula embeddings y los almacena en
ChromaDB (directorio de persistencia según `configs/default.yaml` / `Settings`).
