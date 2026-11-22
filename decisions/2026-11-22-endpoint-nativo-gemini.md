---
titulo: Usar endpoint nativo do Gemini
data: 2026-11-22
status: ativa
tags: [gemini, integracao]
---

## Decisão

Usar `generateContent` nativo quando a URL configurada pertence ao host do Gemini.

## Motivo

O endpoint nativo permite autenticação explícita pelo cabeçalho do Google e evita depender da camada de compatibilidade.

## Alternativas descartadas

- Usar somente o endpoint compatível com OpenAI
