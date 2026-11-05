# Presentation - TriAgent

Interview deck for the Developer Intern technical assessment.

## Files

| File | Purpose |
|---|---|
| `TriAgent_Presentation.pptx` | 16 content slides + 3 appendix slides, 16:9, speaker notes on every slide |
| `SPEAKER_NOTES.md` | Per-slide notes + Appendices A-E (5-min script, 10-min script, 20 Q&A, technical must-knows, claims to verify) |
| `../scripts/build_presentation.py` | Reproducible generator for the `.pptx` |

## Regenerate the deck

```bash
pip install python-pptx
python scripts/build_presentation.py
```

## Edit the content

- Slide content and speaker notes live in `scripts/build_presentation.py`.
- Colors, fonts and layout helpers are defined at the top of the file.
- After editing, re-run the generator. The `.md` notes file is generated from the
  deck's notes pane; to refresh it, re-run the notes build step (or copy the notes
  manually).

## Before presenting

Resolve every item in **Appendix E** of `SPEAKER_NOTES.md`
(and Appendix C slide in the deck), then delete that private checklist slide.
