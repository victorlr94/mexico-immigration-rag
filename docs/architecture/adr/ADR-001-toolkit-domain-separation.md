# ADR-001: Separación entre núcleo reutilizable y capa de dominio

## Estado

Aceptado · Fase 0

## Contexto

Este proyecto es el primero de una serie de proyectos de AI Engineering. El caso
inicial es migratorio, pero la intención es reutilizar la arquitectura en otros
dominios (banca, telco, legal, compliance). Necesitamos una separación que
permita esa reutilización sin sobrearquitecturar la POC.

## Decisión

Dividimos el código fuente en dos planos dentro de `src/`:

- **`src/genai_toolkit/`**: núcleo de AI Engineering **agnóstico de dominio**
  (ingesta, chunking, embeddings, vector store, retrieval, LLM, prompts,
  seguridad, evaluación, observabilidad, configuración, pipeline). No menciona
  el dominio migratorio en ningún lugar.
- **`src/domain/`** + **`src/application/`**: capa fina **específica del
  dominio** (disclaimers, definición de alcance, templates de prompt con
  contexto migratorio) y la orquestación del caso de uso.

El `genai_toolkit/` vive **dentro** del repositorio, no como librería separada
todavía. Las dependencias entre componentes se expresan mediante interfaces
(`typing.Protocol` / ABCs), de modo que su extracción futura a una librería
instalable sea un `git mv` + empaquetado, no un refactor.

## Alternativas consideradas

- **Monolito sin separación**: más rápido al inicio, pero acopla todo al dominio
  migratorio e impide la reutilización, que es un objetivo explícito.
- **Librería `genai-toolkit` separada desde el día 1**: máxima reutilización,
  pero multiplica el costo (versionado, releases, instalación local) sin
  beneficio real con un solo consumidor. Prematuro para una POC.

## Consecuencias

- (+) Reutilización futura barata: cambiar de dominio toca solo la capa fina.
- (+) Las interfaces permiten sustituir LLM, vector store o embedder sin refactor.
- (+) Separación clara comunica madurez de ingeniería en el portfolio.
- (−) Algo más de ceremonia (interfaces) que un monolito directo; se acepta por
  el valor de reutilización y testeo.
- (−) Riesgo de acoplamiento accidental: se mitiga con revisión periódica de que
  `genai_toolkit/` no mencione el dominio.
