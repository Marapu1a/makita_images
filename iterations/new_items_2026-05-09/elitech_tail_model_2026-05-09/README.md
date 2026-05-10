# Elitech Tail Model Iteration

Tail-only pass for fresh `Elitech` items that survived:
- official `elitech.ru`
- exact PDF crops
- family PDF matches
- exact `elitech-m.ru` article matches

This pass uses the older project pattern:
- search by exact article first
- fallback to model/name search
- auto-download only clearly safe model-family matches
- put doubtful matches into a review sheet

Artifacts:
- `output/elitech_model_tail_report.xlsx`
- `output/elitech_model_review.xlsx`
- `output/remaining_after_elitech_model_tail.xlsx`
- `output/import_images/`
