# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Hoàng Văn Dương
**Nhóm:** G08
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là hai vector embedding trỏ gần cùng một hướng trong không gian vector. Với văn bản, điều này thường cho thấy hai câu/đoạn có ý nghĩa gần nhau, dù có thể dùng từ ngữ khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: Người mua có thể gửi yêu cầu trả hàng nếu sản phẩm bị lỗi.
- Câu B: Khách hàng được phép yêu cầu hoàn trả khi hàng nhận được bị hư hỏng.
- Tại sao tương đồng: Hai câu đều nói về quyền yêu cầu trả hàng/hoàn trả khi sản phẩm có vấn đề.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người mua có thể gửi yêu cầu trả hàng nếu sản phẩm bị lỗi.
- Câu B: Hệ thống gợi ý sản phẩm dựa trên lịch sử tìm kiếm của người dùng.
- Tại sao khác: Câu A nói về chính sách trả hàng, còn câu B nói về hệ thống gợi ý sản phẩm, hai nội dung gần như không liên quan.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity tập trung vào hướng của vector, tức là quan hệ về mặt ý nghĩa, thay vì độ lớn tuyệt đối của vector. Điều này phù hợp với text embeddings vì hai câu có cùng nghĩa nên được xem là gần nhau ngay cả khi độ dài hoặc cường độ biểu diễn của vector khác nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Công thức: `ceil((document_length - overlap) / (chunk_size - overlap))`
>
> Thay số: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
>
> Đáp án: **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi `overlap=100`, số chunk là `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks`, tức là tăng từ 23 lên 25 chunks. Overlap lớn hơn giúp giữ ngữ cảnh giữa hai chunk liền kề, giảm nguy cơ cắt mất thông tin quan trọng ở ranh giới chunk, nhưng đổi lại sẽ tạo nhiều chunk hơn và tốn chi phí lưu trữ/truy xuất hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])\s+` để tách câu tại khoảng trắng đứng sau dấu `.`, `!`, hoặc `?`. Hàm bỏ qua input rỗng, loại các câu chỉ có khoảng trắng bằng `strip()`, rồi gom tối đa `max_sentences_per_chunk` câu vào một chunk để giữ ngữ cảnh tự nhiên theo câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử tách văn bản theo thứ tự ưu tiên `\n\n`, `\n`, `. `, khoảng trắng, rồi cuối cùng là cắt theo ký tự nếu không còn separator tốt hơn. Base case là đoạn rỗng thì trả `[]`, đoạn có độ dài nhỏ hơn hoặc bằng `chunk_size` thì trả chính đoạn đó; các phần nhỏ sau khi tách được merge lại sao cho không vượt quá `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` chuyển mỗi `Document` thành một record gồm `id`, `content`, `metadata` và embedding của nội dung, sau đó lưu trong in-memory list `_store`. `search` embedding câu hỏi, tính dot product giữa query embedding và từng document embedding, sắp xếp giảm dần theo score rồi trả về top-k kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc metadata trước khi tính similarity, nên chỉ các chunk có đủ cặp key-value trong `metadata_filter` mới được đưa vào bước ranking. `delete_document` xóa toàn bộ record có `metadata.doc_id` trùng với `doc_id` cần xóa và trả `True` nếu kích thước store giảm.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `KnowledgeBaseAgent.answer` truy xuất top-k chunk từ vector store, rồi dựng context theo từng nguồn dạng `[1] Source: ...` để LLM có căn cứ trả lời. Prompt yêu cầu chỉ dựa trên ngữ cảnh, nói rõ nếu không tìm thấy thông tin, và trích dẫn nguồn dạng `[1]`, `[2]` khi có thể.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
.venv/bin/python -m pytest tests/ -v

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1
rootdir: /home/duong/AI_in_action/lab_07/K4-L3B-Data-Foundations
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::* PASSED
tests/test_solution.py::TestSentenceChunker::* PASSED
tests/test_solution.py::TestRecursiveChunker::* PASSED
tests/test_solution.py::TestEmbeddingStore::* PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::* PASSED
tests/test_solution.py::TestComputeSimilarity::* PASSED
tests/test_solution.py::TestCompareChunkingStrategies::* PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::* PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::* PASSED

============================== 42 passed in 0.21s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Người mua có thể yêu cầu trả hàng nếu sản phẩm bị lỗi. | Khách hàng được hoàn trả khi nhận hàng hư hỏng. | cao | 0.166 | Đúng |
| 2 | Thực phẩm tươi sống cần gửi yêu cầu hoàn tiền trong vòng 24 giờ. | Hàng đông lạnh phải khiếu nại trong 24 giờ sau khi giao thành công. | cao | 0.148 | Đúng |
| 3 | Thẻ tín dụng nhận tiền hoàn trong 7 đến 14 ngày làm việc. | Người bán cần đóng gói hàng đúng quy cách vận chuyển. | thấp | 0.000 | Đúng |
| 4 | Người mua chưa nhận được hàng không cần cung cấp bằng chứng. | Shopee xử lý khiếu nại chưa nhận hàng dựa trên hệ thống theo dõi. | cao | 0.161 | Đúng |
| 5 | Khi đóng gói hàng hoàn trả cần quay video và gửi đủ phụ kiện. | Hệ thống gợi ý sản phẩm dựa trên lịch sử tìm kiếm. | thấp | 0.000 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả bất ngờ nhất là các cặp tôi dự đoán cao chỉ đạt khoảng `0.15-0.17`, không quá lớn về mặt tuyệt đối. Nguyên nhân là benchmark đang dùng `lexical-hash-4096`, một baseline offline thiên về trùng từ và bigram hơn là embedding semantic thật, nên các câu đồng nghĩa nhưng dùng từ khác vẫn không được kéo quá gần nhau. Điều này cho thấy loại embedding quyết định rất nhiều đến khả năng biểu diễn ý nghĩa, không chỉ riêng thuật toán similarity.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thực phẩm tươi sống và đông lạnh phải gửi yêu cầu trả hàng/hoàn tiền trong bao lâu? | `shopee-article-77251#13`: chính sách trả hàng/hoàn tiền, nêu mốc 15 ngày và ngoại lệ thực phẩm tươi sống/đông lạnh. | 0.5128 | Có | Trong vòng 24 giờ kể từ khi đơn hàng được cập nhật giao hàng thành công. |
| 2 | Sau khi Shopee chấp nhận hoàn tiền, thẻ tín dụng hoặc ghi nợ nhận tiền trong bao lâu? | `shopee-article-189473#1`: bài thời gian nhận tiền hoàn, top-1 đúng tài liệu nhưng chưa chứa trực tiếp mốc 7-14 ngày. | 0.3708 | Có một phần | Thẻ tín dụng/ghi nợ nhận tiền hoàn trong 7-14 ngày làm việc, evidence nằm ở top-3. |
| 3 | Nếu tự sắp xếp gửi hàng hoàn trả thì người mua có phải trả phí trước không? | `shopee-article-77251#58`: phần trách nhiệm chi phí hoàn trả, nói các hình thức gửi hàng hoàn trả. | 0.4009 | Có | Có, người mua cần thanh toán trước; Shopee hỗ trợ hoàn phí nếu đủ điều kiện. |
| 4 | Người mua chưa nhận được hàng thì cần cung cấp bằng chứng gì? | `shopee-article-79467#3`: hướng dẫn chuẩn bị bằng chứng, nêu trường hợp chưa nhận hàng. | 0.3929 | Có | Không cần cung cấp bằng chứng; Shopee xử lý dựa trên hệ thống theo dõi đơn hàng. |
| 5 | Khi đóng gói hàng hoàn trả, người mua cần quay video và gửi kèm những gì? | `shopee-article-79508#2`: cách đóng gói đơn hàng hoàn trả, yêu cầu quay video và gửi đủ hộp/phụ kiện/quà tặng. | 0.3918 | Có | Cần quay video quá trình đóng gói và gửi kèm hộp, giấy tờ, phụ kiện, quà tặng nếu có. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

Kết quả benchmark tốt nhất của tôi dùng chiến lược `policy_structure`: `Hit@1 = 80%`, `Hit@3 = 100%`, `MRR = 0.867`, `lab_score = 9/10`.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Qua phần demo, tôi thấy khác biệt lớn nhất không chỉ nằm ở vector store mà nằm ở cách chunk giữ được cấu trúc tài liệu. Khi chunk có lặp lại tiêu đề/chủ đề tài liệu như `policy_structure`, các đoạn nhỏ từ bảng hoặc chính sách dài vẫn giữ đủ ngữ cảnh để truy xuất đúng hơn. Điều này giúp tôi hiểu rằng tối ưu RAG cần đo bằng câu hỏi thật và evidence thật, không chỉ nhìn chunk có vẻ gọn.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 9 / 10 |
| **Tổng phần cá nhân** | **59 / 60** |
