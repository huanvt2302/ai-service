# 2026-04-14 — Clean Up Ray And Envs

**Version:** 1.1.2  
**Type:** Refactor | Infrastructure  
**Scope:** Backend | Infrastructure | Docs

---

## Summary
Hoàn thành dọn dẹp các service rác (đặc biệt là các cài đặt liên quan đến Ray) đã không còn được sử dụng và chuẩn hóa biến môi trường LLM cấu hình cho hệ thống sang `LLM_BASE_URL` sau khi chuyển đổi thành công sang MLX server. Swarm architecture vẫn được giữ lại để dự phòng.

---

## Changed
* Đổi tên biến `VLLM_BASE_URL` thành `LLM_BASE_URL` trên toàn bộ dự án (`.env.example`, code gateways, worker, swarm configs).
* Cập nhật `README.md` loại bỏ các đề cập về `vLLM` và điều chỉnh lại thiết kế sang MLX native / llama-cpp.
* Chỉnh sửa các chú thích code trong `document_worker.py` và `gateway.py`.
* Script gcloud cập nhật env variables mới.

## Removed
* Loại bỏ các config liên quan tới `RAY_ADDRESS` và service `ray` trong cả `docker-compose.yml` lẫn `docker-compose.swarm.yml`.
* Xóa bỏ module rỗng `backend/serve`.
* Xóa dependencies của ray trong `requirements.txt`.

---

## Files Changed
- `backend/serve` (deleted)
- `docker-compose.yml` (modified)
- `docker-compose.swarm.yml` (modified)
- `.env.example` (modified)
- `backend/config.py` (modified)
- `backend/requirements.txt` (modified)
- `backend/routes/gateway.py` (modified)
- `backend/routes/rag.py` (modified)
- `backend/workers/document_worker.py` (modified)
- `scripts/burst-gcp.sh` (modified)
- `README.md` (modified)
