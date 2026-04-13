# Tổng quan dự án — NeuralAPI AI Platform

**Phiên bản:** 1.0.0  
**Cập nhật lần cuối:** 2026-04-11  
**Trạng thái:** Active

## Giới thiệu
NeuralAPI là một nền tảng AI Multi-Tenant (đa người dùng/doanh nghiệp), được thiết kế với mô hình tổng thể tương tự như OpenAI Console. 
Nền tảng này cung cấp các tính năng mạnh mẽ để người dùng có thể truy cập API LLM, xây dựng các flow RAG (Retrieval-Augmented Generation), quản lý AI Agents cá nhân hóa, theo dõi mức độ sử dụng tài nguyên và quản lý hóa đơn/thanh toán.

## Mục tiêu dự án
- Cung cấp một nền tảng quản trị AI hiệu quả thông qua Frontend trực quan và API Backend hiệu năng cao.
- Quản lý tối ưu việc truy xuất LLM thông qua hàng đợi (task queue) và phân bổ tài nguyên GPU động (autoscale).
- Bảo đảm tính phân tách, bảo mật dữ liệu an toàn tuyệt đối giữa các tenants (không chia sẻ dữ liệu RAG, API keys hay lịch sử hội thoại agents).
- Cung cấp một giao diện API chuẩn hóa tương thích tốt với chuẩn của OpenAI cho phép tích hợp ngay lập tức vào các ứng dụng bên thứ 3.

## Các tính năng chính (Modules)
- **Dashboard (`/dashboard`)**: Khung nhìn tổng quan hiển thị biểu đồ KPIs và hoạt động hệ thống.
- **RAG & Vector Search (`/rag`)**: Quản lý kho tài liệu, hỗ trợ upload và tự động chunking, embedding để phục vụ truy vấn ngữ nghĩa.
- **AI Agents (`/agents`)**: Công cụ cho phép tạo lập các AI agent tùy biến và lưu trữ ngữ cảnh hội thoại.
- **Quản lý API Keys (`/keys`)**: Tạo, thu hồi và phân quyền API key bảo mật (sử dụng mã hóa một chiều SHA-256).
- **Usage Analytics (`/usage`)**: Phân tích tần suất gọi API, lượng token tiêu thụ trực quan bằng thư viện Recharts.
- **Billing (`/billing`)**: Quản lý hạn mức tài khoản (quota meters) và nâng cấp hạng mức dịch vụ.
- **Quản lý nhóm (`/teams`)**: Quản trị quyền truy cập đa người dùng và chia sẻ nội dung workspace.
- **Webhooks (`/webhooks`)**: Gửi thông báo các sự kiện (event notifications) đến các hệ thống ngoại vi.

## Công nghệ cốt lõi (Tech Stack)
### Frontend
- **Framework**: Next.js 14 với App Router.
- **UI & Styling**: Tailwind CSS, lucide-react, next-themes.
- **Hiển thị dữ liệu**: Recharts.

### Backend & API
- **Web Gateway**: FastAPI.
- **LLM Engine**: Ray Serve tự động quy mô kết hợp vLLM (sử dụng model: `qwen3.5-plus`).
- **Xác thực (Auth)**: JWT (HS256), passlib (hashing bcrypt mật khẩu người dùng), và SHA-256 cho API Keys.

### Database & Background Jobs
- **Cơ sở dữ liệu**: PostgreSQL 16 tích hợp extension `pgvector` phục vụ tìm kiếm cosine similarity cho pipeline RAG. ORM sử dụng SQLAlchemy và Alembic.
- **Message Queue & Cache**: Redis (Giới hạn Rate Limiting và Hàng đợi).
- **Background Worker**: RQ Worker đảm nhiệm tiến trình chạy ngầm xử lý phân tách (chunking) và vector hóa (embedding) tài liệu RAG.

### Infrastructure & Monitoring
- Vận hành trên nền **Docker & Docker Compose**.
- Giám sát trạng thái hoạt động qua **Prometheus** và **Grafana**. 

> **Lưu ý:** Để biết thêm chi tiết về thiết kế hệ thống và API, vui lòng xem các tài liệu `system-design.md`, `architecture.md` và `api-spec.md` trong thư mục `docs/`.
