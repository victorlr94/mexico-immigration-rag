# ADR-003: Gate de dependency audit con lista explícita de excepciones

## Estado

Aceptado · Fase 0

## Contexto

`pip-audit` en CI falla el build ante **cualquier** vulnerabilidad conocida en
las dependencias, sin distinguir severidad ni si existe un fix disponible.
Tras actualizar `pypdf` (ver ADR-002), quedaron 7 vulnerabilidades en 6
paquetes que no se pueden resolver de inmediato sin asumir riesgo:

- 3 son transitivas de `langchain` y se resolverían con un upgrade de versión
  mayor (0.3 → 1.x) que no se justifica hacer a ciegas sin código que use su
  API todavía.
- 1 (`ragas`, CVE-2026-6587, SSRF) **no tiene parche disponible** del
  proveedor a la fecha — ningún upgrade la resuelve hoy.
- 2 (`transformers`, `diskcache`) son transitivas sin fix version estable
  reportada, o cuyo único fix es un release candidate no apto para producción.

Con el job tal como estaba, el `Dependency audit` de CI **nunca podría quedar
en verde** mientras existan estas vulnerabilidades — independientemente de si
se revisaron y aceptaron consciente y razonadamente, o si simplemente nadie
las miró. Eso degrada el valor del check: deja de distinguir "hay algo nuevo
que requiere atención" de "ya lo vimos y aceptamos el riesgo".

## Decisión

Se mantiene `pip-audit` como gate bloqueante (rechazado: deshabilitarlo o
ignorar el exit code completo — ver alternativas abajo), pero se introduce
`security/accepted-vulnerabilities.txt`: una lista explícita de IDs de
vulnerabilidad ya revisados, cada uno con su justificación y una fecha de
revisión, que el workflow pasa a `pip-audit --ignore-vuln` dinámicamente.

Cualquier vulnerabilidad **nueva** que no esté en ese archivo sigue
bloqueando el build — que es el comportamiento correcto de un gate de
seguridad real.

## Alternativas consideradas

1. **Quitar el exit code de error (`pip-audit || true`)**: el check queda
   siempre verde, pero pierde la capacidad de alertar sobre vulnerabilidades
   *nuevas*. Rechazada: convierte el gate en decorativo.
2. **`--ignore-vuln` hardcodeado directamente en el YAML del workflow**:
   funciona, pero los IDs quedan sin contexto (solo códigos), mezclados con
   sintaxis de CI, y son menos visibles para quien no lee YAML. Rechazada en
   favor de un archivo dedicado y legible en texto plano.
3. **Deshabilitar el job por completo**: pierde toda la señal, incluida la de
   vulnerabilidades futuras en dependencias directas. Rechazada.

## Consecuencias

- (+) El gate distingue vulnerabilidades nuevas (bloquean) de ya revisadas
  (no bloquean), preservando su utilidad real.
- (+) Cada excepción queda documentada con su razón y una fecha de revisión,
  mitigando el riesgo de "ignorar y olvidar" (limitación conocida de
  `pip-audit --ignore-vuln`, que no soporta expiración nativa).
- (+) El archivo es legible por cualquiera sin conocer la sintaxis de
  GitHub Actions.
- (−) Requiere disciplina manual: alguien debe revisar y limpiar entradas
  resueltas (ej. al completar el upgrade de langchain, quitar sus 3
  entradas relacionadas). Se mitiga con la fecha de revisión en cada bloque
  y la revisión periódica que ya exige la Security Skill.
- (−) Un ID ignorado por error (mal copiado, demasiado amplio) podría
  enmascarar una vulnerabilidad real. Mitigado porque `--ignore-vuln` actúa
  por ID exacto de vulnerabilidad, no por nombre de paquete — no hay forma
  de "ignorar todo lo de X paquete" por accidente.

## Seguimiento

Próxima revisión obligatoria de `security/accepted-vulnerabilities.txt`:
**2026-09-01** (fecha anotada en cada entrada del archivo).
