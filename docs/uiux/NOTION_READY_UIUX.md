# UI/UX 설계서 (Notion 반영용)

> 원본: `docs/uiux/UIUX_Spec.md`
> 대상 페이지: https://www.notion.so/UI-UX-2ee405a3a72080a58c93d967ef0f2444

## 핵심 요약
- ReqID union: 77
- API rows: 75 (unique endpoints: 71)
- DB tables: 61
- Figma node: 10301:23060

## 불일치 목록
1. ReqID set mismatch between requirements and key features -> keep union matrix
2. CUSTOMER SSE scope mismatch -> MVP baseline, Phase2 advanced stream
3. MCP API without dedicated DB area -> use tool/audit tables in MVP
4. Latency target mismatch -> first-token and total latency both enforced

## IA
- Agent Console: SCR-AGT-001~007
- Customer Widget: SCR-CUS-001~003
- Admin/OPS: SCR-ADM-001~005

## Notion 수동 반영 절차
1. Paste this structure with H1/H2/H3 preserved
2. Convert matrix sections to Notion tables
3. Upload 14 PNG files from `docs/uiux/assets/`
4. Verify rendering and lock baseline

## 관련 파일
- `docs/uiux/UIUX_Spec.md`
- `docs/uiux/Figma_to_React_Checklist.md`
- `docs/uiux/assets/*.png`
