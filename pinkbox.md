# 🩷 PinkBox

**Transparentny blackbox dla ludzi, którzy chcą widzieć więcej.**

PinkBox to warstwa humoru, dystansu i inteligentnej regulacji w systemach AI.

Nie jest filtrem cenzury.  
Nie jest trybem wyśmiewania użytkownika.  
Nie jest „śmiesznym dodatkiem”.

PinkBox to mechanizm, który pozwala systemowi przyjąć chaos, napięcie lub absurd bez utraty jakości odpowiedzi.

## Kluczowe założenia

- Rozróżnia ekspresję od agresji.
- Działa jako bufor przed rdzeniem modelu.
- Dodaje krótki komentarz tylko przy podwyższonym impakcie.
- Pozostaje transparentny: pokazuje, co robi i dlaczego.

## Poziomy działania

- **Level 0**: brak komentarza (`impact_score < 0.40`).
- **Level 1**: lekka regulacja (`0.40 <= impact_score < 0.65`).
- **Level 2**: wysoki impakt, opcjonalne pytanie refleksyjne (`impact_score >= 0.65`).

## Pipeline

```text
User input
→ Safety check
→ Expressive / toxic intent detection
→ Impact score
→ Absorb & transform
→ PinkBox hint
→ Core model
→ Final response
```

## Status

- Version: 0.2
- Part of: KaiSpace / Python Zero / MC1448X ecosystem
- Mode: experimental, transparent, human-friendly
- License: MIT
