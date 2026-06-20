# ADR-002: pypdf como librería de extracción de texto de PDF

## Estado

Aceptado · Fase 0

## Contexto

`pip-audit` en CI reportó 28 CVEs sobre `pypdf==5.9.0` (pin original `~=5.0`).
La mayoría de los hallazgos son del tipo "long runtimes" / "RAM exhaustion" al
procesar PDFs malformados (ej. CVE-2026-22691: tiempos de ejecución largos al
reconstruir la tabla de referencias cruzadas con `startxref` inválido) — es
decir, vectores de **denegación de servicio**, no de ejecución de código ni
fuga de datos. Aun así, el volumen (28 CVEs en una sola versión) es una señal
de que esa versión específica está desactualizada respecto a los fixes
disponibles.

Dado que este componente procesa **archivos subidos directamente por
usuarios** (la mayor superficie de ataque del sistema, según la Security
Skill), se evaluó tanto actualizar la versión como cambiar de librería.

## Decisión

Actualizamos el pin a `pypdf~=6.0` (resuelve la mayoría de los CVEs
reportados) y **mantenemos pypdf** como la librería de extracción de texto,
sin cambiar a una alternativa.

Se refuerza la mitigación ya prevista en la Security Skill como complemento
necesario — un upgrade de versión no sustituye los controles, los completa:

- Límite de tamaño de archivo (`max_file_size_mb`, ya en `Settings`).
- Límite de número de páginas (`max_pages`, ya en `Settings`).
- Parseo aislado en `try/except` con timeout explícito al implementar el
  loader (pendiente, Fase 1).

## Alternativa considerada: PyMuPDF (fitz)

Se evaluó como reemplazo directo por su mejor rendimiento en extracción.
Descartada por dos motivos, cualquiera de los dos ya suficiente por sí solo:

1. **Vulnerabilidad de mayor severidad**: PyMuPDF 1.26.5 tuvo un path
   traversal y escritura arbitraria de archivos en su función
   `embedded_get` (VU#504749) — categoría de riesgo más grave (escritura
   arbitraria en disco) que los DoS reportados en pypdf.
2. **Licencia AGPL-3.0**: PyMuPDF se distribuye bajo AGPL (o licencia
   comercial de pago). AGPL exigiría liberar el código fuente completo del
   proyecto bajo los mismos términos, lo cual entra en conflicto directo con
   el requerimiento original del proyecto de usar "tecnologías gratuitas y
   open source" en un repositorio de portfolio bajo licencia MIT.

Conclusión: ninguna librería de parseo de PDF está exenta de este tipo de
vulnerabilidades — son en buena medida inherentes a la complejidad del
formato PDF. La estrategia correcta no es "elegir la librería sin CVEs"
(no existe tal cosa), sino mantener la versión razonablemente actualizada y
reforzar los controles de entrada alrededor de cualquier librería elegida.

## Consecuencias

- (+) Se resuelven la mayoría de los CVEs activos sin cambiar de dependencia.
- (+) Se evita adoptar AGPL, que habría comprometido la licencia MIT del proyecto.
- (+) Se evita una vulnerabilidad de mayor severidad (escritura arbitraria).
- (−) pypdf 6.x puede tener cambios menores de API respecto a 5.x; se
  verificará al implementar el loader en la Fase 1.
- (−) Persiste la necesidad de revisar `pip-audit` periódicamente — pypdf
  seguirá generando CVEs nuevos con el tiempo, dado el formato que procesa.
