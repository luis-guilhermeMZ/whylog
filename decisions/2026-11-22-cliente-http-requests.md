---
titulo: Usar requests para chamadas HTTP
data: 2026-11-22
status: ativa
tags: [python, integracao]
---

## Decisão

Manter `requests` como única dependência de runtime para chamadas HTTP. O cliente suporta o endpoint documentado em [[2026-11-22-endpoint-nativo-gemini]].

## Motivo

A biblioteca é pequena, conhecida e suficiente para as requisições síncronas da CLI.

## Alternativas descartadas

- Adicionar SDKs específicos de cada provedor
